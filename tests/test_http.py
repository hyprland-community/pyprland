"""Tests for pyprland.httpclient fallback implementation."""

import json
import warnings
from http.client import HTTPResponse
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest
from pyprland.httpclient import (
    FallbackClientError,
    FallbackClientSession,
    FallbackClientTimeout,
    FallbackResponse,
    reset_fallback_warning,
)

# HTTP status codes for tests
HTTP_OK = 200
HTTP_REDIRECT = 302
HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR = 500

# Timeout values for tests
DEFAULT_TIMEOUT = 30
CUSTOM_TIMEOUT = 60


class TestFallbackClientTimeout:
    """Tests for FallbackClientTimeout."""

    def test_default_timeout(self) -> None:
        """Test default timeout value."""
        timeout = FallbackClientTimeout()
        assert timeout.total == DEFAULT_TIMEOUT

    def test_custom_timeout(self) -> None:
        """Test custom timeout value."""
        timeout = FallbackClientTimeout(total=CUSTOM_TIMEOUT)
        assert timeout.total == CUSTOM_TIMEOUT


class TestFallbackResponse:
    """Tests for FallbackResponse."""

    def test_status_and_url(self) -> None:
        """Test status and url attributes."""
        response = FallbackResponse(status=HTTP_OK, url="https://example.com", data=b"test")
        assert response.status == HTTP_OK
        assert response.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_json(self) -> None:
        """Test JSON parsing."""
        data = {"key": "value", "number": 42}
        response = FallbackResponse(status=HTTP_OK, url="https://example.com", data=json.dumps(data).encode())
        result = await response.json()
        assert result == data

    @pytest.mark.asyncio
    async def test_read(self) -> None:
        """Test reading binary data."""
        data = b"binary content"
        response = FallbackResponse(status=HTTP_OK, url="https://example.com", data=data)
        result = await response.read()
        assert result == data

    def test_raise_for_status_ok(self) -> None:
        """Test raise_for_status with OK status."""
        response = FallbackResponse(status=HTTP_OK, url="https://example.com", data=b"")
        response.raise_for_status()  # Should not raise

    def test_raise_for_status_redirect(self) -> None:
        """Test raise_for_status with redirect status (should not raise)."""
        response = FallbackResponse(status=HTTP_REDIRECT, url="https://example.com", data=b"")
        response.raise_for_status()  # Should not raise

    def test_raise_for_status_client_error(self) -> None:
        """Test raise_for_status with 4xx status."""
        response = FallbackResponse(status=HTTP_NOT_FOUND, url="https://example.com", data=b"")
        with pytest.raises(FallbackClientError, match="HTTP 404"):
            response.raise_for_status()

    def test_raise_for_status_server_error(self) -> None:
        """Test raise_for_status with 5xx status."""
        response = FallbackResponse(status=HTTP_SERVER_ERROR, url="https://example.com", data=b"")
        with pytest.raises(FallbackClientError, match="HTTP 500"):
            response.raise_for_status()


class TestFallbackClientSession:
    """Tests for FallbackClientSession."""

    @pytest.fixture(autouse=True)
    def reset_warning(self) -> None:
        """Reset fallback warning before each test."""
        reset_fallback_warning()

    def _mock_response(self, data: bytes, status: int = HTTP_OK, url: str = "https://example.com") -> MagicMock:
        """Create a mock urllib response."""
        mock = MagicMock(spec=HTTPResponse)
        mock.status = status
        mock.url = url
        mock.read.return_value = data
        return mock

    @pytest.mark.asyncio
    async def test_get_simple(self) -> None:
        """Test simple GET request."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response(b'{"result": "ok"}')

            session = FallbackClientSession()
            async with session.get("https://example.com/api") as response:
                assert response.status == HTTP_OK
                data = await response.json()
                assert data == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_get_with_params(self) -> None:
        """Test GET request with query parameters."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response(b"ok")

            session = FallbackClientSession()
            async with session.get("https://example.com/search", params={"q": "test", "page": "1"}) as response:
                assert response.status == HTTP_OK

            # Verify URL was built with params
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert "q=test" in request.full_url
            assert "page=1" in request.full_url

    @pytest.mark.asyncio
    async def test_get_with_headers(self) -> None:
        """Test GET request with custom headers."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response(b"ok")

            session = FallbackClientSession(headers={"User-Agent": "test-agent"})
            async with session.get("https://example.com", headers={"X-Custom": "value"}) as response:
                assert response.status == HTTP_OK

            # Verify headers were set
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.get_header("User-agent") == "test-agent"
            assert request.get_header("X-custom") == "value"

    @pytest.mark.asyncio
    async def test_get_with_timeout(self) -> None:
        """Test GET request with timeout configuration."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response(b"ok")

            session = FallbackClientSession(timeout=FallbackClientTimeout(total=CUSTOM_TIMEOUT))
            async with session.get("https://example.com") as response:
                assert response.status == HTTP_OK

            # Verify timeout was passed
            call_args = mock_urlopen.call_args
            assert call_args[1]["timeout"] == CUSTOM_TIMEOUT

    @pytest.mark.asyncio
    async def test_http_error_returns_response(self) -> None:
        """Test that HTTP errors return a response with error status."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            error_response = BytesIO(b"Not Found")
            mock_urlopen.side_effect = HTTPError(
                url="https://example.com",
                code=HTTP_NOT_FOUND,
                msg="Not Found",
                hdrs={},  # type: ignore[arg-type]
                fp=error_response,
            )

            session = FallbackClientSession()
            async with session.get("https://example.com") as response:
                assert response.status == HTTP_NOT_FOUND

    @pytest.mark.asyncio
    async def test_network_error_raises_client_error(self) -> None:
        """Test that network errors raise ClientError."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("Connection refused")

            session = FallbackClientSession()
            with pytest.raises(FallbackClientError, match="Connection refused"):
                async with session.get("https://example.com"):
                    pass

    @pytest.mark.asyncio
    async def test_timeout_raises_client_error(self) -> None:
        """Test that timeout raises ClientError."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError()

            session = FallbackClientSession()
            with pytest.raises(FallbackClientError, match="timed out"):
                async with session.get("https://example.com"):
                    pass

    @pytest.mark.asyncio
    async def test_session_context_manager(self) -> None:
        """Test session as async context manager."""
        with patch("pyprland.httpclient.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response(b"ok")

            async with FallbackClientSession() as session:
                assert not session.closed
                async with session.get("https://example.com") as response:
                    assert response.status == HTTP_OK

            assert session.closed

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test session close."""
        session = FallbackClientSession()
        assert not session.closed
        await session.close()
        assert session.closed

    def test_warns_on_first_use(self) -> None:
        """Test that warning is emitted on first use."""
        with pytest.warns(UserWarning, match="aiohttp not installed"):
            FallbackClientSession()

    def test_warns_only_once(self) -> None:
        """Test that warning is only emitted once."""
        with pytest.warns(UserWarning, match="aiohttp not installed"):
            FallbackClientSession()

        # Second instantiation should not warn
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            FallbackClientSession()  # Should not raise


class TestFallbackClientError:
    """Tests for FallbackClientError."""

    def test_is_exception(self) -> None:
        """Test that FallbackClientError is an Exception."""
        assert issubclass(FallbackClientError, Exception)

    def test_message(self) -> None:
        """Test error message."""
        error = FallbackClientError("Something went wrong")
        assert str(error) == "Something went wrong"
