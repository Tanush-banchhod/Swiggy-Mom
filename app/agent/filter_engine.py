"""Filter restaurants and menu items before scoring."""

from typing import Any

import structlog

log = structlog.get_logger()

_MIN_RATING = 4.0


def filter_restaurants(
    restaurants: list[dict[str, Any]],
    notify_lead_minutes: int = 45,
    min_rating: float = _MIN_RATING,
) -> list[dict[str, Any]]:
    """Keep only open, well-rated restaurants that can deliver within the notify window."""
    max_delivery_minutes = notify_lead_minutes - 5
    passing = []
    for r in restaurants:
        if r.get("availabilityStatus") != "OPEN":
            continue
        rating = float(r.get("rating", 0))
        if rating < min_rating:
            continue
        delivery_time = int(r.get("estimatedDeliveryTime", 9999))
        if delivery_time > max_delivery_minutes:
            continue
        passing.append(r)

    log.debug("filter.restaurants", total=len(restaurants), passing=len(passing))
    return passing


def filter_items(
    items: list[dict[str, Any]],
    allergy_blocks: list[str],
    taste_dislikes: list[str],
) -> list[dict[str, Any]]:
    """
    Apply allergy blocks (hard zero) and taste dislikes (soft penalty flag).
    Returns items with an injected `_dislike_penalty` float (0.3 if disliked, 1.0 otherwise).
    """
    result = []
    blocks_lower = {b.lower() for b in allergy_blocks}
    dislikes_lower = {d.lower() for d in taste_dislikes}

    for item in items:
        ingredients_raw = item.get("ingredients", [])
        if isinstance(ingredients_raw, str):
            ingredients = [i.strip().lower() for i in ingredients_raw.split(",")]
        else:
            ingredients = [str(i).lower() for i in ingredients_raw]

        name_lower = item.get("name", "").lower()

        # Hard block: skip entirely
        if any(b in name_lower or any(b in ing for ing in ingredients) for b in blocks_lower):
            log.debug("filter.item_blocked", item=item.get("name"), reason="allergy")
            continue

        # Soft penalty
        has_dislike = any(
            d in name_lower or any(d in ing for ing in ingredients) for d in dislikes_lower
        )
        item = {**item, "_dislike_penalty": 0.3 if has_dislike else 1.0}
        result.append(item)

    return result
