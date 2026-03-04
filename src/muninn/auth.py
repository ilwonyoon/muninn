"""Bearer token authentication middleware for Muninn HTTP transport."""

from __future__ import annotations

import hmac
import os
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Validates API key from ``x-api-key`` or ``Authorization: Bearer``.

    Rejects requests without a valid token with HTTP 401.
    Uses constant-time comparison to prevent timing attacks.
    """

    _BYPASS_PREFIXES = ("/oauth/", "/dashboard/", "/static/", "/_next/")
    _BYPASS_PATHS = ("/oauth", "/dashboard", "/favicon.ico", "/robots.txt")

    def __init__(self, app: object, api_key: str | None = None) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._api_key = api_key

    @staticmethod
    def _is_api_path(path: str) -> bool:
        return path == "/api" or path.startswith("/api/")

    @classmethod
    def _is_bypassed_path(cls, path: str) -> bool:
        return path in cls._BYPASS_PATHS or path.startswith(cls._BYPASS_PREFIXES)

    @staticmethod
    def _extract_token(request: Request) -> str:
        header_key = request.headers.get("x-api-key", "").strip()
        if header_key:
            return header_key

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.removeprefix("Bearer ").strip()

        return ""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # OAuth and static assets stay publicly accessible.
        if self._is_bypassed_path(path):
            return await call_next(request)

        configured_api_key = self._api_key or os.environ.get("MUNINN_API_KEY", "")

        # Local dev mode: allow API routes when no API key is configured.
        if not configured_api_key and self._is_api_path(path):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                {"error": "Missing or invalid Authorization header or x-api-key"},
                status_code=401,
            )

        if not hmac.compare_digest(token, configured_api_key):
            return JSONResponse(
                {"error": "Invalid API key"},
                status_code=401,
            )

        return await call_next(request)


def create_authenticated_app(
    mcp: FastMCP,
    api_key: str,
    *,
    extra_routes: list | None = None,
) -> object:
    """Wrap the MCP streamable HTTP app with Bearer token authentication.

    Returns a Starlette application with the auth middleware applied.
    The MCP app's lifespan context is forwarded so the StreamableHTTP
    session manager initialises correctly.

    Parameters
    ----------
    extra_routes:
        Additional Starlette routes (e.g. ``Mount("/api", ...)``) to
        include alongside the MCP app.
    """
    # Inject extra routes (e.g. /api) directly into the MCP app
    # so all routes live in a single Starlette instance.
    for route in extra_routes or []:
        mcp._custom_starlette_routes.append(route)

    mcp_asgi = mcp.streamable_http_app()

    # Wrap with Bearer token auth middleware.
    mcp_asgi.add_middleware(BearerTokenMiddleware, api_key=api_key)

    return mcp_asgi
