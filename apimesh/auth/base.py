"""Base authentication types."""

from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class AuthType(Enum):
    """Authentication types."""

    API_KEY = "api_key"
    JWT = "jwt"
    NONE = "none"


@dataclass
class AuthResult:
    """Result of authentication check."""

    success: bool
    authenticated: bool = False
    client_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    auth_type: Optional[AuthType] = None


class AuthMiddleware:
    """Base class for authentication middleware."""

    async def authenticate(self, request: Any) -> AuthResult:
        """Authenticate a request."""
        raise NotImplementedError
