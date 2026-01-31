"""Wallhaven API backend for wallpaper images."""

import random
from typing import TYPE_CHECKING, ClassVar

from pyprland.httpclient import ClientError

from . import register_backend
from .base import HTTP_OK, Backend, BackendError, ImageInfo

if TYPE_CHECKING:
    from pyprland.httpclient import FallbackClientSession


@register_backend
class WallhavenBackend(Backend):
    """Backend for Wallhaven - dedicated wallpaper site with extensive filters.

    Wallhaven provides high-quality wallpapers with filtering by resolution,
    category, and search terms. No API key required for SFW content.

    See: https://wallhaven.cc/help/api
    """

    name: ClassVar[str] = "wallhaven"
    supports_keywords: ClassVar[bool] = True
    base_url: ClassVar[str] = "https://wallhaven.cc/api/v1"

    async def fetch_image_info(
        self,
        session: "FallbackClientSession",
        min_width: int = 1920,
        min_height: int = 1080,
        keywords: list[str] | None = None,
    ) -> ImageInfo:
        """Fetch a random wallpaper from Wallhaven.

        Args:
            session: HTTP session for making requests.
            min_width: Minimum image width in pixels.
            min_height: Minimum image height in pixels.
            keywords: Optional search terms.

        Returns:
            ImageInfo with the wallpaper URL.

        Raises:
            BackendError: If Wallhaven fails to return an image.
        """
        # Build search parameters
        params: dict[str, str] = {
            "categories": "100",  # General only (not anime/people)
            "purity": "100",  # SFW only
            "sorting": "random",
            "atleast": f"{min_width}x{min_height}",
        }

        if keywords:
            params["q"] = " ".join(keywords)

        try:
            async with session.get(f"{self.base_url}/search", params=params) as response:
                if response.status != HTTP_OK:
                    raise BackendError(self.name, f"HTTP {response.status}")

                data = await response.json()

                if not data.get("data"):
                    raise BackendError(self.name, "No images found matching criteria")

                # Pick a random image from results
                image = random.choice(data["data"])

                # Determine extension from path
                path = image.get("path", "")
                extension = path.rsplit(".", 1)[-1] if "." in path else "jpg"

                return ImageInfo(
                    url=image["path"],
                    width=image.get("dimension_x"),
                    height=image.get("dimension_y"),
                    source=self.name,
                    image_id=image.get("id", ""),
                    extension=extension,
                    extra={
                        "category": image.get("category", ""),
                        "views": str(image.get("views", "")),
                        "favorites": str(image.get("favorites", "")),
                    },
                )
        except ClientError as e:
            raise BackendError(self.name, str(e)) from e
        except (KeyError, ValueError) as e:
            raise BackendError(self.name, f"Invalid response: {e}") from e
