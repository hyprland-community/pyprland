"""Unsplash Source backend for random images."""

import random
from typing import TYPE_CHECKING, ClassVar

from . import register_backend
from .base import Backend, ImageInfo, fetch_redirect_image

if TYPE_CHECKING:
    from pyprland.httpclient import FallbackClientSession


@register_backend
class UnsplashBackend(Backend):
    """Backend for Unsplash Source - simple URL-based random images.

    Unsplash Source provides direct image URLs without requiring an API key.
    Images are served at the requested dimensions.

    See: https://source.unsplash.com/
    """

    name: ClassVar[str] = "unsplash"
    supports_keywords: ClassVar[bool] = True
    base_url: ClassVar[str] = "https://source.unsplash.com"

    async def fetch_image_info(
        self,
        session: "FallbackClientSession",
        min_width: int = 1920,
        min_height: int = 1080,
        keywords: list[str] | None = None,
    ) -> ImageInfo:
        """Fetch a random image from Unsplash.

        Args:
            session: HTTP session for making requests.
            min_width: Minimum image width in pixels.
            min_height: Minimum image height in pixels.
            keywords: Optional keywords to filter images (e.g., ["nature", "forest"]).

        Returns:
            ImageInfo with the resolved image URL.

        Raises:
            BackendError: If Unsplash fails to return an image.
        """
        # Build URL with size and optional keywords
        url = f"{self.base_url}/random/{min_width}x{min_height}"
        if keywords:
            query = ",".join(keywords)
            url = f"{url}/?{query}"

        # Add cache buster to ensure random image
        cache_buster = random.randint(1, 1000000)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}_={cache_buster}"

        return await fetch_redirect_image(
            session=session,
            url=url,
            backend_name=self.name,
            dimensions=(min_width, min_height),
            id_extractor=self._extract_id,
        )

    @staticmethod
    def _extract_id(url: str) -> str:
        """Extract image ID from Unsplash URL.

        Args:
            url: Final URL after redirects.

        Returns:
            Image ID if found, empty string otherwise.
        """
        if "unsplash.com/photos/" in url:
            parts = url.split("photos/")
            if len(parts) > 1:
                return parts[1].split("/")[0].split("?")[0]
        return ""
