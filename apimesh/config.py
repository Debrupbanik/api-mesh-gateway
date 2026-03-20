"""Configuration management for API Mesh Gateway."""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "API Mesh Gateway"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    redis_ttl_default: int = 300

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60

    ai_predictions_enabled: bool = True
    ai_model_path: str = "/tmp/apimesh_model.joblib"

    prometheus_enabled: bool = True
    prometheus_port: int = 9090

    class Config:
        env_prefix = "APIMESH_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
