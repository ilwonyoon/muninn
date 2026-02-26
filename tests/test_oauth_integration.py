"""Integration tests for OAuth login routes (Starlette TestClient)."""

from __future__ import annotations

import time

import pytest
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.testclient import TestClient

from muninn.oauth_login import create_login_routes
from muninn.oauth_provider import MuninnOAuthProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(
    client_id: str = "int-client",
    client_secret: str = "int-secret",
) -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=[AnyUrl("https://example.com/callback")],
    )


def _make_auth_params(
    state: str = "int-state",
    code_challenge: str = "int-challenge",
) -> AuthorizationParams:
    return AuthorizationParams(
        state=state,
        scopes=["muninn"],
        code_challenge=code_challenge,
        redirect_uri=AnyUrl("https://example.com/callback"),
        redirect_uri_provided_explicitly=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def oauth_app(tmp_path):
    """Return (Starlette app, MuninnOAuthProvider) wired with login routes."""
    db_path = str(tmp_path / "oauth_int_test.db")
    provider = MuninnOAuthProvider(db_path=db_path, owner_password="mypin")
    routes = create_login_routes(provider)
    app = Starlette(routes=routes)
    return app, provider


@pytest.fixture
def client(oauth_app):
    """Return a Starlette TestClient for the login routes."""
    app, _ = oauth_app
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# Async helper to create a code through the provider
# ---------------------------------------------------------------------------


async def _create_auth_code(provider: MuninnOAuthProvider) -> str:
    """Register a client, run authorize(), and return the code_id."""
    oauth_client = _make_client()
    await provider.register_client(oauth_client)
    params = _make_auth_params()
    auth_url = await provider.authorize(oauth_client, params)
    return auth_url.split("code_id=")[1]


# ---------------------------------------------------------------------------
# Login Page
# ---------------------------------------------------------------------------


class TestLoginPage:
    def test_get_login_page(self, client):
        """GET /oauth/login?code_id=test returns 200 with HTML containing 'Muninn'."""
        response = client.get("/oauth/login?code_id=test")

        assert response.status_code == 200
        assert "Muninn" in response.text

    def test_login_page_contains_form(self, client):
        """Response HTML contains a <form and 'PIN' references."""
        response = client.get("/oauth/login?code_id=test")

        assert "<form" in response.text
        assert "PIN" in response.text

    def test_wrong_pin_returns_401(self, client):
        """POST /oauth/login with wrong pin returns 401."""
        response = client.post(
            "/oauth/login",
            data={"code_id": "some-code", "pin": "wrong-pin"},
        )

        assert response.status_code == 401
        assert "Invalid PIN" in response.text

    @pytest.mark.anyio
    async def test_correct_pin_redirects(self, oauth_app):
        """POST with correct PIN and valid code returns 302 redirect."""
        app, provider = oauth_app
        code_id = await _create_auth_code(provider)

        test_client = TestClient(app, follow_redirects=False)
        response = test_client.post(
            "/oauth/login",
            data={"code_id": code_id, "pin": "mypin"},
        )

        assert response.status_code == 302
        location = response.headers["location"]
        assert "example.com/callback" in location
        assert f"code={code_id}" in location
        assert "state=int-state" in location

    @pytest.mark.anyio
    async def test_expired_code_returns_400(self, oauth_app, monkeypatch):
        """POST with correct PIN but expired code returns 400."""
        app, provider = oauth_app
        code_id = await _create_auth_code(provider)

        # Advance time past the auth code TTL (600s)
        future = time.time() + 700
        monkeypatch.setattr(time, "time", lambda: future)

        test_client = TestClient(app, follow_redirects=False)
        response = test_client.post(
            "/oauth/login",
            data={"code_id": code_id, "pin": "mypin"},
        )

        assert response.status_code == 400
        assert "expired" in response.text.lower() or "invalid" in response.text.lower()
