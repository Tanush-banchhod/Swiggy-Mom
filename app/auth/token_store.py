"""Store and retrieve Swiggy OAuth tokens in Redis with TTL."""

import json
from datetime import timedelta

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger()

_TOKEN_TTL = timedelta(days=4, hours=23)  # Swiggy tokens live 5 days; refresh before expiry
_PKCE_TTL = timedelta(minutes=10)


def _token_key(user_id: str) -> str:
    return f"swiggy:token:{user_id}"


def _pkce_key(state: str) -> str:
    return f"swiggy:pkce:{state}"


async def store_token(redis: aioredis.Redis, user_id: str, token_data: dict[str, object]) -> None:  # type: ignore[type-arg]
    await redis.set(
        _token_key(user_id),
        json.dumps(token_data),
        ex=int(_TOKEN_TTL.total_seconds()),
    )
    log.info("token.stored", user_id=user_id)


async def get_token(redis: aioredis.Redis, user_id: str) -> dict[str, object] | None:  # type: ignore[type-arg]
    raw = await redis.get(_token_key(user_id))
    if raw is None:
        return None
    return json.loads(raw)  # type: ignore[no-any-return]


async def get_access_token(redis: aioredis.Redis, user_id: str) -> str | None:  # type: ignore[type-arg]
    data = await get_token(redis, user_id)
    if data is None:
        return None
    return str(data.get("access_token", ""))


async def store_pkce_state(redis: aioredis.Redis, state: str, verifier: str) -> None:  # type: ignore[type-arg]
    await redis.set(_pkce_key(state), verifier, ex=int(_PKCE_TTL.total_seconds()))


async def pop_pkce_verifier(redis: aioredis.Redis, state: str) -> str | None:  # type: ignore[type-arg]
    verifier = await redis.get(_pkce_key(state))
    if verifier:
        await redis.delete(_pkce_key(state))
    return verifier


async def delete_token(redis: aioredis.Redis, user_id: str) -> None:  # type: ignore[type-arg]
    await redis.delete(_token_key(user_id))
