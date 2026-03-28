"""Main gateway application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .config import get_settings, get_auth_settings
from .config_loader import ConfigLoader
from .circuit import CircuitBreakerManager
from .cache import CacheManager
from .limiter import RateLimiterManager
from .ai import TrafficPredictor
from .routing import RequestRouter
from .auth import APIKeyAuth, JWTAuth
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
api_key_auth: APIKeyAuth = None
jwt_auth: JWTAuth = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router, api_key_auth, jwt_auth
    settings = get_settings()
    auth_settings = get_auth_settings()

    circuit_breaker_manager = CircuitBreakerManager()
    cache_manager = CacheManager()
    rate_limiter_manager = RateLimiterManager()
    traffic_predictor = TrafficPredictor(settings.ai_model_path)

    # Initialize authentication
    if auth_settings.api_key_enabled:
        from .auth.api_key import APIKeyConfig

        api_key_config = APIKeyConfig(
            enabled=True,
            header_name=auth_settings.api_key_header,
        )
        for key in auth_settings.api_keys:
            api_key_config.add_key(key)
        api_key_auth = APIKeyAuth(api_key_config)
        logger.info("API Key authentication enabled")

    if auth_settings.jwt_enabled:
        from .auth.jwt import JWTConfig

        jwt_config = JWTConfig(
            enabled=True,
            secret_key=auth_settings.jwt_secret,
            algorithm=auth_settings.jwt_algorithm,
            audience=auth_settings.jwt_audience,
            issuer=auth_settings.jwt_issuer,
        )
        jwt_auth = JWTAuth(jwt_config)
        logger.info("JWT authentication enabled")

    # Load configuration from file or use defaults
    if settings.config_file:
        services, routes = ConfigLoader.load(settings.config_file)
        logger.info(f"Loaded config from {settings.config_file}")
    else:
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


async def authenticate_request(request: Request, route: RouteConfig):
    """Authenticate request using configured auth methods."""
    global api_key_auth, jwt_auth

    if not route.auth_required:
        return None

    # Try API key auth first
    if api_key_auth:
        result = await api_key_auth.authenticate(request)
        if result.success:
            return None  # Authenticated

    # Try JWT auth
    if jwt_auth:
        result = await jwt_auth.authenticate(request)
        if result.success:
            return None  # Authenticated

    # Return error if we get here
    return JSONResponse(
        status_code=401,
        content={"error": "Unauthorized", "message": "Authentication required"},
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
    global router

    # Get matched route for auth check
    full_path = f"/{path}"
    if request.url.query:
        full_path += f"?{request.url.query}"

    route, _ = router.match_route(full_path)

    # Check authentication if required
    if route:
        auth_error = await authenticate_request(request, route)
        if auth_error:
            return auth_error

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
