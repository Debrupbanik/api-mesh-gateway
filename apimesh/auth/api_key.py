"""API Key authentication."""

from dataclasses import dataclass, field
from typing import Optional
import hashlib
import time

from .base import AuthMiddleware, AuthResult, AuthType


@dataclass
class APIKeyConfig:
    """Configuration for API key authentication."""

    enabled: bool = False
    header_name: str = "X-API-Key"
    keys: list[str] = field(default_factory=list)
    key_hashes: set[str] = field(default_factory=set)
    expire_keys: dict[str, float] = field(default_factory=dict)
    allow_expired: bool = False

    def add_key(self, key: str, expires_at: Optional[float] = None):
        """Add an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        self.key_hashes.add(key_hash)
        if expires_at:
            self.expire_keys[key_hash] = expires_at

    def remove_key(self, key: str):
        """Remove an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        self.key_hashes.discard(key_hash)
        self.expire_keys.pop(key_hash, None)

    def is_valid(self, key: str) -> bool:
        """Check if an API key is valid."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        if key_hash not in self.key_hashes:
            return False

        # Check expiration
        if key_hash in self.expire_keys:
            if time.time() > self.expire_keys[key_hash]:
                if not self.allow_expired:
                    return False

        return True


class APIKeyAuth(AuthMiddleware):
    """API Key authentication middleware."""

    def __init__(self, config: APIKeyConfig):
        self.config = config

    async def authenticate(self, request) -> AuthResult:
        """Authenticate using API key."""
        return self.authenticate_sync(request)

    def authenticate_sync(self, request) -> AuthResult:
        """Synchronous authenticate using API key."""
        if not self.config.enabled:
            return AuthResult(success=True, authenticated=True, auth_type=AuthType.NONE)

        api_key = request.headers.get(self.config.header_name)

        if not api_key:
            return AuthResult(
                success=False,
                authenticated=False,
                error=f"Missing API key. Provide {self.config.header_name} header.",
                auth_type=AuthType.API_KEY,
            )

        if not self.config.is_valid(api_key):
            return AuthResult(
                success=False,
                authenticated=False,
                error="Invalid or expired API key",
                auth_type=AuthType.API_KEY,
            )

        return AuthResult(
            success=True,
            authenticated=True,
            client_id=api_key[:8] + "...",
            metadata={"auth_type": "api_key"},
            auth_type=AuthType.API_KEY,
        )
