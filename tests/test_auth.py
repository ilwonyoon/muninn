"""Unit tests for BearerTokenMiddleware and create_authenticated_app."""

from __future__ import annotations

import hmac

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from muninn.auth import BearerTokenMiddleware

TEST_API_KEY = "test-secret-key-abc123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _homepage(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


def _make_client(api_key: str = TEST_API_KEY) -> TestClient:
    """Return a TestClient wrapping a minimal Starlette app with BearerTokenMiddleware."""
    app = Starlette(
        routes=[Route("/", _homepage)],
        middleware=[Middleware(BearerTokenMiddleware, api_key=api_key)],
    )
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — valid token
# ---------------------------------------------------------------------------


class TestValidToken:
    def test_valid_token_passes(self):
        """A request with the correct Bearer token is forwarded (200)."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
        assert response.status_code == 200

    def test_valid_token_response_body_intact(self):
        """The upstream response body is returned unmodified when auth passes."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": f"Bearer {TEST_API_KEY}"})
        assert response.text == "OK"


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — missing Authorization header
# ---------------------------------------------------------------------------


class TestMissingAuthHeader:
    def test_missing_authorization_header_returns_401(self):
        """A request with no Authorization header is rejected with 401."""
        client = _make_client()
        response = client.get("/")
        assert response.status_code == 401

    def test_missing_header_returns_json_error(self):
        """The 401 response from a missing header is JSON with an 'error' key."""
        client = _make_client()
        response = client.get("/")
        body = response.json()
        assert "error" in body

    def test_missing_header_error_message(self):
        """The 401 error message mentions missing or invalid header."""
        client = _make_client()
        response = client.get("/")
        assert "Missing" in response.json()["error"]


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — invalid / wrong token
# ---------------------------------------------------------------------------


class TestInvalidToken:
    def test_wrong_token_returns_401(self):
        """A request with the wrong token value is rejected with 401."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 401

    def test_wrong_token_returns_json_error(self):
        """The 401 response from a wrong token is JSON with an 'error' key."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": "Bearer wrong-token"})
        body = response.json()
        assert "error" in body

    def test_wrong_token_error_message(self):
        """The 401 error message for a wrong token mentions 'Invalid'."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": "Bearer wrong-token"})
        assert "Invalid" in response.json()["error"]

    def test_empty_token_after_bearer_returns_401(self):
        """'Bearer ' with nothing after it (empty string after strip) is rejected."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    def test_whitespace_only_token_after_bearer_returns_401(self):
        """'Bearer    ' (only whitespace after prefix) is rejected after strip."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": "Bearer    "})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — wrong prefix / scheme
# ---------------------------------------------------------------------------


class TestWrongPrefix:
    def test_lowercase_bearer_prefix_returns_401(self):
        """'bearer' (lowercase) is not accepted — prefix check is case-sensitive."""
        client = _make_client()
        response = client.get(
            "/", headers={"Authorization": f"bearer {TEST_API_KEY}"}
        )
        assert response.status_code == 401

    def test_basic_scheme_returns_401(self):
        """An Authorization header using 'Basic' scheme is rejected with 401."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert response.status_code == 401

    def test_raw_token_without_scheme_returns_401(self):
        """A raw token with no scheme prefix is rejected with 401."""
        client = _make_client()
        response = client.get("/", headers={"Authorization": TEST_API_KEY})
        assert response.status_code == 401

    def test_bearer_without_space_returns_401(self):
        """'Bearer' immediately followed by the token (no space separator) is rejected."""
        client = _make_client()
        response = client.get(
            "/", headers={"Authorization": f"Bearer{TEST_API_KEY}"}
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — whitespace stripping
# ---------------------------------------------------------------------------


class TestWhitespaceStripping:
    def test_token_with_trailing_whitespace_is_accepted(self):
        """Token with trailing spaces is still accepted after strip()."""
        client = _make_client()
        response = client.get(
            "/", headers={"Authorization": f"Bearer {TEST_API_KEY}   "}
        )
        assert response.status_code == 200

    def test_token_with_extra_leading_space_is_accepted(self):
        """Extra space between 'Bearer' and the token is handled by strip()."""
        client = _make_client()
        # "Bearer  token" — two spaces; removeprefix strips "Bearer ", strip() removes extra.
        response = client.get(
            "/", headers={"Authorization": f"Bearer  {TEST_API_KEY}"}
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — constant-time comparison
# ---------------------------------------------------------------------------


class TestConstantTimeComparison:
    def test_hmac_compare_digest_correct_match(self):
        """hmac.compare_digest returns True for identical strings (sanity check)."""
        assert hmac.compare_digest(TEST_API_KEY, TEST_API_KEY) is True

    def test_hmac_compare_digest_no_match(self):
        """hmac.compare_digest returns False for different strings (sanity check)."""
        assert hmac.compare_digest("wrong", TEST_API_KEY) is False

    def test_token_prefix_of_real_key_is_rejected(self):
        """A token that is only a prefix of the real key is rejected."""
        client = _make_client()
        prefix = TEST_API_KEY[: len(TEST_API_KEY) // 2]
        response = client.get("/", headers={"Authorization": f"Bearer {prefix}"})
        assert response.status_code == 401

    def test_token_suffix_of_real_key_is_rejected(self):
        """A token that is only a suffix of the real key is rejected."""
        client = _make_client()
        suffix = TEST_API_KEY[len(TEST_API_KEY) // 2 :]
        response = client.get("/", headers={"Authorization": f"Bearer {suffix}"})
        assert response.status_code == 401

    def test_token_with_extra_character_is_rejected(self):
        """A token that is the real key plus one extra character is rejected."""
        client = _make_client()
        extended = TEST_API_KEY + "x"
        response = client.get("/", headers={"Authorization": f"Bearer {extended}"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# BearerTokenMiddleware — different api_key configurations
# ---------------------------------------------------------------------------


class TestDifferentApiKeys:
    def test_correct_key_accepted_for_custom_key(self):
        """Middleware configured with a custom key accepts that exact key."""
        client = _make_client(api_key="another-secret-xyz")
        response = client.get(
            "/", headers={"Authorization": "Bearer another-secret-xyz"}
        )
        assert response.status_code == 200

    def test_default_test_key_rejected_when_different_key_configured(self):
        """The default test key is rejected when middleware uses a different key."""
        client = _make_client(api_key="another-secret-xyz")
        response = client.get(
            "/", headers={"Authorization": f"Bearer {TEST_API_KEY}"}
        )
        assert response.status_code == 401

    def test_each_client_uses_its_own_key(self):
        """Two middleware instances with different keys each accept only their own key."""
        client_a = _make_client(api_key="key-alpha")
        client_b = _make_client(api_key="key-beta")

        assert client_a.get("/", headers={"Authorization": "Bearer key-alpha"}).status_code == 200
        assert client_a.get("/", headers={"Authorization": "Bearer key-beta"}).status_code == 401
        assert client_b.get("/", headers={"Authorization": "Bearer key-beta"}).status_code == 200
        assert client_b.get("/", headers={"Authorization": "Bearer key-alpha"}).status_code == 401
