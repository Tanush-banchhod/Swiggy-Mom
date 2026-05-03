"""Poll order status and write meal_log entry on delivery."""

import asyncio
from typing import Any

import structlog

from app.agent.swiggy_client import SwiggyClient

log = structlog.get_logger()

_POLL_INTERVAL_S = 10
_MAX_POLLS = 60  # 10 minutes


async def track_until_delivered(
    client: SwiggyClient,
    order_id: str,
    on_delivered: Any = None,  # callable(order_data) → None
) -> dict[str, Any]:
    """Poll track_food_order every 10s until delivered or max polls reached."""
    for attempt in range(_MAX_POLLS):
        try:
            status_data = await client.track_food_order(order_id)
            status = status_data.get("status", "").upper()
            log.debug("tracker.poll", order_id=order_id, status=status, attempt=attempt)

            if status in {"DELIVERED", "COMPLETED"}:
                log.info("tracker.delivered", order_id=order_id)
                if on_delivered:
                    await on_delivered(status_data)
                return status_data

            if status in {"CANCELLED", "FAILED"}:
                log.warning("tracker.terminal_non_delivery", order_id=order_id, status=status)
                return status_data

        except Exception as exc:
            log.warning("tracker.poll_error", order_id=order_id, error=str(exc))

        await asyncio.sleep(_POLL_INTERVAL_S)

    log.warning("tracker.max_polls_reached", order_id=order_id)
    return {"status": "UNKNOWN", "order_id": order_id}
