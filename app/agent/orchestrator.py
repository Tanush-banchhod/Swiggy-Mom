"""Main agent loop — runs at meal trigger time or on manual /suggestions/now call."""

import datetime
from typing import Any

import structlog

from app.agent import filter_engine, scorer, suggestion_builder

log = structlog.get_logger()


async def build_suggestions(
    swiggy_token: str,
    user_id: str,
    address_id: str,
    allergy_blocks: list[str],
    taste_dislikes: list[str],
    notify_lead_minutes: int = 45,
    recent_restaurant_ids: list[str] | None = None,
    recent_item_ids: list[str] | None = None,
    protein_remaining_g: int = 100,
    meal_type: str = "Lunch",
) -> dict[str, Any]:
    """
    Full suggestion pipeline:
    1. search_restaurants → filter
    2. get_restaurant_menu for top candidates → filter items
    3. score → rank → top 3
    4. build notification payload
    """
    from app.agent.swiggy_client import SwiggyClient

    client = SwiggyClient(swiggy_token)

    log.info("agent.suggestions.start", user_id=user_id, address_id=address_id)

    restaurants = await client.search_restaurants(address_id)
    qualified = filter_engine.filter_restaurants(restaurants, notify_lead_minutes)

    if not qualified:
        log.warning("agent.no_qualifying_restaurants", user_id=user_id)
        return {
            "status": "no_options",
            "message": "Nothing qualifies right now — check back closer to meal time.",
            "suggestions": [],
        }

    all_items: list[dict[str, Any]] = []
    for restaurant in qualified[:5]:  # fetch menus for top 5 candidates
        restaurant_id = restaurant.get("id", restaurant.get("restaurantId", ""))
        try:
            menu = await client.get_restaurant_menu(restaurant_id)
            categories = menu.get("categories", [])
            for category in categories:
                for item in category.get("items", []):
                    item["restaurantId"] = restaurant_id
                    item["restaurantName"] = restaurant.get("name", "")
                    all_items.append(item)
        except Exception as exc:
            log.warning("agent.menu_fetch_failed", restaurant_id=restaurant_id, error=str(exc))
            continue

    filtered = filter_engine.filter_items(all_items, allergy_blocks, taste_dislikes)
    ranked = scorer.rank_items(
        filtered,
        recent_restaurant_ids or [],
        recent_item_ids or [],
    )

    suggestions = suggestion_builder.build_top_3(ranked)

    if not suggestions:
        return {
            "status": "no_options",
            "message": "All options blocked by your allergy or preference settings.",
            "suggestions": [],
        }

    notification = suggestion_builder.build_notification_payload(
        suggestions, protein_remaining_g, meal_type
    )

    log.info("agent.suggestions.done", user_id=user_id, count=len(suggestions))
    return {
        "status": "ok",
        "suggestions": suggestions,
        "notification": notification,
        "scoring_breakdown": [
            {
                "item_name": s["item_name"],
                "score": s["score"],
                "label": s["label"],
            }
            for s in suggestions
        ],
    }


async def build_suggestions_for_demo() -> dict[str, Any]:
    """
    Demo-friendly version of the suggestion pipeline.
    Returns mock-structured data to show the full flow without a real Swiggy token.
    """
    mock_items = [
        {
            "id": "item_001",
            "name": "Grilled Chicken Bowl",
            "restaurantId": "rest_001",
            "restaurantName": "FitBowl Kitchen",
            "price": 280,
            "defaultPrice": 280,
            "protein_g": 42,
            "imageUrl": "",
            "ingredients": ["chicken", "brown rice", "broccoli"],
        },
        {
            "id": "item_002",
            "name": "Paneer Tikka Wrap",
            "restaurantId": "rest_002",
            "restaurantName": "Wrap Republic",
            "price": 199,
            "defaultPrice": 199,
            "protein_g": 28,
            "imageUrl": "",
            "ingredients": ["paneer", "whole wheat", "mint"],
        },
        {
            "id": "item_003",
            "name": "Dal Tadka + Brown Rice",
            "restaurantId": "rest_003",
            "restaurantName": "Homestyle Kitchen",
            "price": 149,
            "defaultPrice": 149,
            "protein_g": 18,
            "imageUrl": "",
            "ingredients": ["lentils", "rice", "ghee"],
        },
        {
            "id": "item_004",
            "name": "Egg White Omelette",
            "restaurantId": "rest_001",
            "restaurantName": "FitBowl Kitchen",
            "price": 179,
            "defaultPrice": 179,
            "protein_g": 22,
            "imageUrl": "",
            "ingredients": ["egg white", "spinach", "cheese"],
        },
    ]

    filtered = filter_engine.filter_items(mock_items, allergy_blocks=[], taste_dislikes=[])
    ranked = scorer.rank_items(filtered, recent_restaurant_ids=[], recent_item_ids=[])
    suggestions = suggestion_builder.build_top_3(ranked)
    notification = suggestion_builder.build_notification_payload(suggestions, protein_remaining_g=108)

    return {
        "status": "ok",
        "demo_mode": True,
        "note": "Real mode requires Swiggy OAuth token and configured profile.",
        "pipeline": {
            "step_1": "search_restaurants(addressId) → filter by OPEN + rating ≥ 4.0 + delivery ≤ 40 min",
            "step_2": "get_restaurant_menu(restaurantId) × top 5 restaurants",
            "step_3": "filter_items: hard-block allergies, soft-penalize dislikes",
            "step_4": "score: protein_g / price × preference signals × variety × recency",
            "step_5": "top 3 → notification payload",
        },
        "suggestions": suggestions,
        "notification": notification,
        "scoring_breakdown": [
            {
                "item_name": s["item_name"],
                "score": s["score"],
                "label": s["label"],
                "protein_g": s["protein_g"],
                "price_inr": s["price_inr"],
                "protein_per_rupee": round(s["protein_g"] / max(s["price_inr"], 1), 4),
            }
            for s in suggestions
        ],
    }
