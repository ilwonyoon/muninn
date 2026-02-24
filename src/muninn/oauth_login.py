"""PIN-based login page for Muninn OAuth authorization flow."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from muninn.oauth_provider import MuninnOAuthProvider


def create_login_routes(provider: MuninnOAuthProvider) -> list[Route]:
    """Return Starlette routes for the OAuth PIN login page."""

    async def login_page(request: Request) -> HTMLResponse | RedirectResponse:
        if request.method == "GET":
            code_id = request.query_params.get("code_id", "")
            return HTMLResponse(_render_login_html(code_id))

        # POST — validate PIN
        form = await request.form()
        code_id = str(form.get("code_id", ""))
        pin = str(form.get("pin", ""))

        if not provider.verify_pin(pin):
            return HTMLResponse(
                _render_login_html(code_id, error="Invalid PIN"),
                status_code=401,
            )

        result = provider.approve_code(code_id)
        if result is None:
            return HTMLResponse(
                _render_login_html(code_id, error="Authorization code expired or invalid"),
                status_code=400,
            )

        redirect_uri = result["redirect_uri"]
        code = result["code"]
        state = result.get("state")

        params = f"code={code}"
        if state:
            params += f"&state={state}"

        separator = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(
            url=f"{redirect_uri}{separator}{params}",
            status_code=302,
        )

    return [Route("/oauth/login", endpoint=login_page, methods=["GET", "POST"])]


def _render_login_html(code_id: str, error: str | None = None) -> str:
    """Return a self-contained HTML login page string."""
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    safe_code_id = html.escape(code_id)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Muninn \u2014 Authorize</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0;
            background: #f5f5f5;
        }}
        .card {{
            background: white; border-radius: 12px; padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 360px; width: 100%; text-align: center;
        }}
        h1 {{ font-size: 24px; margin: 0 0 8px; }}
        .subtitle {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
        input[type="password"] {{
            width: 100%; padding: 12px; font-size: 18px;
            border: 2px solid #ddd; border-radius: 8px;
            text-align: center; letter-spacing: 4px;
            box-sizing: border-box; margin-bottom: 16px;
        }}
        input:focus {{ border-color: #333; outline: none; }}
        button {{
            width: 100%; padding: 12px; font-size: 16px;
            background: #333; color: white; border: none;
            border-radius: 8px; cursor: pointer;
        }}
        button:hover {{ background: #555; }}
        .error {{ color: #e53e3e; font-size: 14px; margin-bottom: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Muninn</h1>
        <p class="subtitle">Enter your PIN to authorize access</p>
        {error_html}
        <form method="POST" action="/oauth/login">
            <input type="hidden" name="code_id" value="{safe_code_id}">
            <input type="password" name="pin" placeholder="PIN" autofocus required>
            <button type="submit">Authorize</button>
        </form>
    </div>
</body>
</html>"""
