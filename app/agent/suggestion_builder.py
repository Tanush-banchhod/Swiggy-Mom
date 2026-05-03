"""Build the final top-3 suggestion payload."""

from typing import Any


_LABELS = ["Best macro fit", "Your usual pick", "Budget pick"]


def build_top_3(ranked_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Takes ranked item list and returns exactly 3 suggestions.
    If fewer than 3 items pass filters, returns what's available (minimum 1).
    """
    top = ranked_items[:3]
    suggestions = []
    for i, item in enumerate(top):
        suggestions.append(
            {
                "slot": i + 1,
                "label": _LABELS[i] if i < len(_LABELS) else f"Option {i + 1}",
                "item_id": item.get("id", item.get("itemId", "")),
                "item_name": item.get("name", ""),
                "restaurant_id": item.get("restaurantId", ""),
                "restaurant_name": item.get("restaurantName", ""),
                "price_inr": item.get("price", item.get("defaultPrice", 0)),
                "protein_g": item.get("protein_g", 0),
                "score": round(item.get("_score", 0), 4),
                "image_url": item.get("imageUrl", ""),
            }
        )
    return suggestions


def build_notification_payload(
    suggestions: list[dict[str, Any]],
    protein_remaining_g: int,
    meal_type: str = "Lunch",
) -> dict[str, Any]:
    names = " · ".join(s["item_name"] for s in suggestions)
    return {
        "title": f"{meal_type} in 45 min — 3 options ready",
        "body": f"{names}. {protein_remaining_g}g protein left today.",
        "data": {"suggestions": suggestions},
    }
