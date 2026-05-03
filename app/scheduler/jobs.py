"""APScheduler setup — starts background meal trigger jobs."""

import asyncio

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = structlog.get_logger()

_scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine from a sync APScheduler job."""
    asyncio.run(coro)


def schedule_meal_trigger(user_id: str, hour: int, minute: int, meal_type: str) -> None:
    """
    Schedule a suggestion fire for `user_id` at (hour, minute) IST minus 45 min.
    Call this whenever a user updates their meal windows.
    """
    trigger_minute = minute - 45
    trigger_hour = hour
    if trigger_minute < 0:
        trigger_minute += 60
        trigger_hour -= 1
    if trigger_hour < 0:
        trigger_hour += 24

    job_id = f"meal_{user_id}_{meal_type}"

    from app.scheduler.meal_trigger import fire_meal_suggestions

    _scheduler.add_job(
        _run_async,
        CronTrigger(hour=trigger_hour, minute=trigger_minute),
        id=job_id,
        args=[fire_meal_suggestions(user_id, meal_type)],
        replace_existing=True,
    )
    log.info(
        "scheduler.job_scheduled",
        job_id=job_id,
        trigger_time=f"{trigger_hour:02d}:{trigger_minute:02d}",
    )


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        log.info("scheduler.started")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("scheduler.stopped")
