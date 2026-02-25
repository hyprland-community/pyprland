"""File-based image cache with TTL support."""

import hashlib
import time
from pathlib import Path

from ...aioops import aiopen

# Dual-hash key format: {16-char source hash}_{16-char settings hash}
# Total length: 16 + 1 (underscore) + 16 = 33
DUAL_HASH_KEY_LENGTH = 33
DUAL_HASH_SEPARATOR_POS = 16


class ImageCache:
    """File-based image cache with configurable TTL and cleanup.

    Attributes:
        cache_dir: Directory where cached files are stored.
        ttl: Time-to-live in seconds for cached files. None means forever.
        max_size: Maximum cache size in bytes. None means unlimited.
        max_count: Maximum number of cached files. None means unlimited.
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl: int | None = None,
        max_size: int | None = None,
        max_count: int | None = None,
    ) -> None:
        """Initialize the image cache.

        Args:
            cache_dir: Directory for cached files.
            ttl: Time-to-live in seconds. None means cached files never expire.
            max_size: Maximum total cache size in bytes. None means unlimited.
            max_count: Maximum number of cached files. None means unlimited.
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size
        self.max_count = max_count
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, key: str) -> str:
        """Generate a hash from the cache key.

        If the key is already in dual-hash format ({16chars}_{16chars}),
        returns it as-is to preserve the source hash for orphan detection.

        Args:
            key: The cache key to hash.

        Returns:
            A hex digest of the key, or the key itself if already hashed.
        """
        # Check if key is already in dual-hash format: exactly 33 chars with underscore at position 16
        if len(key) == DUAL_HASH_KEY_LENGTH and key[DUAL_HASH_SEPARATOR_POS] == "_":
            return key
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    def get_path(self, key: str, extension: str = "jpg") -> Path:
        """Get the cache file path for a given key.

        Args:
            key: Unique identifier for the cached item.
            extension: File extension for the cached file.

        Returns:
            Path to the cached file (may or may not exist).
        """
        filename = f"{self._hash_key(key)}.{extension}"
        return self.cache_dir / filename

    def is_valid(self, path: Path) -> bool:
        """Check if a cached file exists and is not expired.

        Args:
            path: Path to the cached file.

        Returns:
            True if the file exists and is within TTL, False otherwise.
        """
        if not path.exists():
            return False

        if self.ttl is None:
            return True

        mtime = path.stat().st_mtime
        age = time.time() - mtime
        return age < self.ttl

    def get(self, key: str, extension: str = "jpg") -> Path | None:
        """Get a cached file if it exists and is valid.

        Args:
            key: Unique identifier for the cached item.
            extension: File extension for the cached file.

        Returns:
            Path to the cached file if valid, None otherwise.
        """
        path = self.get_path(key, extension)
        if self.is_valid(path):
            return path
        return None

    async def store(self, key: str, data: bytes, extension: str = "jpg") -> Path:
        """Store data in the cache.

        Args:
            key: Unique identifier for the cached item.
            data: Binary data to cache.
            extension: File extension for the cached file.

        Returns:
            Path to the cached file.
        """
        path = self.get_path(key, extension)
        async with aiopen(path, "wb") as f:
            await f.write(data)

        # Auto-cleanup if any limit is set
        if self.max_size is not None or self.max_count is not None:
            self._auto_cleanup()

        return path

    def _get_cache_size(self) -> int:
        """Calculate total size of cached files.

        Returns:
            Total size in bytes.
        """
        total = 0
        for file in self.cache_dir.iterdir():
            if file.is_file():
                total += file.stat().st_size
        return total

    def _get_cache_count(self) -> int:
        """Count cached files.

        Returns:
            Number of cached files.
        """
        return sum(1 for f in self.cache_dir.iterdir() if f.is_file())

    def _is_under_limits(self, current_size: int, current_count: int) -> bool:
        """Check if cache is under all configured limits.

        Args:
            current_size: Current total size in bytes.
            current_count: Current number of files.

        Returns:
            True if under all limits, False otherwise.
        """
        size_ok = self.max_size is None or current_size <= self.max_size
        count_ok = self.max_count is None or current_count <= self.max_count
        return size_ok and count_ok

    def _auto_cleanup(self) -> None:
        """Automatically clean up old files if cache exceeds any limit."""
        if self.max_size is None and self.max_count is None:
            return

        current_size = self._get_cache_size()
        current_count = self._get_cache_count()

        if self._is_under_limits(current_size, current_count):
            return

        # Sort files by mtime (oldest first)
        files = sorted(
            (f for f in self.cache_dir.iterdir() if f.is_file()),
            key=lambda f: f.stat().st_mtime,
        )

        # Remove oldest files until under all limits
        for file in files:
            if self._is_under_limits(current_size, current_count):
                break
            size = file.stat().st_size
            file.unlink()
            current_size -= size
            current_count -= 1

    def cleanup(self, max_age: int | None = None) -> int:
        """Manually clean up old cached files.

        Args:
            max_age: Maximum age in seconds. Files older than this are removed.
                     If None, uses the cache's TTL setting.

        Returns:
            Number of files removed.
        """
        age_limit = max_age if max_age is not None else self.ttl
        if age_limit is None:
            return 0

        removed = 0
        now = time.time()

        for file in self.cache_dir.iterdir():
            if not file.is_file():
                continue
            mtime = file.stat().st_mtime
            if now - mtime > age_limit:
                file.unlink()
                removed += 1

        return removed

    def clear(self) -> int:
        """Remove all cached files.

        Returns:
            Number of files removed.
        """
        removed = 0
        for file in self.cache_dir.iterdir():
            if file.is_file():
                file.unlink()
                removed += 1
        return removed
