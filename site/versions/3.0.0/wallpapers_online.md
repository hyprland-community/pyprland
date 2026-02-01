---
---

# Online Wallpapers

Pyprland can fetch wallpapers from free online sources without requiring API keys. When `online_ratio` is set, each wallpaper change has a chance to fetch a new image from the configured backends. If a fetch fails, it falls back to local images.

Downloaded images are stored in the `online_folder` subfolder and become part of your local collection for future use.

> [!note]
> Online fetching requires `online_ratio > 0`. If `online_backends` is empty, online fetching is disabled.

## Configuration

| Option | Description |
|--------|-------------|
| `online_ratio` · *float* · =`0.0` | Probability of fetching online (0.0-1.0) |
| `online_backends` · *list* · =`["unsplash", "picsum", "wallhaven", "reddit"]` | Enabled online backends |
| `online_keywords` · *list* | Keywords to filter online images |
| `online_folder` · *str* · =`"online"` | Subfolder for downloaded online images |


### `online_ratio` *float* · =`0.0` {#config-online-ratio}

Probability (0.0 to 1.0) of fetching a wallpaper from online sources instead of local files. Set to `0.0` to disable online fetching or `1.0` to always fetch online.

```toml
online_ratio = 0.3  # 30% chance of fetching online
```

### `online_backends` *list* · =`["unsplash", "picsum", "wallhaven", "reddit"]` {#config-online-backends}

List of online backends to use. Defaults to all available backends. Set to an empty list to disable online fetching. See [Available Backends](#available-backends) for details.

```toml
online_backends = ["unsplash", "wallhaven"]  # Use only these two
```

### `online_keywords` *list* {#config-online-keywords}

Keywords to filter online wallpaper searches. Not all backends support keywords.

```toml
online_keywords = ["nature", "landscape", "mountains"]
```

### `online_folder` *str* · =`"online"` {#config-online-folder}

Subfolder name within `path` where downloaded online images are stored. These images persist and become part of your local collection.

```toml
online_folder = "online"  # Stores in {path}/online/
```

## Cache Management

| Option | Description |
|--------|-------------|
| `cache_days` · *int* · =`0` | Days to keep cached images (0 = forever) |
| `cache_max_mb` · *int* · =`100` | Maximum cache size in MB (0 = unlimited) |
| `cache_max_images` · *int* · =`0` | Maximum number of cached images (0 = unlimited) |


### `cache_days` *int* · =`0` {#config-cache-days}

Days to keep cached images before automatic cleanup. Set to `0` to keep images forever.

```toml
cache_days = 30  # Remove cached images older than 30 days
```

### `cache_max_mb` *int* · =`100` {#config-cache-max-mb}

Maximum cache size in megabytes. When exceeded, oldest files are removed first. Set to `0` for unlimited.

```toml
cache_max_mb = 500  # Limit cache to 500 MB
```

### `cache_max_images` *int* · =`0` {#config-cache-max-images}

Maximum number of cached images. When exceeded, oldest files are removed first. Set to `0` for unlimited.

```toml
cache_max_images = 100  # Keep at most 100 cached images
```

## Available Backends

| Backend | Keywords | Description |
|---------|:--------:|-------------|
| `unsplash` | ✓ | Unsplash Source - high quality photos |
| `wallhaven` | ✓ | Wallhaven - curated wallpapers |
| `reddit` | ✓ | Reddit - keywords map to wallpaper subreddits |
| `picsum` | ✗ | Picsum Photos - random images |
| `bing` | ✗ | Bing Daily Wallpaper |

## Example Configuration

```toml
[wallpapers]
path = "~/Pictures/wallpapers/"
online_ratio = 0.2  # 20% chance to fetch online
online_backends = ["unsplash", "wallhaven"]
online_keywords = ["nature", "minimal"]
```
