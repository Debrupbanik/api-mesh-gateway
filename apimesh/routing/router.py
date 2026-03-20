"""Request routing and forwarding."""

import httpx
import time
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from ..circuit import CircuitBreakerManager, CircuitBreakerOpen
from ..cache import CacheManager
from ..ai import TrafficPredictor
from ..limiter import RateLimiterManager, RateLimitConfig
from ..core import RouteConfig, ServiceConfig, LoadBalancingStrategy
from .load_balancer import LoadBalancer

import logging

logger = logging.getLogger(__name__)


class RequestRouter:
    """
    Routes incoming requests to appropriate backend services.

    Features:
    - Path-based routing
    - Load balancing
    - Circuit breaker protection
    - Rate limiting
    - Caching
    - Request/response transformation
    """

    def __init__(
        self,
        routes: list[RouteConfig],
        services: dict[str, ServiceConfig],
        circuit_breaker_manager: CircuitBreakerManager,
        cache_manager: CacheManager,
        rate_limiter_manager: RateLimiterManager,
        traffic_predictor: TrafficPredictor,
    ):
        self.routes = routes
        self.services = services
        self.circuit_breaker_manager = circuit_breaker_manager
        self.cache_manager = cache_manager
        self.rate_limiter_manager = rate_limiter_manager
        self.traffic_predictor = traffic_predictor
        self.load_balancer = LoadBalancer(traffic_predictor)

    def match_route(
        self, path: str
    ) -> tuple[Optional[RouteConfig], Optional[ServiceConfig]]:
        """Find matching route and service for a path."""
        for route in self.routes:
            if path.startswith(route.path_pattern):
                service = self.services.get(route.service_name)
                return route, service
        return None, None

    async def route_request(
        self,
        request: Request,
        path: str,
        method: str,
    ) -> Response:
        """Route and forward a request to the appropriate backend."""
        start_time = time.time()

        route, service = self.match_route(path)

        if not route or not service:
            return JSONResponse(
                status_code=404, content={"error": "Route not found", "path": path}
            )

        if method not in route.methods:
            return JSONResponse(
                status_code=405,
                content={"error": "Method not allowed", "allowed": route.methods},
            )

        client_id = self._get_client_id(request)

        allowed, rate_info = await self.rate_limiter_manager.check_rate_limit(
            route.path_pattern, client_id
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", **rate_info},
                headers={"Retry-After": str(rate_info["retry_after"])},
            )

        cache_key = f"{method}:{path}"
        if request.url.query:
            cache_key += f"?{request.url.query}"

        cached = await self.cache_manager.get(cache_key)
        if cached:
            return JSONResponse(content={"data": cached, "cached": True})

        breaker = await self.circuit_breaker_manager.get_breaker(service.name)

        try:
            backend_response = await breaker.call(
                self._forward_request, request, path, route, service
            )

            if route.cache_ttl:
                ttl = route.cache_ttl
            else:
                ttl = self.traffic_predictor.predict_next_ttl()

            await self.cache_manager.set(cache_key, str(backend_response), ttl)

        except CircuitBreakerOpen:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service temporarily unavailable",
                    "message": f"Circuit breaker open for {service.name}",
                },
            )
        except Exception as e:
            logger.error(f"Request routing error: {e}")
            return JSONResponse(
                status_code=502, content={"error": "Bad gateway", "message": str(e)}
            )

        duration = time.time() - start_time
        self.traffic_predictor.record_request(duration * 1000, 200)

        return backend_response

    async def _forward_request(
        self,
        request: Request,
        path: str,
        route: RouteConfig,
        service: ServiceConfig,
    ) -> Response:
        """Forward request to backend service."""
        instances = [
            {"host": host, "port": service.port, "weight": service.weight}
            for host in service.hosts
        ]

        instance = self.load_balancer.select_instance(
            instances, strategy=LoadBalancingStrategy.ROUND_ROBIN.value
        )

        target_path = path.replace(route.path_pattern, "", 1)
        if not target_path.startswith("/"):
            target_path = "/" + target_path

        url = f"http://{instance['host']}:{instance['port']}{service.path_prefix}{target_path}"

        headers = dict(request.headers)
        headers.pop("host", None)
        headers["x-forwarded-for"] = (
            request.client.host if request.client else "unknown"
        )
        headers["x-apimesh-request"] = "true"

        timeout = httpx.Timeout(service.timeout)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                req_body = await request.body()

                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=req_body if req_body else None,
                    params=dict(request.query_params),
                )

                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.text else {},
                    headers=dict(response.headers),
                )
            except httpx.TimeoutException:
                raise
            except httpx.RequestError as e:
                logger.error(f"Backend request error: {e}")
                raise

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class LoadBalancer:
    """Simple load balancer wrapper."""

    def __init__(self, predictor):
        self.predictor = predictor

    def select_instance(self, instances: list[dict], strategy: str) -> dict:
        if len(instances) == 1:
            return instances[0]
        return instances[0]
