"""Idempotency-safe order placement.

Rules:
- Always call get_food_cart immediately before place_food_order.
- On 5xx: check get_food_orders first. If order exists → treat as success.
- If not found after 5xx → retry place_food_order once with 2–5s delay.
- Never blind-retry place_food_order.
- COD only (paymentMethod="COD").
"""

import asyncio
from typing import Any

import structlog

from app.agent.swiggy_client import SwiggyClient, SwiggyMCPError
from app.orders.cart_manager import CartTotalExceeded, find_best_cod_coupon, get_fresh_cart

log = structlog.get_logger()

_MAX_CART_INR = 1000


class OrderConfirmRequired(Exception):
    """Raised when we need explicit user confirmation before proceeding."""

    def __init__(self, preview: dict[str, Any]) -> None:
        self.preview = preview
        super().__init__("User confirmation required before placing order.")


async def _resolve_address_label(client: SwiggyClient, address_id: str) -> dict[str, str]:
    """Return human-readable address fields for the given address_id."""
    try:
        addresses = await client.get_addresses()
        for addr in addresses:
            if addr.get("id") == address_id or addr.get("addressId") == address_id:
                return {
                    "address_id": address_id,
                    "label": addr.get("tag", addr.get("label", "Delivery address")),
                    "line": addr.get("address", addr.get("flatNo", "")),
                    "area": addr.get("area", addr.get("locality", "")),
                    "city": addr.get("city", ""),
                }
    except Exception as exc:
        log.warning("order.address_resolve_failed", address_id=address_id, error=str(exc))

    # Fallback if get_addresses fails or address not found
    return {"address_id": address_id, "label": "Saved address", "line": "", "area": "", "city": ""}


async def prepare_order_preview(
    client: SwiggyClient,
    address_id: str,
) -> dict[str, Any]:
    """
    Fetch fresh cart, resolve delivery address, apply best COD coupon.
    Returns a preview + confirm_prompt that includes the delivery address.
    Does NOT place the order — user must call /orders/place with address_confirmed=true.
    """
    # Resolve address and cart in parallel
    address_info, cart = await asyncio.gather(
        _resolve_address_label(client, address_id),
        get_fresh_cart(client, address_id),
    )

    total = float(cart.get("total", 0))

    if total > _MAX_CART_INR:
        return {
            "status": "rejected",
            "reason": f"Cart total ₹{total:.0f} exceeds ₹{_MAX_CART_INR} cap. Please reduce items.",
        }

    coupon_applied = False
    coupon_code: str | None = await find_best_cod_coupon(client)
    if coupon_code:
        try:
            await client.apply_food_coupon(coupon_code)
            cart = await get_fresh_cart(client, address_id)
            coupon_applied = True
        except SwiggyMCPError as exc:
            log.warning("order.coupon_apply_failed", coupon=coupon_code, error=str(exc))

    restaurant_name = cart.get("restaurantName", "restaurant")
    items_preview = cart.get("items", [])
    final_total = float(cart.get("total", total))
    delivery_time = cart.get("estimatedDeliveryTime", "~30 min")

    address_display = address_info["label"]
    if address_info.get("line"):
        address_display += f" — {address_info['line']}"
    if address_info.get("area"):
        address_display += f", {address_info['area']}"

    return {
        "status": "awaiting_confirmation",
        "preview": {
            "restaurant": restaurant_name,
            "items": items_preview,
            "total_inr": final_total,
            "payment_method": "COD",
            "delivery_estimate": delivery_time,
            "coupon_applied": coupon_code if coupon_applied else None,
            "delivery_address": address_info,
        },
        "confirm_prompt": (
            f"Order from {restaurant_name}?\n"
            f"Deliver to: {address_display}\n"
            f"Total ₹{final_total:.0f} · COD · {delivery_time}\n"
            f"Reply with address_confirmed=true to place this order."
        ),
    }


async def place_order_after_confirm(
    client: SwiggyClient,
    address_id: str,
    address_confirmed: bool,
) -> dict[str, Any]:
    """
    Called only after the user has reviewed the preview AND confirmed the delivery address.
    address_confirmed must be True — we never place an order to an address the user hasn't seen.
    Implements full idempotency logic.
    """
    if not address_confirmed:
        return {
            "status": "rejected",
            "reason": (
                "Delivery address not confirmed. Call /orders/confirm first, "
                "verify the address shown, then re-submit with address_confirmed=true."
            ),
        }

    # Always fetch fresh cart state immediately before placement
    cart = await get_fresh_cart(client, address_id)
    total = float(cart.get("total", 0))

    if total > _MAX_CART_INR:
        return {
            "status": "rejected",
            "reason": f"Cart total ₹{total:.0f} exceeds cap. Cannot place order.",
        }

    try:
        result = await client.place_food_order(payment_method="COD")
        order_id = result.get("orderId", result.get("order_id", ""))
        log.info("order.placed", order_id=order_id)
        return {"status": "placed", "order_id": order_id, "details": result}

    except SwiggyMCPError as exc:
        if not exc.retriable:
            raise

        log.warning("order.5xx_on_place", error=str(exc))
        await asyncio.sleep(3)

        # Idempotency check: did the order go through anyway?
        existing = await client.get_food_orders()
        if existing:
            latest = existing[0]
            order_id = latest.get("orderId", latest.get("order_id", ""))
            if order_id:
                log.info("order.idempotency_recovered", order_id=order_id)
                return {"status": "placed", "order_id": order_id, "details": latest, "idempotency_recovery": True}

        # Safe to retry once
        log.info("order.retry_after_5xx")
        result = await client.place_food_order(payment_method="COD")
        order_id = result.get("orderId", result.get("order_id", ""))
        return {"status": "placed", "order_id": order_id, "details": result}
