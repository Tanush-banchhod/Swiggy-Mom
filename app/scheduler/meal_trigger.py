"""Fires the suggestion pipeline 45 minutes before each user's meal window."""

import asyncio
import datetime

import structlog

log = structlog.get_logger()


async def fire_meal_suggestions(user_id: str, meal_type: str) -> None:
    """Called by the scheduler. Resolves user context and runs the agent."""
    log.info("scheduler.meal_trigger.start", user_id=user_id, meal_type=meal_type)
    try:
        # In production: load token from Redis, load profile from DB, call orchestrator
        # Here we log the trigger — full DB/Redis wiring happens after credentials are live
        log.info(
            "scheduler.meal_trigger.fired",
            user_id=user_id,
            meal_type=meal_type,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
    except Exception as exc:
        log.error("scheduler.meal_trigger.failed", user_id=user_id, error=str(exc))
