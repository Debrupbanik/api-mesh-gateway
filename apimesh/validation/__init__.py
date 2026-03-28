"""Request/Response validation module."""

from typing import Any, Callable, Optional, Type
from pydantic import BaseModel, ValidationError
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RequestValidator:
    """Validate incoming requests against Pydantic models."""

    def __init__(self, model: Optional[Type[BaseModel]] = None):
        self.model = model

    async def validate(self, request: Request) -> tuple[bool, Any, str]:
        """Validate request body against model.

        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        body = await request.json()
        return self._validate_data(body)

    def validate_sync(self, data: Any) -> tuple[bool, Any, str]:
        """Synchronous validation of data."""
        return self._validate_data(data)

    def _validate_data(self, data: Any) -> tuple[bool, Any, str]:
        """Internal validation logic."""
        if not self.model:
            return True, None, ""

        try:
            validated = self.model(**data)
            return True, validated, ""
        except ValidationError as e:
            errors = e.errors()
            return False, None, str(errors)
        except Exception as e:
            return False, None, f"Invalid data: {str(e)}"


class ResponseValidator:
    """Validate outgoing responses against Pydantic models."""

    def __init__(self, model: Optional[Type[BaseModel]] = None):
        self.model = model

    def validate(self, response_data: Any) -> tuple[bool, Any, str]:
        """Validate response data against model.

        Returns:
            Tuple of (is_valid, validated_data, error_message)
        """
        if not self.model:
            return True, response_data, ""

        try:
            if isinstance(response_data, dict):
                validated = self.model(**response_data)
            else:
                validated = self.model.model_validate(response_data)
            return True, validated, ""
        except ValidationError as e:
            return False, response_data, str(e.errors())


class ValidationMiddleware:
    """Middleware for request/response validation."""

    def __init__(
        self,
        request_model: Optional[Type[BaseModel]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ):
        self.request_validator = RequestValidator(request_model)
        self.response_validator = ResponseValidator(response_model)

    async def validate_request(self, request: Request) -> tuple[bool, Any, str]:
        """Validate incoming request."""
        return await self.request_validator.validate(request)

    def validate_response(self, response_data: Any) -> tuple[bool, Any, str]:
        """Validate outgoing response."""
        return self.response_validator.validate(response_data)


def validate_query_params(
    model: Type[BaseModel], request: Request
) -> tuple[bool, Any, str]:
    """Validate query parameters against a Pydantic model.

    Returns:
        Tuple of (is_valid, validated_data, error_message)
    """
    try:
        params = dict(request.query_params)
        validated = model(**params)
        return True, validated, ""
    except ValidationError as e:
        return False, None, str(e.errors())


def validate_path_params(
    model: Type[BaseModel], path_params: dict
) -> tuple[bool, Any, str]:
    """Validate path parameters against a Pydantic model.

    Returns:
        Tuple of (is_valid, validated_data, error_message)
    """
    try:
        validated = model(**path_params)
        return True, validated, ""
    except ValidationError as e:
        return False, None, str(e.errors())
