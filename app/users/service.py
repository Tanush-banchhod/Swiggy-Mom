import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User

log = structlog.get_logger()


async def get_or_create_user(db: AsyncSession, swiggy_user_id: str) -> User:
    result = await db.execute(select(User).where(User.swiggy_user_id == swiggy_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(swiggy_user_id=swiggy_user_id)
        db.add(user)
        await db.flush()
        log.info("user.created", swiggy_user_id=swiggy_user_id, user_id=str(user.id))
    return user


async def get_user_by_swiggy_id(db: AsyncSession, swiggy_user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.swiggy_user_id == swiggy_user_id))
    return result.scalar_one_or_none()


async def soft_delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.deleted_at = datetime.now(timezone.utc)
        log.info("user.soft_deleted", user_id=str(user_id))
