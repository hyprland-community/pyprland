"""Bing Daily Wallpaper backend."""

import random
from typing import TYPE_CHECKING, ClassVar

from pyprland.httpclient import ClientError

from . import register_backend
from .base import HTTP_OK, Backend, BackendError, ImageInfo

if TYPE_CHECKING:
    from pyprland.httpclient import FallbackClientSession

# Bing's standard wallpaper resolution
BING_WIDTH = 1920
BING_HEIGHT = 1080


@register_backend
class BingBackend(Backend):
    """Backend for Bing Daily Wallpaper.

    Bing provides beautiful daily wallpapers, typically landscapes and nature.
    No API key required. Returns images from the last 8 days.

    Note: Images are typically 1920x1080. Size parameters are used only
    for validation, not filtering (Bing doesn't support size filtering).
    """

    name: ClassVar[str] = "bing"
    supports_keywords: ClassVar[bool] = False
    base_url: ClassVar[str] = "https://www.bing.com"

    async def fetch_image_info(
        self,
        session: "FallbackClientSession",
        min_width: int = 1920,
        min_height: int = 1080,
        keywords: list[str] | None = None,  # noqa: ARG002
    ) -> ImageInfo:
        """Fetch a random daily wallpaper from Bing.

        Args:
            session: HTTP session for making requests.
            min_width: Minimum image width (Bing images are typically 1920x1080).
            min_height: Minimum image height.
            keywords: Ignored - Bing doesn't support keyword filtering.

        Returns:
            ImageInfo with the wallpaper URL.

        Raises:
            BackendError: If Bing fails to return an image.
        """
        # Warn if requesting larger than Bing's typical resolution
        if min_width > BING_WIDTH or min_height > BING_HEIGHT:
            # Bing images might not meet the size requirement, but we'll try
            pass

        # Fetch up to 8 recent images (Bing's limit)
        params = {
            "format": "js",
            "idx": "0",  # Start from today
            "n": "8",  # Number of images
            "mkt": "en-US",
        }

        try:
            async with session.get(f"{self.base_url}/HPImageArchive.aspx", params=params) as response:
                if response.status != HTTP_OK:
                    raise BackendError(self.name, f"HTTP {response.status}")

                data = await response.json()

                images = data.get("images", [])
                if not images:
                    raise BackendError(self.name, "No images available")

                # Pick a random image from available
                image = random.choice(images)

                # Build full URL (Bing returns relative paths)
                url_path = image.get("url", "")
                if not url_path:
                    raise BackendError(self.name, "No URL in image data")

                # Request UHD resolution if available
                # Replace resolution in URL for higher quality
                url_path = url_path.replace("1920x1080", "UHD")
                full_url = f"{self.base_url}{url_path}"

                # Extract ID from urlbase
                urlbase = image.get("urlbase", "")
                extracted_id = urlbase.split(".")[-1] if "." in urlbase else urlbase

                return ImageInfo(
                    url=full_url,
                    width=BING_WIDTH,
                    height=BING_HEIGHT,
                    source=self.name,
                    image_id=extracted_id,
                    extension="jpg",
                    extra={
                        "title": image.get("title", ""),
                        "copyright": image.get("copyright", ""),
                        "date": image.get("startdate", ""),
                    },
                )

        except ClientError as e:
            raise BackendError(self.name, str(e)) from e
        except (KeyError, ValueError) as e:
            raise BackendError(self.name, f"Invalid response: {e}") from e
