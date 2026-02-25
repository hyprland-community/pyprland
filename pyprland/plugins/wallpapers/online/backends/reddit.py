"""Reddit JSON API backend for wallpaper images."""

import random
from typing import TYPE_CHECKING, ClassVar

from pyprland.httpclient import ClientError

from . import register_backend
from .base import HTTP_OK, Backend, BackendError, ImageInfo

if TYPE_CHECKING:
    from pyprland.httpclient import FallbackClientSession

# Subreddits with high-quality wallpapers
DEFAULT_SUBREDDITS = [
    "wallpapers",
    "wallpaper",
    "MinimalWallpaper",
]

# Mapping of keywords to relevant subreddits
KEYWORD_SUBREDDITS: dict[str, list[str]] = {
    "nature": ["EarthPorn", "natureporn", "SkyPorn"],
    "landscape": ["EarthPorn", "LandscapePhotography"],
    "city": ["CityPorn", "cityphotos"],
    "space": ["spaceporn", "astrophotography"],
    "minimal": ["MinimalWallpaper", "minimalism"],
    "dark": ["Amoledbackgrounds", "darkwallpapers"],
    "anime": ["Animewallpaper", "AnimeWallpapersSFW"],
    "art": ["ArtPorn", "ImaginaryLandscapes"],
    "car": ["carporn", "Autos"],
    "architecture": ["ArchitecturePorn", "architecture"],
}


@register_backend
class RedditBackend(Backend):
    """Backend for Reddit - community-curated wallpapers from subreddits.

    Uses Reddit's public JSON API to fetch images from wallpaper subreddits.
    No authentication required for public subreddits.

    Keywords are mapped to relevant subreddits (e.g., "nature" -> r/EarthPorn).
    """

    name: ClassVar[str] = "reddit"
    supports_keywords: ClassVar[bool] = True
    base_url: ClassVar[str] = "https://www.reddit.com"

    async def fetch_image_info(
        self,
        session: "FallbackClientSession",
        min_width: int = 1920,
        min_height: int = 1080,
        keywords: list[str] | None = None,
    ) -> ImageInfo:
        """Fetch a random wallpaper from Reddit.

        Args:
            session: HTTP session for making requests.
            min_width: Minimum image width in pixels.
            min_height: Minimum image height in pixels.
            keywords: Optional keywords mapped to subreddits.

        Returns:
            ImageInfo with the image URL.

        Raises:
            BackendError: If no suitable image is found.
        """
        # Select subreddits based on keywords
        subreddits = self._get_subreddits(keywords)
        subreddit = random.choice(subreddits)

        # Fetch posts from the subreddit
        url = f"{self.base_url}/r/{subreddit}/hot.json"
        params = {"limit": "50"}

        headers = {
            "User-Agent": "pyprland-wallpaper-fetcher/1.0",
        }

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != HTTP_OK:
                    raise BackendError(self.name, f"HTTP {response.status} from r/{subreddit}")

                data = await response.json()

                # Filter for suitable images
                candidates = self._filter_posts(data, min_width, min_height)

                if not candidates:
                    raise BackendError(self.name, f"No images found in r/{subreddit} matching size")

                # Pick a random post
                post = random.choice(candidates)

                return self._post_to_image_info(post)

        except ClientError as e:
            raise BackendError(self.name, str(e)) from e
        except (KeyError, ValueError) as e:
            raise BackendError(self.name, f"Invalid response: {e}") from e

    def _get_subreddits(self, keywords: list[str] | None) -> list[str]:
        """Get relevant subreddits based on keywords.

        Args:
            keywords: Optional list of keywords.

        Returns:
            List of subreddit names.
        """
        if not keywords:
            return DEFAULT_SUBREDDITS

        subreddits: list[str] = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in KEYWORD_SUBREDDITS:
                subreddits.extend(KEYWORD_SUBREDDITS[keyword_lower])
            else:
                # Try the keyword as a subreddit name
                subreddits.append(keyword)

        return subreddits or DEFAULT_SUBREDDITS

    def _filter_posts(
        self,
        data: dict,
        min_width: int,
        min_height: int,
    ) -> list[dict]:
        """Filter posts for suitable images.

        Args:
            data: Reddit API response data.
            min_width: Minimum width.
            min_height: Minimum height.

        Returns:
            List of suitable post data dictionaries.
        """
        candidates: list[dict] = []

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})

            # Skip non-image posts
            if post.get("is_self"):
                continue

            url = post.get("url", "")
            if not self._is_image_url(url):
                continue

            # Check dimensions if available
            preview = post.get("preview", {})
            images = preview.get("images", [])
            if images:
                source = images[0].get("source", {})
                width = source.get("width", 0)
                height = source.get("height", 0)
                if width < min_width or height < min_height:
                    continue

            candidates.append(post)

        return candidates

    def _is_image_url(self, url: str) -> bool:
        """Check if URL points to an image.

        Args:
            url: URL to check.

        Returns:
            True if URL appears to be an image.
        """
        image_extensions = (".jpg", ".jpeg", ".png", ".webp")
        image_hosts = ("i.redd.it", "i.imgur.com")

        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in image_extensions) or any(host in url_lower for host in image_hosts)

    def _post_to_image_info(self, post: dict) -> ImageInfo:
        """Convert a Reddit post to ImageInfo.

        Args:
            post: Reddit post data.

        Returns:
            ImageInfo for the post's image.
        """
        url = post.get("url", "")

        # Get dimensions from preview if available
        width = None
        height = None
        preview = post.get("preview", {})
        images = preview.get("images", [])
        if images:
            source = images[0].get("source", {})
            width = source.get("width")
            height = source.get("height")

        # Determine extension
        extension = "jpg"
        for ext in (".png", ".webp", ".jpeg", ".jpg"):
            if ext in url.lower():
                extension = ext.lstrip(".")
                break

        return ImageInfo(
            url=url,
            width=width,
            height=height,
            source=self.name,
            image_id=post.get("id", ""),
            extension=extension,
            extra={
                "title": post.get("title", ""),
                "subreddit": post.get("subreddit", ""),
                "score": str(post.get("score", 0)),
            },
        )
