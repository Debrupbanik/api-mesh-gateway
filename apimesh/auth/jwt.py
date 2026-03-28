"""JWT authentication."""

from dataclasses import dataclass
from typing import Optional, Any, Callable
import jwt
from datetime import datetime, timezone, timedelta

from .base import AuthMiddleware, AuthResult, AuthType


@dataclass
class JWTConfig:
    """Configuration for JWT authentication."""

    enabled: bool = False
    secret_key: str = ""
    algorithm: str = "HS256"
    audience: Optional[str] = None
    issuer: Optional[str] = None
    leeway: int = 0
    verify_signature: bool = True
    verify_expiration: bool = True
    extract_token: Optional[Callable[[Any], str]] = None

    def __post_init__(self):
        if not self.secret_key and self.enabled:
            raise ValueError("JWT secret_key is required when JWT auth is enabled")


class JWTAuth(AuthMiddleware):
    """JWT authentication middleware."""

    def __init__(self, config: JWTConfig):
        self.config = config
        self._default_token_extractor = lambda req: self._extract_from_header(req)

    def _extract_from_header(self, request) -> Optional[str]:
        """Extract JWT from Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _extract_token(self, request) -> Optional[str]:
        """Extract token from request."""
        if self.config.extract_token:
            return self.config.extract_token(request)
        return self._default_token_extractor(request)

    async def authenticate(self, request) -> AuthResult:
        """Authenticate using JWT."""
        return self.authenticate_sync(request)

    def authenticate_sync(self, request) -> AuthResult:
        """Synchronous authenticate using JWT."""
        if not self.config.enabled:
            return AuthResult(success=True, authenticated=True, auth_type=AuthType.NONE)

        token = self._extract_token(request)

        if not token:
            return AuthResult(
                success=False,
                authenticated=False,
                error="Missing JWT token. Provide Authorization: Bearer <token> header.",
                auth_type=AuthType.JWT,
            )

        try:
            options = {
                "verify_signature": self.config.verify_signature,
                "verify_exp": self.config.verify_expiration,
                "verify_aud": bool(self.config.audience),
                "verify_iss": bool(self.config.issuer),
                "require_exp": False,
                "require_aud": bool(self.config.audience),
                "require_iss": bool(self.config.issuer),
                "require_nbf": False,
            }

            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
                leeway=self.config.leeway,
                options=options,
            )

            client_id = payload.get("sub", payload.get("client_id", "unknown"))

            return AuthResult(
                success=True,
                authenticated=True,
                client_id=str(client_id),
                metadata={
                    "auth_type": "jwt",
                    "payload": payload,
                },
                auth_type=AuthType.JWT,
            )

        except jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                authenticated=False,
                error="JWT token has expired",
                auth_type=AuthType.JWT,
            )
        except jwt.InvalidAudienceError:
            return AuthResult(
                success=False,
                authenticated=False,
                error="Invalid JWT audience",
                auth_type=AuthType.JWT,
            )
        except jwt.InvalidIssuerError:
            return AuthResult(
                success=False,
                authenticated=False,
                error="Invalid JWT issuer",
                auth_type=AuthType.JWT,
            )
        except jwt.InvalidTokenError as e:
            return AuthResult(
                success=False,
                authenticated=False,
                error=f"Invalid JWT token: {str(e)}",
                auth_type=AuthType.JWT,
            )

    @staticmethod
    def create_token(
        secret_key: str,
        subject: str,
        algorithm: str = "HS256",
        expires_in: timedelta = timedelta(hours=1),
        audience: Optional[str] = None,
        issuer: Optional[str] = None,
        additional_claims: dict = None,
    ) -> str:
        """Create a new JWT token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + expires_in,
        }

        if audience:
            payload["aud"] = audience
        if issuer:
            payload["iss"] = issuer
        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, secret_key, algorithm=algorithm)
