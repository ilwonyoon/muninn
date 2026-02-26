"""OAuth 2.1 authorization server provider backed by SQLite.

Implements the MCP SDK's ``OAuthAuthorizationServerProvider`` protocol so that
Muninn can authenticate remote MCP clients via the standard OAuth code flow
with PKCE.

Single-user design: the *owner_password* (a PIN) gates authorization approval.
"""

from __future__ import annotations

import hmac
import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ACCESS_TOKEN_TTL = 3600  # 1 hour
_REFRESH_TOKEN_TTL = 2_592_000  # 30 days
_AUTH_CODE_TTL = 600  # 10 minutes

_SCHEMA_SQL = """\
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT,
    client_info_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    code_challenge TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    redirect_uri_provided_explicitly INTEGER NOT NULL DEFAULT 0,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    resource TEXT,
    state TEXT,
    expires_at REAL NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    token_type TEXT NOT NULL CHECK(token_type IN ('access', 'refresh')),
    scopes_json TEXT NOT NULL DEFAULT '[]',
    resource TEXT,
    expires_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class MuninnOAuthProvider(OAuthAuthorizationServerProvider):
    """SQLite-backed OAuth 2.1 authorization server for Muninn.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  May be the same database used by
        :class:`~muninn.store.MuninnStore` or a dedicated file.
    owner_password:
        PIN that the resource owner must enter to approve an authorization
        request.
    login_url:
        Base URL for the login/approval page served by the HTTP transport.
    """

    def __init__(
        self,
        db_path: str,
        owner_password: str,
        login_url: str = "/oauth/login",
    ) -> None:
        self._db_path = db_path
        self._owner_password = owner_password
        self._login_url = login_url

        # Ensure parent directory exists.
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialise schema.
        conn = self._get_connection()
        try:
            with conn:
                conn.executescript(_SCHEMA_SQL)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Open a new connection with ``Row`` factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Client registration
    # ------------------------------------------------------------------

    async def get_client(
        self, client_id: str
    ) -> OAuthClientInformationFull | None:
        """Look up a registered client by *client_id*."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT client_info_json FROM oauth_clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        try:
            return OAuthClientInformationFull.model_validate_json(
                row["client_info_json"]
            )
        except Exception:
            return None

    async def register_client(
        self, client_info: OAuthClientInformationFull
    ) -> None:
        """Persist a new client registration."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO oauth_clients (client_id, client_secret, client_info_json)
                    VALUES (?, ?, ?)
                    """,
                    (
                        client_info.client_id,
                        client_info.client_secret,
                        client_info.model_dump_json(),
                    ),
                )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Begin the authorization flow.

        Generates an authorization code, stores it as *unapproved*, and
        returns a redirect URL pointing to the login page where the owner
        can enter their PIN.
        """
        code = secrets.token_urlsafe(32)
        expires_at = time.time() + _AUTH_CODE_TTL
        scopes_json = json.dumps(params.scopes if params.scopes else [])

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO oauth_codes
                        (code, client_id, code_challenge, redirect_uri,
                         redirect_uri_provided_explicitly, scopes_json,
                         resource, state, expires_at, approved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        code,
                        client.client_id,
                        params.code_challenge,
                        str(params.redirect_uri),
                        1 if params.redirect_uri_provided_explicitly else 0,
                        scopes_json,
                        params.resource,
                        params.state,
                        expires_at,
                    ),
                )
        finally:
            conn.close()

        return f"{self._login_url}?code_id={code}"

    # ------------------------------------------------------------------
    # Authorization code exchange
    # ------------------------------------------------------------------

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        """Load an *approved*, non-expired authorization code."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM oauth_codes
                WHERE code = ? AND client_id = ? AND approved = 1
                """,
                (authorization_code, client.client_id),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        if time.time() > row["expires_at"]:
            return None

        scopes: list[str] = json.loads(row["scopes_json"])

        return AuthorizationCode(
            code=row["code"],
            scopes=scopes,
            expires_at=row["expires_at"],
            client_id=row["client_id"],
            code_challenge=row["code_challenge"],
            redirect_uri=row["redirect_uri"],
            redirect_uri_provided_explicitly=bool(
                row["redirect_uri_provided_explicitly"]
            ),
            resource=row["resource"],
        )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        """Exchange an authorization code for access + refresh tokens."""
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        now = int(time.time())
        access_expires = now + _ACCESS_TOKEN_TTL
        refresh_expires = now + _REFRESH_TOKEN_TTL

        scopes = authorization_code.scopes or []
        scopes_json = json.dumps(scopes)
        resource = authorization_code.resource

        conn = self._get_connection()
        try:
            with conn:
                # Consume the authorization code.
                conn.execute(
                    "DELETE FROM oauth_codes WHERE code = ?",
                    (authorization_code.code,),
                )

                # Persist access token.
                conn.execute(
                    """
                    INSERT INTO oauth_tokens
                        (token, client_id, token_type, scopes_json, resource, expires_at)
                    VALUES (?, ?, 'access', ?, ?, ?)
                    """,
                    (
                        access_token,
                        client.client_id,
                        scopes_json,
                        resource,
                        access_expires,
                    ),
                )

                # Persist refresh token.
                conn.execute(
                    """
                    INSERT INTO oauth_tokens
                        (token, client_id, token_type, scopes_json, resource, expires_at)
                    VALUES (?, ?, 'refresh', ?, ?, ?)
                    """,
                    (
                        refresh_token,
                        client.client_id,
                        scopes_json,
                        resource,
                        refresh_expires,
                    ),
                )
        finally:
            conn.close()

        scope_str = " ".join(scopes) if scopes else None

        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=_ACCESS_TOKEN_TTL,
            scope=scope_str,
            refresh_token=refresh_token,
        )

    # ------------------------------------------------------------------
    # Refresh token exchange
    # ------------------------------------------------------------------

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        """Load a non-expired refresh token for *client*."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM oauth_tokens
                WHERE token = ? AND client_id = ? AND token_type = 'refresh'
                """,
                (refresh_token, client.client_id),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        if row["expires_at"] is not None and time.time() > row["expires_at"]:
            return None

        scopes: list[str] = json.loads(row["scopes_json"])

        return RefreshToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=scopes,
            expires_at=row["expires_at"],
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Rotate a refresh token, issuing new access + refresh tokens."""
        new_access = secrets.token_urlsafe(32)
        new_refresh = secrets.token_urlsafe(32)

        now = int(time.time())
        access_expires = now + _ACCESS_TOKEN_TTL
        refresh_expires = now + _REFRESH_TOKEN_TTL

        effective_scopes = scopes if scopes else refresh_token.scopes
        scopes_json = json.dumps(effective_scopes)

        conn = self._get_connection()
        try:
            with conn:
                # Remove old refresh token.
                conn.execute(
                    "DELETE FROM oauth_tokens WHERE token = ?",
                    (refresh_token.token,),
                )

                # Remove old access tokens for this client.
                conn.execute(
                    """
                    DELETE FROM oauth_tokens
                    WHERE client_id = ? AND token_type = 'access'
                    """,
                    (client.client_id,),
                )

                # Insert new access token.
                conn.execute(
                    """
                    INSERT INTO oauth_tokens
                        (token, client_id, token_type, scopes_json, resource, expires_at)
                    VALUES (?, ?, 'access', ?, ?, ?)
                    """,
                    (
                        new_access,
                        client.client_id,
                        scopes_json,
                        None,
                        access_expires,
                    ),
                )

                # Insert new refresh token.
                conn.execute(
                    """
                    INSERT INTO oauth_tokens
                        (token, client_id, token_type, scopes_json, resource, expires_at)
                    VALUES (?, ?, 'refresh', ?, ?, ?)
                    """,
                    (
                        new_refresh,
                        client.client_id,
                        scopes_json,
                        None,
                        refresh_expires,
                    ),
                )
        finally:
            conn.close()

        scope_str = " ".join(effective_scopes) if effective_scopes else None

        return OAuthToken(
            access_token=new_access,
            token_type="Bearer",
            expires_in=_ACCESS_TOKEN_TTL,
            scope=scope_str,
            refresh_token=new_refresh,
        )

    # ------------------------------------------------------------------
    # Access token validation
    # ------------------------------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and validate a non-expired access token."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM oauth_tokens
                WHERE token = ? AND token_type = 'access'
                """,
                (token,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        if row["expires_at"] is not None and time.time() > row["expires_at"]:
            return None

        scopes: list[str] = json.loads(row["scopes_json"])

        return AccessToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=scopes,
            expires_at=row["expires_at"],
            resource=row["resource"],
        )

    # ------------------------------------------------------------------
    # Token revocation
    # ------------------------------------------------------------------

    async def revoke_token(
        self, token: AccessToken | RefreshToken
    ) -> None:
        """Revoke a token and any paired tokens for the same client."""
        conn = self._get_connection()
        try:
            with conn:
                # Delete the specific token.
                conn.execute(
                    "DELETE FROM oauth_tokens WHERE token = ?",
                    (token.token,),
                )

                # Also delete all tokens for this client to fully
                # invalidate the session (both access and refresh).
                conn.execute(
                    "DELETE FROM oauth_tokens WHERE client_id = ?",
                    (token.client_id,),
                )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # PIN / approval helpers (called by the login page handler)
    # ------------------------------------------------------------------

    def verify_pin(self, pin: str) -> bool:
        """Timing-safe comparison of *pin* against the owner password."""
        return hmac.compare_digest(pin, self._owner_password)

    def approve_code(self, code: str) -> dict[str, Any] | None:
        """Mark an authorization code as approved after PIN validation.

        Returns a dict with ``code``, ``redirect_uri``, and ``state`` so the
        caller can build the redirect response.  Returns ``None`` if the code
        does not exist or has already expired.
        """
        conn = self._get_connection()
        try:
            with conn:
                row = conn.execute(
                    """
                    SELECT code, redirect_uri, state, expires_at
                    FROM oauth_codes
                    WHERE code = ? AND approved = 0
                    """,
                    (code,),
                ).fetchone()

                if row is None:
                    return None

                if time.time() > row["expires_at"]:
                    return None

                conn.execute(
                    "UPDATE oauth_codes SET approved = 1 WHERE code = ?",
                    (code,),
                )
        finally:
            conn.close()

        return {
            "code": row["code"],
            "redirect_uri": row["redirect_uri"],
            "state": row["state"],
        }
