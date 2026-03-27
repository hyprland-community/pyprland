"""aiohttp.web server for the pyprland GUI.

Defines HTTP routes that serve the Vue.js frontend and expose the
JSON API consumed by it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web

from . import api

__all__ = ["create_app"]

# Pre-built Vue app lives here (committed to repo)
STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
#  API routes
# ---------------------------------------------------------------------------


async def handle_get_plugins(_request: web.Request) -> web.Response:
    """GET /api/plugins — list all plugins with schema metadata."""
    data = api.get_plugins_schema()
    return web.json_response(data)


async def handle_get_config(_request: web.Request) -> web.Response:
    """GET /api/config — return current configuration."""
    data = api.get_config()
    return web.json_response(data)


async def handle_validate(request: web.Request) -> web.Response:
    """POST /api/validate — validate config without saving."""
    body = await request.json()
    config: dict[str, Any] = body.get("config", {})
    errors = api.validate_config(config)
    return web.json_response({"ok": not errors, "errors": errors})


async def handle_save(request: web.Request) -> web.Response:
    """POST /api/save — validate and save config to disk."""
    body = await request.json()
    config: dict[str, Any] = body.get("config", {})
    result = api.save_config(config)
    return web.json_response(result)


async def handle_apply(request: web.Request) -> web.Response:
    """POST /api/apply — save config and reload the daemon."""
    body = await request.json()
    config: dict[str, Any] = body.get("config", {})
    result = await api.apply_config(config)
    return web.json_response(result)


# ---------------------------------------------------------------------------
#  SPA fallback: serve static files or index.html
# ---------------------------------------------------------------------------

# Resolved once so path traversal checks are reliable
_STATIC_DIR_RESOLVED = STATIC_DIR.resolve()


async def handle_spa_fallback(request: web.Request) -> web.FileResponse:
    """Serve a static file if it exists, otherwise fall back to index.html.

    This is the standard pattern for single-page applications: real files
    (icon.png, robots.txt, etc.) are served directly, while unknown paths
    return the SPA entry point so client-side routing can take over.
    """
    tail = request.match_info.get("tail", "")
    if tail:
        candidate = (STATIC_DIR / tail).resolve()
        # Only serve if the file exists and stays inside STATIC_DIR (prevent traversal)
        if candidate.is_file() and _STATIC_DIR_RESOLVED in candidate.parents:
            return web.FileResponse(candidate)

    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise web.HTTPNotFound(text="Frontend not built. Run the Vue build first.")
    return web.FileResponse(index)


# ---------------------------------------------------------------------------
#  App factory
# ---------------------------------------------------------------------------


def create_app() -> web.Application:
    """Build and return the aiohttp Application."""
    app = web.Application()

    # API routes
    app.router.add_get("/api/plugins", handle_get_plugins)
    app.router.add_get("/api/config", handle_get_config)
    app.router.add_post("/api/validate", handle_validate)
    app.router.add_post("/api/save", handle_save)
    app.router.add_post("/api/apply", handle_apply)

    # Static assets (JS, CSS, etc.)
    if STATIC_DIR.exists() and (STATIC_DIR / "assets").exists():
        app.router.add_static("/assets", STATIC_DIR / "assets")

    # SPA fallback - serve static files or index.html for everything else
    app.router.add_get("/{tail:.*}", handle_spa_fallback)

    return app
