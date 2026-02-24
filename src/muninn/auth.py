"""Bearer token authentication middleware for Muninn HTTP transport."""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount

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


def create_authenticated_app(mcp: FastMCP, api_key: str) -> object:
    """Wrap the MCP streamable HTTP app with Bearer token authentication.

    Returns a Starlette application with the auth middleware applied.
    """
    from starlette.applications import Starlette

    mcp_asgi = mcp.streamable_http_app()

    app = Starlette(
        routes=[Mount("/", app=mcp_asgi)],
        middleware=[Middleware(BearerTokenMiddleware, api_key=api_key)],
    )

    return app
