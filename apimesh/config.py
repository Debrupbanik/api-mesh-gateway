"""Configuration management for API Mesh Gateway."""

from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache


class AuthSettings(BaseSettings):
    """Authentication settings."""

    # API Key Auth
    api_key_enabled: bool = False
    api_key_header: str = "X-API-Key"
    api_keys: list[str] = []

    # JWT Auth
    jwt_enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_audience: Optional[str] = None
    jwt_issuer: Optional[str] = None

    class Config:
        env_prefix = "APIMESH_AUTH_"
        case_sensitive = False


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

    config_file: Optional[str] = None

    class Config:
        env_prefix = "APIMESH_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Get cached auth settings instance."""
    return AuthSettings()
