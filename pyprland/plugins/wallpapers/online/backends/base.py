"""Base classes and types for wallpaper backends.

This module contains the abstract base class, data types, and helper functions
used by all wallpaper backend implementations. It is separate from __init__.py
to avoid cyclic imports when backends import these types.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar

from pyprland.httpclient import ClientError

if TYPE_CHECKING:
    from pyprland.httpclient import FallbackClientSession

# HTTP status code for successful responses
HTTP_OK = HTTPStatus.OK


@dataclass(slots=True)
class ImageInfo:
    """Metadata about a fetched image.

    Attributes:
        url: Direct URL to download the image.
        width: Image width in pixels, if known.
        height: Image height in pixels, if known.
        source: Name of the backend that provided this image.
        image_id: Unique identifier for the image from the source.
        extension: File extension (e.g., "jpg", "png").
        extra: Additional metadata from the source.
    """

    url: str
    width: int | None = None
    height: int | None = None
    source: str = ""
    image_id: str = ""
    extension: str = "jpg"
    extra: dict[str, str] = field(default_factory=dict)


class Backend(ABC):
    """Abstract base class for wallpaper backends.

    Each backend must implement fetch_image_info() to retrieve metadata
    about a random image from its source.

    Class Attributes:
        name: Unique identifier for the backend.
        supports_keywords: Whether this backend supports keyword filtering.
        base_url: Base URL for the API (for documentation).
    """

    name: ClassVar[str]
    supports_keywords: ClassVar[bool] = False
    base_url: ClassVar[str] = ""

    @abstractmethod
    async def fetch_image_info(
        self,
        session: "FallbackClientSession",
        min_width: int = 1920,
        min_height: int = 1080,
        keywords: list[str] | None = None,
    ) -> ImageInfo:
        """Fetch metadata for a random image meeting size requirements.

        Args:
            session: HTTP session for making requests.
            min_width: Minimum image width in pixels.
            min_height: Minimum image height in pixels.
            keywords: Optional list of keywords to filter images.

        Returns:
            ImageInfo with the image URL and metadata.

        Raises:
            BackendError: If the backend fails to fetch an image.
        """
        ...


class BackendError(Exception):
    """Exception raised when a backend fails to fetch an image."""

    def __init__(self, backend: str, message: str) -> None:
        """Initialize the error.

        Args:
            backend: Name of the backend that failed.
            message: Error description.
        """
        self.backend = backend
        self.message = message
        super().__init__(f"{backend}: {message}")


async def fetch_redirect_image(
    session: "FallbackClientSession",
    url: str,
    backend_name: str,
    dimensions: tuple[int, int],
    id_extractor: Callable[[str], str] | None = None,
) -> ImageInfo:
    """Fetch image info from a URL that redirects to the final image.

    Common pattern for backends like Unsplash and Picsum which redirect
    to actual image URLs. This helper handles the redirect and extracts
    the final URL.

    Args:
        session: HTTP session for making requests.
        url: Initial URL that will redirect to the image.
        backend_name: Name of the backend (for ImageInfo.source).
        dimensions: Tuple of (width, height) for the requested image.
        id_extractor: Optional function to extract image ID from final URL.

    Returns:
        ImageInfo with the resolved image URL.

    Raises:
        BackendError: On HTTP errors or network failures.
    """
    try:
        async with session.get(url, allow_redirects=True) as response:
            if response.status != HTTP_OK:
                raise BackendError(backend_name, f"HTTP {response.status}")

            final_url = str(response.url)
            image_id = id_extractor(final_url) if id_extractor else ""

            return ImageInfo(
                url=final_url,
                width=dimensions[0],
                height=dimensions[1],
                source=backend_name,
                image_id=image_id,
                extension="jpg",
            )
    except ClientError as e:
        raise BackendError(backend_name, str(e)) from e
