"""Tests for validation module."""

import pytest
from pydantic import BaseModel, Field
from typing import Optional

from apimesh.validation import (
    RequestValidator,
    ResponseValidator,
    validate_query_params,
    validate_path_params,
)


class MockRequest:
    """Mock request for testing."""

    def __init__(self, headers=None, query_params=None, json_body=None):
        self.headers = headers or {}
        self.query_params = query_params or {}
        self._json_body = json_body

    async def json(self):
        return self._json_body


class TestUserModel(BaseModel):
    """Test Pydantic model."""

    name: str
    email: str = Field(..., pattern=r"^[a-z]+@[a-z]+\.[a-z]+$")
    age: Optional[int] = None


class TestRequestValidator:
    """Test request validation."""

    def test_no_model(self):
        """No model means always valid."""
        validator = RequestValidator()

        is_valid, data, error = validator.validate_sync(
            MockRequest(json_body={"name": "test"})
        )

        assert is_valid is True
        assert data is None

    def test_valid_request(self):
        """Valid request should pass."""
        validator = RequestValidator(model=TestUserModel)

        is_valid, data, error = validator.validate_sync(
            {"name": "John", "email": "john@example.com", "age": 25}
        )

        assert is_valid is True
        assert data.name == "John"
        assert data.email == "john@example.com"
        assert data.age == 25

    def test_invalid_email(self):
        """Invalid email should fail."""
        validator = RequestValidator(model=TestUserModel)

        is_valid, data, error = validator.validate_sync(
            {"name": "John", "email": "invalid-email"}
        )

        assert is_valid is False
        assert "email" in error.lower()

    def test_missing_required_field(self):
        """Missing required field should fail."""
        validator = RequestValidator(model=TestUserModel)

        is_valid, data, error = validator.validate_sync(
            {"name": "John"}  # Missing email
        )

        assert is_valid is False


class TestResponseValidator:
    """Test response validation."""

    def test_no_model(self):
        """No model means always valid."""
        validator = ResponseValidator()

        is_valid, data, error = validator.validate({"key": "value"})

        assert is_valid is True
        assert data == {"key": "value"}

    def test_valid_response(self):
        """Valid response should pass."""
        validator = ResponseValidator(model=TestUserModel)

        is_valid, data, error = validator.validate(
            {"name": "John", "email": "john@example.com"}
        )

        assert is_valid is True
        assert data.name == "John"

    def test_invalid_response(self):
        """Invalid response should fail."""
        validator = ResponseValidator(model=TestUserModel)

        is_valid, data, error = validator.validate(
            {"name": "John", "email": "not-an-email"}
        )

        assert is_valid is False


class TestQueryParamValidation:
    """Test query parameter validation."""

    def test_valid_params(self):
        """Valid params should pass."""

        class QueryParams(BaseModel):
            page: int = 1
            limit: int = 10

        request = MockRequest(query_params={"page": "2", "limit": "20"})

        is_valid, data, error = validate_query_params(QueryParams, request)

        assert is_valid is True
        assert data.page == 2
        assert data.limit == 20

    def test_invalid_params(self):
        """Invalid params should fail."""

        class QueryParams(BaseModel):
            page: int

        request = MockRequest(query_params={"page": "not-a-number"})

        is_valid, data, error = validate_query_params(QueryParams, request)

        assert is_valid is False


class TestPathParamValidation:
    """Test path parameter validation."""

    def test_valid_params(self):
        """Valid path params should pass."""

        class PathParams(BaseModel):
            user_id: int
            action: str

        params = {"user_id": "123", "action": "edit"}

        is_valid, data, error = validate_path_params(PathParams, params)

        assert is_valid is True
        assert data.user_id == 123
        assert data.action == "edit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
