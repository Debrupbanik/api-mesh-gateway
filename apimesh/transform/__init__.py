"""Request/Response transformation module."""

from typing import Any, Callable, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RequestTransformer:
    """Transform incoming requests before forwarding."""

    def __init__(
        self,
        add_headers: Optional[Dict[str, str]] = None,
        remove_headers: Optional[list[str]] = None,
        transform_body: Optional[Callable[[Any], Any]] = None,
    ):
        self.add_headers = add_headers or {}
        self.remove_headers = remove_headers or []
        self.transform_body = transform_body

    def transform_headers(self, headers: dict) -> dict:
        """Transform request headers."""
        for header in self.remove_headers:
            headers.pop(header, None)

        headers.update(self.add_headers)

        return headers

    def transform_body(self, body: Any) -> Any:
        """Transform request body."""
        if self.transform_body:
            return self.transform_body(body)
        return body


class ResponseTransformer:
    """Transform backend responses before returning to client."""

    def __init__(
        self,
        add_headers: Optional[Dict[str, str]] = None,
        transform_body: Optional[Callable[[Any], Any]] = None,
        wrap_response: bool = False,
        wrap_key: str = "data",
    ):
        self.add_headers = add_headers or {}
        self.transform_body = transform_body
        self.wrap_response = wrap_response
        self.wrap_key = wrap_key

    def transform_headers(self, headers: dict) -> dict:
        """Transform response headers."""
        headers.update(self.add_headers)
        return headers

    def transform_body(self, body: Any) -> Any:
        """Transform response body."""
        if self.transform_body:
            body = self.transform_body(body)

        if self.wrap_response and self.wrap_key:
            body = {self.wrap_key: body}

        return body


class TransformConfig:
    """Configuration for transformations."""

    def __init__(
        self,
        request_add_headers: Optional[Dict[str, str]] = None,
        request_remove_headers: Optional[list[str]] = None,
        response_add_headers: Optional[Dict[str, str]] = None,
        response_wrap: bool = False,
        response_wrap_key: str = "data",
    ):
        self.request_transformer = RequestTransformer(
            add_headers=request_add_headers,
            remove_headers=request_remove_headers,
        )
        self.response_transformer = ResponseTransformer(
            add_headers=response_add_headers,
            wrap_response=response_wrap,
            wrap_key=response_wrap_key,
        )
