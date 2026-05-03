from fastapi import APIRouter, HTTPException, status

from app.agent.swiggy_client import SwiggyClient, SwiggyMCPError
from app.orders import order_service
from app.orders.schemas import ConfirmOrderIn, PlaceOrderIn

router = APIRouter()


@router.post("/confirm")
async def confirm_order(data: ConfirmOrderIn) -> dict[str, object]:
    """
    Phase 1 — preview only. Fetches cart, resolves delivery address, applies best coupon.

    Returns a confirm_prompt that shows:
      - Restaurant name and items
      - Delivery address (label + street — user must verify this is correct)
      - Total, payment method, estimated delivery time

    The user must read this, confirm the address is right, then call POST /orders/place
    with address_confirmed=true.
    """
    client = SwiggyClient(data.swiggy_token)

    try:
        preview = await order_service.prepare_order_preview(client, data.address_id)
    except SwiggyMCPError as exc:
        if "UNAUTHORIZED" in exc.code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Swiggy token expired. Re-authenticate.",
            ) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return preview


@router.post("/place")
async def place_order(data: PlaceOrderIn) -> dict[str, object]:
    """
    Phase 2 — place the order.

    Requires address_confirmed=true. If the user hasn't seen and confirmed the delivery
    address from /orders/confirm, this will be rejected.
    """
    if not data.address_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "address_confirmed must be true. Call POST /orders/confirm first, "
                "show the user the delivery address, then re-submit with address_confirmed=true."
            ),
        )

    client = SwiggyClient(data.swiggy_token)
    try:
        result = await order_service.place_order_after_confirm(
            client, data.address_id, data.address_confirmed
        )
        return result
    except SwiggyMCPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/history")
async def order_history() -> dict[str, object]:
    """Meal log — returns macro and spend history."""
    return {
        "orders": [],
        "note": "Connect your Swiggy account to see meal history.",
    }
