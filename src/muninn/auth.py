"""Bearer token authentication middleware for Muninn HTTP transport."""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Validates Bearer token in the Authorization header.

    Rejects requests without a valid token with HTTP 401.
    Uses constant-time comparison to prevent timing attacks.
    """

    def __init__(self, app: object, api_key: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._api_key = api_key

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Dashboard REST API routes are local-only, skip auth.
        if request.url.path.startswith("/api/"):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
            )

        token = auth_header.removeprefix("Bearer ").strip()

        if not hmac.compare_digest(token, self._api_key):
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
