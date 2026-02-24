"""Tests for Bearer token authentication middleware."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from muninn.auth import BearerTokenMiddleware

SECRET = "test-secret-key-12345"


def _hello(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _make_app(api_key: str = SECRET) -> Starlette:
    """Create a minimal Starlette app with auth middleware for testing."""
    return Starlette(
        routes=[Route("/", _hello)],
        middleware=[Middleware(BearerTokenMiddleware, api_key=api_key)],
    )


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_make_app())


class TestBearerTokenMiddleware:
    def test_valid_token_passes(self, client: TestClient):
        resp = client.get("/", headers={"Authorization": f"Bearer {SECRET}"})
        assert resp.status_code == 200
        assert resp.text == "ok"

    def test_missing_auth_header_returns_401(self, client: TestClient):
        resp = client.get("/")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["error"]

    def test_wrong_token_returns_401(self, client: TestClient):
        resp = client.get("/", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["error"]

    def test_non_bearer_scheme_returns_401(self, client: TestClient):
        resp = client.get("/", headers={"Authorization": f"Basic {SECRET}"})
        assert resp.status_code == 401

    def test_empty_bearer_returns_401(self, client: TestClient):
        resp = client.get("/", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_bearer_with_extra_whitespace(self, client: TestClient):
        resp = client.get(
            "/", headers={"Authorization": f"Bearer   {SECRET}  "}
        )
        assert resp.status_code == 200
