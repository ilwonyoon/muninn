"""Unit tests for MuninnOAuthProvider (no HTTP, direct method calls)."""

from __future__ import annotations

import sqlite3
import time

import pytest
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyUrl

from muninn.oauth_provider import MuninnOAuthProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(
    client_id: str = "test-client",
    client_secret: str = "test-secret",
) -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=[AnyUrl("https://example.com/callback")],
    )


def _make_auth_params(
    state: str = "test-state",
    code_challenge: str = "test-challenge",
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
def provider(tmp_path):
    """Return a MuninnOAuthProvider backed by an isolated temp database."""
    db_path = str(tmp_path / "oauth_test.db")
    return MuninnOAuthProvider(db_path=db_path, owner_password="test-pin-123")


# ---------------------------------------------------------------------------
# Full-flow helper (reused across test classes)
# ---------------------------------------------------------------------------


async def _do_authorize(provider: MuninnOAuthProvider):
    """Register a client, authorize, and return (client, code_id, auth_url)."""
    client = _make_client()
    await provider.register_client(client)
    params = _make_auth_params()
    auth_url = await provider.authorize(client, params)
    # Extract the code_id from the URL: /oauth/login?code_id=<code>
    code_id = auth_url.split("code_id=")[1]
    return client, code_id, auth_url


async def _do_exchange(provider: MuninnOAuthProvider):
    """Full flow through token exchange. Returns (client, oauth_token)."""
    client, code_id, _ = await _do_authorize(provider)
    provider.approve_code(code_id)
    auth_code = await provider.load_authorization_code(client, code_id)
    assert auth_code is not None
    token = await provider.exchange_authorization_code(client, auth_code)
    return client, token


# ---------------------------------------------------------------------------
# Client Registration
# ---------------------------------------------------------------------------


class TestClientRegistration:
    @pytest.mark.anyio
    async def test_register_and_get_client(self, provider):
        """Register a client, then get_client returns it with same client_id."""
        client = _make_client()
        await provider.register_client(client)

        loaded = await provider.get_client("test-client")
        assert loaded is not None
        assert loaded.client_id == "test-client"
        assert loaded.client_secret == "test-secret"

    @pytest.mark.anyio
    async def test_get_nonexistent_client(self, provider):
        """get_client returns None for an unregistered client_id."""
        result = await provider.get_client("does-not-exist")
        assert result is None

    @pytest.mark.anyio
    async def test_register_duplicate_client(self, provider):
        """Registering the same client_id twice raises IntegrityError."""
        client = _make_client()
        await provider.register_client(client)

        with pytest.raises(sqlite3.IntegrityError):
            await provider.register_client(client)


# ---------------------------------------------------------------------------
# Authorize
# ---------------------------------------------------------------------------


class TestAuthorize:
    @pytest.mark.anyio
    async def test_authorize_returns_login_url(self, provider):
        """authorize() returns a URL containing /oauth/login?code_id=."""
        client = _make_client()
        await provider.register_client(client)
        params = _make_auth_params()

        url = await provider.authorize(client, params)

        assert "/oauth/login?code_id=" in url
        code_id = url.split("code_id=")[1]
        assert len(code_id) > 0

    @pytest.mark.anyio
    async def test_authorize_stores_unapproved_code(self, provider):
        """After authorize(), load_authorization_code returns None (not approved)."""
        client, code_id, _ = await _do_authorize(provider)

        result = await provider.load_authorization_code(client, code_id)
        assert result is None


# ---------------------------------------------------------------------------
# Authorization Code Flow
# ---------------------------------------------------------------------------


class TestAuthorizationCodeFlow:
    @pytest.mark.anyio
    async def test_approve_and_load_code(self, provider):
        """authorize → approve_code → load_authorization_code returns AuthorizationCode."""
        client, code_id, _ = await _do_authorize(provider)

        provider.approve_code(code_id)
        auth_code = await provider.load_authorization_code(client, code_id)

        assert auth_code is not None
        assert isinstance(auth_code, AuthorizationCode)
        assert auth_code.code == code_id
        assert auth_code.client_id == "test-client"
        assert auth_code.code_challenge == "test-challenge"

    @pytest.mark.anyio
    async def test_exchange_code_for_tokens(self, provider):
        """Full flow: authorize → approve → load → exchange → OAuthToken."""
        client, token = await _do_exchange(provider)

        assert isinstance(token, OAuthToken)
        assert token.access_token is not None
        assert len(token.access_token) > 0
        assert token.refresh_token is not None
        assert len(token.refresh_token) > 0
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

    @pytest.mark.anyio
    async def test_code_consumed_after_exchange(self, provider):
        """After exchange, load_authorization_code returns None (code deleted)."""
        client, code_id, _ = await _do_authorize(provider)
        provider.approve_code(code_id)
        auth_code = await provider.load_authorization_code(client, code_id)
        assert auth_code is not None

        await provider.exchange_authorization_code(client, auth_code)

        result = await provider.load_authorization_code(client, code_id)
        assert result is None

    @pytest.mark.anyio
    async def test_expired_code_returns_none(self, provider, monkeypatch):
        """An expired authorization code returns None from load_authorization_code."""
        client, code_id, _ = await _do_authorize(provider)
        provider.approve_code(code_id)

        # Advance time past the code TTL (600s)
        future = time.time() + 700
        monkeypatch.setattr(time, "time", lambda: future)

        result = await provider.load_authorization_code(client, code_id)
        assert result is None


# ---------------------------------------------------------------------------
# Access Token
# ---------------------------------------------------------------------------


class TestAccessToken:
    @pytest.mark.anyio
    async def test_load_valid_access_token(self, provider):
        """After exchange, load_access_token returns a valid AccessToken."""
        client, token = await _do_exchange(provider)

        access = await provider.load_access_token(token.access_token)

        assert access is not None
        assert isinstance(access, AccessToken)
        assert access.token == token.access_token
        assert access.client_id == "test-client"

    @pytest.mark.anyio
    async def test_load_invalid_token(self, provider):
        """A random string returns None from load_access_token."""
        result = await provider.load_access_token("totally-bogus-token-value")
        assert result is None

    @pytest.mark.anyio
    async def test_expired_access_token_returns_none(self, provider, monkeypatch):
        """An expired access token returns None from load_access_token."""
        client, token = await _do_exchange(provider)

        # Advance time past the access token TTL (3600s)
        future = time.time() + 4000
        monkeypatch.setattr(time, "time", lambda: future)

        result = await provider.load_access_token(token.access_token)
        assert result is None


# ---------------------------------------------------------------------------
# Refresh Token
# ---------------------------------------------------------------------------


class TestRefreshToken:
    @pytest.mark.anyio
    async def test_refresh_token_flow(self, provider):
        """Exchange auth code, then refresh for new tokens."""
        client, token = await _do_exchange(provider)

        # Load the refresh token
        rt = await provider.load_refresh_token(client, token.refresh_token)
        assert rt is not None
        assert isinstance(rt, RefreshToken)

        # Exchange it for new tokens
        new_token = await provider.exchange_refresh_token(
            client, rt, scopes=["muninn"]
        )

        assert isinstance(new_token, OAuthToken)
        assert new_token.access_token != token.access_token
        assert new_token.refresh_token != token.refresh_token

    @pytest.mark.anyio
    async def test_old_tokens_deleted_after_refresh(self, provider):
        """After refresh, old access token no longer loads."""
        client, token = await _do_exchange(provider)
        old_access = token.access_token
        old_refresh = token.refresh_token

        rt = await provider.load_refresh_token(client, old_refresh)
        assert rt is not None
        await provider.exchange_refresh_token(client, rt, scopes=["muninn"])

        # Old access token should be gone
        assert await provider.load_access_token(old_access) is None
        # Old refresh token should be gone
        assert await provider.load_refresh_token(client, old_refresh) is None

    @pytest.mark.anyio
    async def test_invalid_refresh_token(self, provider):
        """A random string returns None from load_refresh_token."""
        client = _make_client()
        await provider.register_client(client)

        result = await provider.load_refresh_token(client, "bogus-refresh-token")
        assert result is None


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------


class TestRevocation:
    @pytest.mark.anyio
    async def test_revoke_access_token(self, provider):
        """After revoking an access token, load_access_token returns None."""
        client, token = await _do_exchange(provider)

        access = await provider.load_access_token(token.access_token)
        assert access is not None

        await provider.revoke_token(access)

        assert await provider.load_access_token(token.access_token) is None

    @pytest.mark.anyio
    async def test_revoke_deletes_all_client_tokens(self, provider):
        """Revoking one token deletes all tokens for that client."""
        client, token = await _do_exchange(provider)

        access = await provider.load_access_token(token.access_token)
        assert access is not None

        await provider.revoke_token(access)

        # Both access and refresh tokens should be gone
        assert await provider.load_access_token(token.access_token) is None
        assert await provider.load_refresh_token(client, token.refresh_token) is None


# ---------------------------------------------------------------------------
# PIN Validation
# ---------------------------------------------------------------------------


class TestPinValidation:
    def test_correct_pin(self, provider):
        """verify_pin returns True for the correct owner password."""
        assert provider.verify_pin("test-pin-123") is True

    def test_wrong_pin(self, provider):
        """verify_pin returns False for an incorrect PIN."""
        assert provider.verify_pin("wrong") is False

    def test_empty_pin(self, provider):
        """verify_pin returns False for an empty string."""
        assert provider.verify_pin("") is False


# ---------------------------------------------------------------------------
# approve_code
# ---------------------------------------------------------------------------


class TestApproveCode:
    @pytest.mark.anyio
    async def test_approve_valid_code(self, provider):
        """approve_code returns dict with code, redirect_uri, and state."""
        _, code_id, _ = await _do_authorize(provider)

        result = provider.approve_code(code_id)

        assert result is not None
        assert result["code"] == code_id
        assert "example.com/callback" in result["redirect_uri"]
        assert result["state"] == "test-state"

    @pytest.mark.anyio
    async def test_approve_nonexistent_code(self, provider):
        """approve_code returns None for a code that does not exist."""
        result = provider.approve_code("nonexistent-code-value")
        assert result is None

    @pytest.mark.anyio
    async def test_approve_already_approved_code(self, provider):
        """approve_code returns None if the code was already approved."""
        _, code_id, _ = await _do_authorize(provider)

        first = provider.approve_code(code_id)
        assert first is not None

        second = provider.approve_code(code_id)
        assert second is None
