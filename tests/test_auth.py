"""Tests for authentication module."""

import pytest
from datetime import timedelta
import jwt as pyjwt

from apimesh.auth.api_key import APIKeyAuth, APIKeyConfig
from apimesh.auth.jwt import JWTAuth, JWTConfig


class MockRequest:
    """Mock request object for testing."""

    def __init__(self, headers=None):
        self.headers = headers or {}


class TestAPIKeyAuth:
    """Test API Key authentication."""

    def test_disabled_auth(self):
        """Disabled auth should allow all requests."""
        config = APIKeyConfig(enabled=False)
        auth = APIKeyAuth(config)

        result = auth.authenticate_sync(MockRequest())

        assert result.success is True
        assert result.authenticated is True

    def test_missing_key(self):
        """Missing API key should fail."""
        config = APIKeyConfig(enabled=True, keys=["test-key"])
        auth = APIKeyAuth(config)

        result = auth.authenticate_sync(MockRequest())

        assert result.success is False
        assert "Missing API key" in result.error

    def test_invalid_key(self):
        """Invalid API key should fail."""
        config = APIKeyConfig(enabled=True, keys=["valid-key"])
        auth = APIKeyAuth(config)

        result = auth.authenticate_sync(MockRequest({"X-API-Key": "invalid-key"}))

        assert result.success is False
        assert "Invalid" in result.error

    def test_valid_key(self):
        """Valid API key should pass."""
        config = APIKeyConfig(enabled=True)
        config.add_key("valid-key")
        auth = APIKeyAuth(config)

        result = auth.authenticate_sync(MockRequest({"X-API-Key": "valid-key"}))

        assert result.success is True
        assert result.authenticated is True
        assert result.client_id is not None


class TestJWTAuth:
    """Test JWT authentication."""

    def test_disabled_auth(self):
        """Disabled auth should allow all requests."""
        config = JWTConfig(enabled=False)
        auth = JWTAuth(config)

        result = auth.authenticate_sync(MockRequest())

        assert result.success is True
        assert result.authenticated is True

    def test_missing_token(self):
        """Missing JWT token should fail."""
        config = JWTConfig(enabled=True, secret_key="secret")
        auth = JWTAuth(config)

        result = auth.authenticate_sync(MockRequest())

        assert result.success is False
        assert "Missing JWT" in result.error

    def test_invalid_token(self):
        """Invalid JWT token should fail."""
        config = JWTConfig(enabled=True, secret_key="secret")
        auth = JWTAuth(config)

        result = auth.authenticate_sync(
            MockRequest({"Authorization": "Bearer invalid.token.here"})
        )

        assert result.success is False

    def test_valid_token(self):
        """Valid JWT token should pass."""
        secret = "test-secret-key"
        config = JWTConfig(enabled=True, secret_key=secret)
        auth = JWTAuth(config)

        token = JWTAuth.create_token(
            secret_key=secret,
            subject="test-user",
            expires_in=timedelta(hours=1),
        )

        result = auth.authenticate_sync(
            MockRequest({"Authorization": f"Bearer {token}"})
        )

        assert result.success is True
        assert result.authenticated is True
        assert result.client_id == "test-user"

    def test_expired_token(self):
        """Expired JWT token should fail."""
        secret = "test-secret-key"
        config = JWTConfig(enabled=True, secret_key=secret)
        auth = JWTAuth(config)

        token = JWTAuth.create_token(
            secret_key=secret,
            subject="test-user",
            expires_in=timedelta(seconds=-1),  # Already expired
        )

        result = auth.authenticate_sync(
            MockRequest({"Authorization": f"Bearer {token}"})
        )

        assert result.success is False
        assert "expired" in result.error.lower()

    def test_create_token(self):
        """Test token creation with additional claims."""
        secret = "test-secret"

        token = JWTAuth.create_token(
            secret_key=secret,
            subject="user123",
            expires_in=timedelta(hours=2),
            additional_claims={"role": "admin", "tenant": "acme"},
        )

        payload = pyjwt.decode(token, secret, algorithms=["HS256"])

        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["tenant"] == "acme"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
