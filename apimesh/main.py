"""Main gateway application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .config import get_settings
from .circuit import CircuitBreakerManager
from .cache import CacheManager
from .limiter import RateLimiterManager
from .ai import TrafficPredictor
from .routing import RequestRouter
from .core import RouteConfig, ServiceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

requests_total = Counter(
    "apimesh_requests_total", "Total requests", ["method", "endpoint", "status"]
)
request_duration = Histogram(
    "apimesh_request_duration_seconds", "Request duration", ["method", "endpoint"]
)

gateway_app: FastAPI = None
router: RequestRouter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router
    settings = get_settings()

    circuit_breaker_manager = CircuitBreakerManager()
    cache_manager = CacheManager()
    rate_limiter_manager = RateLimiterManager()
    traffic_predictor = TrafficPredictor(settings.ai_model_path)

    services = {
        "api": ServiceConfig(
            name="api",
            hosts=["localhost"],
            port=8001,
            path_prefix="/api/v1",
        )
    }

    routes = [
        RouteConfig(
            path_pattern="/api",
            service_name="api",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            cache_ttl=60,
        )
    ]

    router = RequestRouter(
        routes=routes,
        services=services,
        circuit_breaker_manager=circuit_breaker_manager,
        cache_manager=cache_manager,
        rate_limiter_manager=rate_limiter_manager,
        traffic_predictor=traffic_predictor,
    )

    await cache_manager.connect()

    logger.info("API Mesh Gateway started")
    yield

    await cache_manager.disconnect()
    logger.info("API Mesh Gateway stopped")


gateway_app = FastAPI(
    title="API Mesh Gateway",
    description="AI-Powered API Gateway with intelligent routing, caching, and circuit breaking",
    version="1.0.0",
    lifespan=lifespan,
)

gateway_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@gateway_app.get("/")
async def root():
    return {"message": "API Mesh Gateway", "version": "1.0.0"}


@gateway_app.get("/health")
async def health():
    return {"status": "healthy"}


@gateway_app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@gateway_app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy(path: str, request: Request):
    full_path = f"/{path}"
    if request.url.query:
        full_path += f"?{request.url.query}"

    return await router.route_request(request, full_path, request.method)


def run():
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "apimesh.main:gateway_app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
