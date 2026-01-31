"""HTTP client abstraction with aiohttp fallback to urllib.

This module provides a unified HTTP client interface that uses aiohttp when
available, falling back to Python's built-in urllib otherwise. This allows
the wallpapers/online feature to work without the optional aiohttp dependency.

Usage:
    from pyprland.httpclient import ClientSession, ClientTimeout, ClientError

    async with ClientSession(timeout=ClientTimeout(total=30)) as session:
        async with session.get(url, params={"q": "test"}) as response:
            data = await response.json()

For type annotations, use the Fallback* types which define the interface:
    from pyprland.httpclient import FallbackClientSession

    def my_func(session: FallbackClientSession) -> None:
        ...
"""

from __future__ import annotations

import asyncio
import json
import warnings
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Self

# Try importing aiohttp
try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    aiohttp = None  # type: ignore[assignment]
    HAS_AIOHTTP = False

_fallback_warned = False  # pylint: disable=invalid-name

# HTTP status threshold for client/server errors
HTTP_ERROR_THRESHOLD = HTTPStatus.BAD_REQUEST  # 400


# --- Fallback Implementations ---


class FallbackClientError(Exception):
    """HTTP client error (fallback for aiohttp.ClientError)."""


class FallbackClientTimeout:
    """Timeout configuration (fallback for aiohttp.ClientTimeout)."""

    def __init__(self, total: float = 30) -> None:
        """Initialize timeout configuration.

        Args:
            total: Total timeout in seconds.
        """
        self.total = total


class FallbackResponse:
    """Response wrapper for urllib (mirrors aiohttp response interface)."""

    def __init__(self, status: int, url: str, data: bytes) -> None:
        """Initialize response.

        Args:
            status: HTTP status code.
            url: Final URL after redirects.
            data: Response body as bytes.
        """
        self.status = status
        self.url = url
        self._data = data

    async def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON data.
        """
        return json.loads(self._data.decode("utf-8"))

    async def read(self) -> bytes:
        """Read response body as bytes.

        Returns:
            Response body.
        """
        return self._data

    def raise_for_status(self) -> None:
        """Raise ClientError if status code indicates an error."""
        if self.status >= HTTP_ERROR_THRESHOLD:
            msg = f"HTTP {self.status}"
            raise FallbackClientError(msg)


class _AsyncRequestContext:
    """Async context manager that executes request on enter."""

    def __init__(self, coro_fn: Callable[[], Coroutine[Any, Any, FallbackResponse]]) -> None:
        """Initialize context manager.

        Args:
            coro_fn: Coroutine function to execute on enter.
        """
        self._coro_fn = coro_fn

    async def __aenter__(self) -> FallbackResponse:
        """Execute request and return response."""
        return await self._coro_fn()

    async def __aexit__(self, *args: object) -> None:
        """Exit context manager."""


class FallbackClientSession:
    """Minimal aiohttp.ClientSession replacement using urllib."""

    def __init__(
        self,
        timeout: FallbackClientTimeout | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize session.

        Args:
            timeout: Timeout configuration.
            headers: Default headers for all requests.
        """
        global _fallback_warned  # noqa: PLW0603
        if not _fallback_warned:
            warnings.warn(
                "aiohttp not installed, using urllib fallback (slower)",
                UserWarning,
                stacklevel=2,
            )
            _fallback_warned = True

        self._timeout = timeout.total if timeout else 30
        self._default_headers = headers or {}
        self.closed = False

    def get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        allow_redirects: bool = True,  # noqa: ARG002  # pylint: disable=unused-argument
    ) -> _AsyncRequestContext:
        """Start a GET request.

        Args:
            url: URL to request.
            params: Query parameters.
            headers: Request headers (merged with session defaults).
            allow_redirects: Whether to follow redirects (urllib always follows).

        Returns:
            Async context manager yielding the response.
        """
        # Build full URL with params
        if params:
            url = f"{url}?{urlencode(params)}"

        # Merge headers
        all_headers = {**self._default_headers, **(headers or {})}

        # Create request
        request = Request(url, headers=all_headers, method="GET")  # noqa: S310

        # Execute in thread pool
        async def _do_request() -> FallbackResponse:
            try:
                response = await asyncio.to_thread(urlopen, request, timeout=self._timeout)
                data = response.read()
                return FallbackResponse(
                    status=response.status,
                    url=response.url,  # Final URL after redirects
                    data=data,
                )
            except HTTPError as e:
                # HTTP error responses (4xx, 5xx)
                return FallbackResponse(
                    status=e.code,
                    url=url,
                    data=e.read() if e.fp else b"",
                )
            except URLError as e:
                raise FallbackClientError(str(e.reason)) from e
            except TimeoutError:
                msg = "Request timed out"
                raise FallbackClientError(msg) from None

        # Return context manager that awaits the request
        return _AsyncRequestContext(_do_request)

    async def close(self) -> None:
        """Close the session."""
        self.closed = True

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context manager."""
        await self.close()


def reset_fallback_warning() -> None:
    """Reset the fallback warning flag (for testing)."""
    global _fallback_warned  # noqa: PLW0603
    _fallback_warned = False  # pylint: disable=invalid-name


# --- Unified Exports ---

if HAS_AIOHTTP and aiohttp is not None:
    ClientSession = aiohttp.ClientSession
    ClientTimeout = aiohttp.ClientTimeout
    ClientError = aiohttp.ClientError
else:
    ClientSession = FallbackClientSession  # type: ignore[assignment,misc]
    ClientTimeout = FallbackClientTimeout  # type: ignore[assignment,misc]
    ClientError = FallbackClientError  # type: ignore[assignment,misc]

__all__ = [
    "HAS_AIOHTTP",
    "ClientError",
    "ClientSession",
    "ClientTimeout",
    "FallbackClientError",
    "FallbackClientSession",
    "FallbackClientTimeout",
    "FallbackResponse",
    "reset_fallback_warning",
]
