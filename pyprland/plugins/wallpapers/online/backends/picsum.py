"""Picsum Photos backend for random images."""

# pylint: disable=duplicate-code  # Uses shared fetch_redirect_image pattern

import random
from typing import TYPE_CHECKING, ClassVar

from . import register_backend
from .base import Backend, ImageInfo, fetch_redirect_image

if TYPE_CHECKING:
    from pyprland.httpclient import FallbackClientSession


@register_backend
class PicsumBackend(Backend):
    """Backend for Picsum Photos - Lorem Ipsum for photos.

    Picsum provides random placeholder images at requested dimensions.
    No API key required. Does not support keyword filtering.

    See: https://picsum.photos/
    """

    name: ClassVar[str] = "picsum"
    supports_keywords: ClassVar[bool] = False
    base_url: ClassVar[str] = "https://picsum.photos"

    @staticmethod
    def _extract_id(url: str) -> str:
        """Extract image ID from picsum URL.

        Args:
            url: Final URL after redirect (e.g., https://i.picsum.photos/id/123/...).

        Returns:
            Image ID or empty string if not found.
        """
        if "/id/" in url:
            parts = url.split("/id/")
            if len(parts) > 1:
                return parts[1].split("/")[0]
        return ""

    async def fetch_image_info(
        self,
        session: "FallbackClientSession",
        min_width: int = 1920,
        min_height: int = 1080,
        keywords: list[str] | None = None,  # noqa: ARG002
    ) -> ImageInfo:
        """Fetch a random image from Picsum.

        Args:
            session: HTTP session for making requests.
            min_width: Minimum image width in pixels.
            min_height: Minimum image height in pixels.
            keywords: Ignored - Picsum doesn't support keywords.

        Returns:
            ImageInfo with the image URL.

        Raises:
            BackendError: If Picsum fails to return an image.
        """
        # Add random seed to get different images
        seed = random.randint(1, 1000000)
        url = f"{self.base_url}/seed/{seed}/{min_width}/{min_height}"

        return await fetch_redirect_image(
            session=session,
            url=url,
            backend_name=self.name,
            dimensions=(min_width, min_height),
            id_extractor=self._extract_id,
        )
