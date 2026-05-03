from pydantic import BaseModel


class ConfirmOrderIn(BaseModel):
    suggestion_slot: int  # 1, 2, or 3
    address_id: str
    swiggy_token: str  # passed client-side after OAuth (dev mode); removed in prod


class PlaceOrderIn(BaseModel):
    suggestion_slot: int
    address_id: str
    swiggy_token: str
    address_confirmed: bool  # must be True — user explicitly acknowledged the delivery address


class OrderOut(BaseModel):
    status: str
    order_id: str | None = None
    details: dict | None = None
