import secrets

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

import redis.asyncio as aioredis

from app.auth import oauth, token_store
from app.dependencies import RedisDep, SettingsDep

router = APIRouter()
log = structlog.get_logger()


@router.get("/login")
async def login(redis: RedisDep, settings: SettingsDep) -> RedirectResponse:
    """Initiate OAuth 2.1 PKCE flow — redirects user to Swiggy login."""
    if not settings.swiggy_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Swiggy client_id not configured. Apply at mcp.swiggy.com/access",
        )

    state = secrets.token_urlsafe(32)
    verifier, challenge = oauth.generate_pkce_pair()

    await token_store.store_pkce_state(redis, state, verifier)
    auth_url = oauth.build_authorization_url(challenge, state)

    log.info("auth.login_initiated", state=state)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    redis: RedisDep,
    code: str = Query(...),
    state: str = Query(...),
) -> dict[str, str]:
    """OAuth redirect handler — exchanges code for token, issues internal JWT."""
    verifier = await token_store.pop_pkce_verifier(redis, state)
    if not verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Restart login.",
        )

    try:
        token_data = await oauth.exchange_code_for_token(code, verifier)
    except Exception as exc:
        log.error("auth.token_exchange_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Token exchange with Swiggy failed.",
        ) from exc

    # Use a stable user identifier — Swiggy returns `sub` in token data or we derive one
    swiggy_sub: str = str(token_data.get("sub", token_data.get("user_id", state[:16])))
    await token_store.store_token(redis, swiggy_sub, token_data)

    internal_jwt = oauth.create_internal_jwt(swiggy_sub)
    log.info("auth.callback_success", user_id=swiggy_sub)

    return {
        "access_token": internal_jwt,
        "token_type": "bearer",
        "user_id": swiggy_sub,
        "note": "Use this token as Bearer in Authorization header for all API calls.",
    }


@router.post("/logout")
async def logout(redis: RedisDep, user_id: str = Query(...)) -> dict[str, str]:
    await token_store.delete_token(redis, user_id)
    return {"status": "logged_out"}
