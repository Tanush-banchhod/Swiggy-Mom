"""OAuth 2.1 PKCE flow for Swiggy MCP."""

import base64
import hashlib
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from jose import jwt

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    verifier = secrets.token_urlsafe(96)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorization_url(code_challenge: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.swiggy_client_id,
        "redirect_uri": settings.swiggy_redirect_uri,
        "scope": "mcp:tools mcp:resources mcp:prompts",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{settings.swiggy_auth_url}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(code: str, code_verifier: str) -> dict[str, object]:
    """POST to Swiggy token endpoint and return the token response."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            settings.swiggy_token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.swiggy_client_id,
                "client_secret": settings.swiggy_client_secret,
                "code": code,
                "redirect_uri": settings.swiggy_redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


def create_internal_jwt(user_id: str) -> str:
    """Issue our own JWT so API clients don't hold raw Swiggy tokens."""
    payload = {
        "sub": user_id,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=5),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")
