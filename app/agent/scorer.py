"""Score menu items: protein-per-rupee × preference signals."""

import datetime
from typing import Any

import structlog

log = structlog.get_logger()


def score_item(
    item: dict[str, Any],
    recent_restaurant_ids: list[str],
    recent_item_ids: list[str],
    day_of_week: int,  # 0=Mon
) -> float:
    """
    base  = protein_g / price_inr
    × dislike_penalty    (injected by filter_engine)
    × variety_bonus      (0.5x if same restaurant used in last 2 meals)
    × recency_penalty    (0.5x if same dish in last 7 days)
    × day_of_week_factor (Fri slightly relaxed, Mon strict)
    """
    protein = float(item.get("protein_g", item.get("nutritionInfo", {}).get("protein", 5)))
    price = float(item.get("price", item.get("defaultPrice", 100))) or 1.0
    base = protein / price

    dislike_penalty: float = item.get("_dislike_penalty", 1.0)

    restaurant_id = item.get("restaurantId", "")
    variety_bonus = 0.5 if restaurant_id in recent_restaurant_ids else 1.0

    item_id = str(item.get("id", item.get("itemId", "")))
    recency_penalty = 0.5 if item_id in recent_item_ids else 1.0

    # Mon=0 is strictest, Fri=4 is most relaxed
    day_factors = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.05, 6: 1.05}
    day_factor = day_factors.get(day_of_week, 1.0)

    score = base * dislike_penalty * variety_bonus * recency_penalty * day_factor
    return round(score, 6)


def rank_items(
    items: list[dict[str, Any]],
    recent_restaurant_ids: list[str],
    recent_item_ids: list[str],
) -> list[dict[str, Any]]:
    today = datetime.date.today().weekday()
    for item in items:
        item["_score"] = score_item(item, recent_restaurant_ids, recent_item_ids, today)
    return sorted(items, key=lambda x: x["_score"], reverse=True)
