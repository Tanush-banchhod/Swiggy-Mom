"""Cart operations — always fetch fresh state before any mutation."""

import asyncio
from typing import Any

import structlog

from app.agent.swiggy_client import SwiggyClient, SwiggyMCPError

log = structlog.get_logger()

_MAX_CART_TOTAL_INR = 1000  # Swiggy Builders Club v1 cap


class CartTotalExceeded(Exception):
    pass


async def get_fresh_cart(client: SwiggyClient, address_id: str) -> dict[str, Any]:
    """Always called immediately before any cart mutation or order placement."""
    return await client.get_food_cart(address_id)


async def add_item_to_cart(
    client: SwiggyClient,
    restaurant_id: str,
    item_id: str,
    address_id: str,
) -> dict[str, Any]:
    cart = await get_fresh_cart(client, address_id)
    current_total = float(cart.get("total", 0))
    if current_total > _MAX_CART_TOTAL_INR:
        raise CartTotalExceeded(
            f"Cart total ₹{current_total:.0f} exceeds ₹{_MAX_CART_TOTAL_INR} Builders Club cap. "
            "Please remove items before adding."
        )

    result = await client.update_food_cart(restaurant_id, item_id, quantity=1, address_id=address_id)
    log.info("cart.item_added", restaurant_id=restaurant_id, item_id=item_id)
    return result

# V2: Extension can be added by integrating with external API keys of some services like honewell or anyother service that provides coupon codes.
async def find_best_cod_coupon(client: SwiggyClient) -> str | None:
    """Return best coupon code that doesn't require online payment."""
    try:
        coupons = await client.fetch_food_coupons()
    except SwiggyMCPError:
        return None

    cod_coupons = [c for c in coupons if not c.get("requiresOnlinePayment", True)]
    if not cod_coupons:
        return None

    # Simple heuristic: pick highest discount value
    best = max(cod_coupons, key=lambda c: float(c.get("discountValue", 0)), default=None)
    return str(best["code"]) if best else None
