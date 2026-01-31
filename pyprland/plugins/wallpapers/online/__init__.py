"""Online wallpaper fetcher with multiple backend support.

This module provides an async interface to fetch wallpaper images from
various free online sources without requiring API keys or subscriptions.

Example usage:
    from pyprland.plugins.wallpapers.online import OnlineFetcher

    async def main():
        fetcher = OnlineFetcher(backends=["unsplash", "wallhaven"])
        image_path = await fetcher.get_image(min_width=1920, min_height=1080)
        print(f"Downloaded: {image_path}")

Available backends:
    - unsplash: Unsplash Source (keywords supported)
    - picsum: Picsum Photos (no keywords)
    - wallhaven: Wallhaven API (keywords supported)
    - reddit: Reddit JSON API (keywords mapped to subreddits)
    - bing: Bing Daily Wallpaper (no keywords)
"""

import logging
import random
from pathlib import Path
from typing import Any, Self

from pyprland.constants import DEFAULT_WALLPAPER_HEIGHT, DEFAULT_WALLPAPER_WIDTH
from pyprland.httpclient import ClientError, ClientSession, ClientTimeout

from ..cache import ImageCache
from .backends import (
    Backend,
    BackendError,
    ImageInfo,
    get_available_backends,
    get_backend,
)

__all__ = [
    "BackendError",
    "ImageInfo",
    "NoBackendAvailableError",
    "OnlineFetcher",
    "get_available_backends",
]

# Default logger
_log = logging.getLogger(__name__)


class NoBackendAvailableError(Exception):
    """Raised when no backends are available or all backends failed."""

    def __init__(self, message: str = "No backends available", tried: list[str] | None = None) -> None:
        """Initialize the error.

        Args:
            message: Error description.
            tried: List of backends that were tried.
        """
        self.tried = tried or []
        super().__init__(message)


class OnlineFetcher:
    """Async wallpaper fetcher supporting multiple online backends.

    Fetches random wallpaper images from various free online sources,
    caches them locally, and returns the file path.

    Attributes:
        backends: List of enabled backend names.
        cache: ImageCache instance for caching downloaded images.
    """

    def __init__(
        self,
        backends: list[str] | None = None,
        *,
        cache: ImageCache,
        log: logging.Logger | None = None,
    ) -> None:
        """Initialize the online fetcher.

        Args:
            backends: List of backend names to enable. None means all available.
            cache: ImageCache instance for caching downloaded images.
            log: Logger instance. Defaults to module logger.
        """
        self._log = log or _log

        # Validate and set up backends
        available = get_available_backends()
        if backends is None:
            self._backend_names = available
        else:
            invalid = [b for b in backends if b not in available]
            if invalid:
                msg = f"Unknown backends: {invalid}. Available: {available}"
                raise ValueError(msg)
            self._backend_names = backends

        if not self._backend_names:
            msg = "At least one backend must be enabled"
            raise ValueError(msg)

        # Initialize backends
        self._backends: dict[str, Backend] = {name: get_backend(name) for name in self._backend_names}

        # Use provided cache
        self.cache = cache

        # Track session for connection reuse
        self._session: Any = None

    @property
    def backends(self) -> list[str]:
        """List of enabled backend names."""
        return list(self._backend_names)

    @property
    def available_backends(self) -> list[str]:
        """List of all available backend names."""
        return get_available_backends()

    async def _get_session(self) -> Any:
        """Get or create an HTTP session.

        Returns:
            HTTP ClientSession.
        """
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                timeout=ClientTimeout(total=30),
                headers={"User-Agent": "pyprland-wallpaper-fetcher/1.0"},
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()

    def _select_backends(self, backend: str | None) -> list[str]:
        """Select which backends to try.

        Args:
            backend: Specific backend name, or None for all backends.

        Returns:
            List of backend names to try in order.

        Raises:
            ValueError: If specified backend is not enabled.
        """
        if backend is not None:
            if backend not in self._backends:
                msg = f"Backend '{backend}' not enabled. Enabled: {self.backends}"
                raise ValueError(msg)
            return [backend]
        # Randomize order for load distribution
        backends_to_try = list(self._backend_names)
        random.shuffle(backends_to_try)
        return backends_to_try

    async def _try_backend(
        self,
        session: Any,
        backend_name: str,
        *,
        min_width: int,
        min_height: int,
        keywords: list[str] | None,
    ) -> Path | None:
        """Try fetching an image from a single backend.

        Args:
            session: HTTP session.
            backend_name: Name of the backend to try.
            min_width: Minimum image width.
            min_height: Minimum image height.
            keywords: Optional search keywords.

        Returns:
            Path to cached image if successful, None if failed.
        """
        backend_instance = self._backends[backend_name]
        self._log.debug("Trying backend: %s", backend_name)

        info = await backend_instance.fetch_image_info(
            session=session,
            min_width=min_width,
            min_height=min_height,
            keywords=keywords,
        )

        # Check cache first
        cache_key = f"{info.source}:{info.image_id}:{info.url}"
        cached_path = self.cache.get(cache_key, info.extension)
        if cached_path:
            self._log.debug("Cache hit: %s", cached_path)
            return cached_path

        # Download image
        image_data = await self._download_image(session, info.url)

        # Store in cache
        cached_path = await self.cache.store(cache_key, image_data, info.extension)
        self._log.info("Downloaded from %s: %s", backend_name, cached_path)
        return cached_path

    async def get_image(
        self,
        min_width: int = DEFAULT_WALLPAPER_WIDTH,
        min_height: int = DEFAULT_WALLPAPER_HEIGHT,
        keywords: list[str] | None = None,
        backend: str | None = None,
    ) -> Path:
        """Fetch and cache a random wallpaper image.

        Tries backends in random order until one succeeds. Downloaded images
        are cached locally and the file path is returned.

        Args:
            min_width: Minimum image width in pixels.
            min_height: Minimum image height in pixels.
            keywords: Optional keywords to filter images (backend-dependent).
            backend: Force a specific backend. None picks randomly.

        Returns:
            Path to the cached image file.

        Raises:
            NoBackendAvailableError: If all backends fail.
            ValueError: If specified backend is not enabled.
        """
        session = await self._get_session()
        backends_to_try = self._select_backends(backend)

        tried: list[str] = []
        last_error: Exception | None = None

        for backend_name in backends_to_try:
            tried.append(backend_name)
            try:
                result = await self._try_backend(
                    session,
                    backend_name,
                    min_width=min_width,
                    min_height=min_height,
                    keywords=keywords,
                )
                if result:
                    return result
            except BackendError as e:
                self._log.warning("Backend %s failed: %s", backend_name, e.message)
                last_error = e
            except ClientError as e:
                self._log.warning("Network error with %s: %s", backend_name, e)
                last_error = e

        # All backends failed
        msg = f"All backends failed. Tried: {tried}"
        raise NoBackendAvailableError(msg, tried=tried) from last_error

    async def _download_image(self, session: Any, url: str) -> bytes:
        """Download an image from a URL.

        Args:
            session: HTTP session.
            url: Image URL.

        Returns:
            Image data as bytes.

        Raises:
            ClientError: On network errors.
        """
        async with session.get(url) as response:
            response.raise_for_status()
            data: bytes = await response.read()
            return data
