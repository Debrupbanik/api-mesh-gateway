"""Service definitions for the API Mesh Gateway."""

from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED = "weighted"
    AI_POWERED = "ai_powered"


class ServiceConfig(BaseModel):
    """Configuration for a backend service."""

    name: str
    hosts: list[str]
    port: int
    path_prefix: str = "/"
    timeout: int = 30
    health_check_path: str = "/health"
    health_check_interval: int = 30
    weight: int = 1
    metadata: dict = {}

    @property
    def base_url(self) -> str:
        """Get base URL for the service."""
        return f"http://{self.hosts[0]}:{self.port}" if self.hosts else ""


class RouteConfig(BaseModel):
    """Route configuration."""

    path_pattern: str
    service_name: str
    methods: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    auth_required: bool = False
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None
    transform_request: bool = False
    transform_response: bool = False


class GatewayConfig(BaseModel):
    """Complete gateway configuration."""

    services: dict[str, ServiceConfig] = {}
    routes: list[RouteConfig] = []
    load_balancing: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    default_timeout: int = 30
    max_retries: int = 3
