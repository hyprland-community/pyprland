"""Tests for ImageCache class."""

import os
import time

import pytest

from pyprland.plugins.wallpapers.cache import ImageCache


def test_cache_get_path(tmp_path):
    """get_path() returns deterministic path for key."""
    cache = ImageCache(cache_dir=tmp_path)
    path1 = cache.get_path("test-key", "jpg")
    path2 = cache.get_path("test-key", "jpg")
    assert path1 == path2
    assert str(path1).endswith(".jpg")


def test_cache_get_path_different_keys(tmp_path):
    """get_path() returns different paths for different keys."""
    cache = ImageCache(cache_dir=tmp_path)
    path1 = cache.get_path("key1", "jpg")
    path2 = cache.get_path("key2", "jpg")
    assert path1 != path2


def test_cache_is_valid_no_ttl(tmp_path):
    """is_valid() returns True for existing files when no TTL."""
    cache = ImageCache(cache_dir=tmp_path)
    path = tmp_path / "test.jpg"
    path.write_bytes(b"data")
    assert cache.is_valid(path) is True


def test_cache_is_valid_nonexistent(tmp_path):
    """is_valid() returns False for non-existent files."""
    cache = ImageCache(cache_dir=tmp_path)
    path = tmp_path / "nonexistent.jpg"
    assert cache.is_valid(path) is False


def test_cache_is_valid_with_ttl_fresh(tmp_path):
    """is_valid() returns True for fresh files within TTL."""
    cache = ImageCache(cache_dir=tmp_path, ttl=60)
    path = tmp_path / "test.jpg"
    path.write_bytes(b"data")
    assert cache.is_valid(path) is True


def test_cache_is_valid_with_ttl_expired(tmp_path):
    """is_valid() returns False for expired files."""
    cache = ImageCache(cache_dir=tmp_path, ttl=1)
    path = tmp_path / "test.jpg"
    path.write_bytes(b"data")
    # Set mtime to 2 seconds ago
    os.utime(path, (time.time() - 2, time.time() - 2))
    assert cache.is_valid(path) is False


def test_cache_get_hit(tmp_path):
    """get() returns path for valid cached file."""
    cache = ImageCache(cache_dir=tmp_path)
    path = cache.get_path("key", "jpg")
    path.write_bytes(b"data")
    assert cache.get("key", "jpg") == path


def test_cache_get_miss(tmp_path):
    """get() returns None for missing file."""
    cache = ImageCache(cache_dir=tmp_path)
    assert cache.get("nonexistent", "jpg") is None


def test_cache_get_expired(tmp_path):
    """get() returns None for expired file."""
    cache = ImageCache(cache_dir=tmp_path, ttl=1)
    path = cache.get_path("key", "jpg")
    path.write_bytes(b"data")
    # Set mtime to 2 seconds ago
    os.utime(path, (time.time() - 2, time.time() - 2))
    assert cache.get("key", "jpg") is None


@pytest.mark.asyncio
async def test_cache_store(tmp_path):
    """store() writes data and returns path."""
    cache = ImageCache(cache_dir=tmp_path)
    path = await cache.store("key", b"image data", "jpg")
    assert path.exists()
    assert path.read_bytes() == b"image data"


@pytest.mark.asyncio
async def test_cache_store_overwrite(tmp_path):
    """store() overwrites existing file."""
    cache = ImageCache(cache_dir=tmp_path)
    path1 = await cache.store("key", b"old data", "jpg")
    path2 = await cache.store("key", b"new data", "jpg")
    assert path1 == path2
    assert path2.read_bytes() == b"new data"


def test_cache_cleanup_with_ttl(tmp_path):
    """cleanup() removes files older than TTL."""
    cache = ImageCache(cache_dir=tmp_path, ttl=1)
    old_file = tmp_path / "old.jpg"
    new_file = tmp_path / "new.jpg"

    old_file.write_bytes(b"old data")
    os.utime(old_file, (time.time() - 2, time.time() - 2))

    new_file.write_bytes(b"new data")

    removed = cache.cleanup()

    assert removed == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_cache_cleanup_no_ttl(tmp_path):
    """cleanup() removes nothing when no TTL is set."""
    cache = ImageCache(cache_dir=tmp_path)
    old_file = tmp_path / "old.jpg"
    old_file.write_bytes(b"data")
    os.utime(old_file, (time.time() - 1000, time.time() - 1000))

    removed = cache.cleanup()

    assert removed == 0
    assert old_file.exists()


def test_cache_cleanup_with_custom_max_age(tmp_path):
    """cleanup() uses provided max_age over TTL."""
    cache = ImageCache(cache_dir=tmp_path, ttl=1000)  # High TTL
    old_file = tmp_path / "old.jpg"
    old_file.write_bytes(b"data")
    os.utime(old_file, (time.time() - 5, time.time() - 5))

    # Use custom max_age of 1 second
    removed = cache.cleanup(max_age=1)

    assert removed == 1
    assert not old_file.exists()


def test_cache_auto_cleanup_max_size(tmp_path):
    """Auto-cleanup removes oldest files when max_size exceeded."""
    cache = ImageCache(cache_dir=tmp_path, max_size=100)

    # Create files totaling > 100 bytes
    old_file = tmp_path / "old.jpg"
    new_file = tmp_path / "new.jpg"

    old_file.write_bytes(b"x" * 60)
    os.utime(old_file, (time.time() - 10, time.time() - 10))

    new_file.write_bytes(b"y" * 60)

    cache._auto_cleanup()

    # Old file should be removed, new file kept
    assert not old_file.exists()
    assert new_file.exists()


def test_cache_auto_cleanup_max_count(tmp_path):
    """Auto-cleanup removes oldest files when max_count exceeded."""
    cache = ImageCache(cache_dir=tmp_path, max_count=1)

    old_file = tmp_path / "old.jpg"
    new_file = tmp_path / "new.jpg"

    old_file.write_bytes(b"old")
    os.utime(old_file, (time.time() - 10, time.time() - 10))

    new_file.write_bytes(b"new")

    cache._auto_cleanup()

    assert not old_file.exists()
    assert new_file.exists()


def test_cache_auto_cleanup_under_limits(tmp_path):
    """Auto-cleanup does nothing when under all limits."""
    cache = ImageCache(cache_dir=tmp_path, max_size=1000, max_count=10)

    file1 = tmp_path / "a.jpg"
    file2 = tmp_path / "b.jpg"

    file1.write_bytes(b"data1")
    file2.write_bytes(b"data2")

    cache._auto_cleanup()

    # Both files should still exist
    assert file1.exists()
    assert file2.exists()


def test_cache_auto_cleanup_no_limits(tmp_path):
    """Auto-cleanup does nothing when no limits are set."""
    cache = ImageCache(cache_dir=tmp_path)

    file1 = tmp_path / "a.jpg"
    file1.write_bytes(b"data")

    cache._auto_cleanup()

    assert file1.exists()


def test_cache_clear(tmp_path):
    """clear() removes all cached files."""
    cache = ImageCache(cache_dir=tmp_path)

    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "b.jpg").write_bytes(b"b")
    (tmp_path / "c.png").write_bytes(b"c")

    removed = cache.clear()

    assert removed == 3
    assert not (tmp_path / "a.jpg").exists()
    assert not (tmp_path / "b.jpg").exists()
    assert not (tmp_path / "c.png").exists()


def test_cache_clear_empty(tmp_path):
    """clear() returns 0 for empty cache."""
    cache = ImageCache(cache_dir=tmp_path)
    removed = cache.clear()
    assert removed == 0


def test_cache_hash_key(tmp_path):
    """_hash_key() generates consistent short hashes."""
    cache = ImageCache(cache_dir=tmp_path)

    # Same key should produce same hash
    hash1 = cache._hash_key("test-key")
    hash2 = cache._hash_key("test-key")
    assert hash1 == hash2

    # Different keys should produce different hashes
    hash3 = cache._hash_key("other-key")
    assert hash1 != hash3

    # Hash should be 32 characters (truncated SHA256)
    assert len(hash1) == 32


def test_cache_get_cache_size(tmp_path):
    """_get_cache_size() returns total size of cached files."""
    cache = ImageCache(cache_dir=tmp_path)

    (tmp_path / "a.jpg").write_bytes(b"a" * 100)
    (tmp_path / "b.jpg").write_bytes(b"b" * 50)

    size = cache._get_cache_size()
    assert size == 150


def test_cache_get_cache_count(tmp_path):
    """_get_cache_count() returns number of cached files."""
    cache = ImageCache(cache_dir=tmp_path)

    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "b.jpg").write_bytes(b"b")
    (tmp_path / "c.png").write_bytes(b"c")

    count = cache._get_cache_count()
    assert count == 3
