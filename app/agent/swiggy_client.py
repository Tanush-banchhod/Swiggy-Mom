"""All Swiggy MCP tool calls go through this module.

Uses streamable HTTP transport with Bearer auth.
On 401: caller should re-run OAuth and retry once.
On UPSTREAM_ERROR: treat as retriable.
"""

from typing import Any

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class SwiggyMCPError(Exception):
    def __init__(self, code: str, message: str, retriable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retriable = retriable


class SwiggyClient:
    """Thin async wrapper around the Swiggy MCP streamable HTTP endpoint."""

    def __init__(self, access_token: str) -> None:
        self._token = access_token
        self._food_url = settings.swiggy_food_mcp_url
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    async def _call(self, server_url: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(server_url, json=payload, headers=self._headers)

        if resp.status_code == 401:
            raise SwiggyMCPError("UNAUTHORIZED", "Swiggy token expired — re-run OAuth", retriable=False)

        if resp.status_code >= 500:
            raise SwiggyMCPError("UPSTREAM_ERROR", f"Swiggy 5xx: {resp.status_code}", retriable=True)

        data = resp.json()
        if "error" in data:
            err = data["error"]
            msg = err.get("message", "unknown error")
            retriable = "UPSTREAM_ERROR" in msg or "rate limit" in msg.lower()
            raise SwiggyMCPError(str(err.get("code", "MCP_ERROR")), msg, retriable=retriable)

        result = data.get("result", {})
        content = result.get("content", [])
        # MCP tools return content as a list of {type, text} blocks
        if content and isinstance(content, list):
            import json
            for block in content:
                if block.get("type") == "text":
                    try:
                        return json.loads(block["text"])
                    except (json.JSONDecodeError, KeyError):
                        return block.get("text")
        return result

    # ── Food tools ──────────────────────────────────────────────────────────

    async def get_addresses(self) -> list[dict[str, Any]]:
        result = await self._call(self._food_url, "get_addresses", {})
        return result.get("addresses", []) if isinstance(result, dict) else []

    async def search_restaurants(self, address_id: str, query: str = "") -> list[dict[str, Any]]:
        args: dict[str, Any] = {"addressId": address_id}
        if query:
            args["query"] = query
        result = await self._call(self._food_url, "search_restaurants", args)
        return result.get("restaurants", []) if isinstance(result, dict) else []

    async def get_restaurant_menu(
        self, restaurant_id: str, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        result = await self._call(
            self._food_url,
            "get_restaurant_menu",
            {"restaurantId": restaurant_id, "page": page, "pageSize": page_size},
        )
        return result if isinstance(result, dict) else {}

    async def search_menu(self, restaurant_id: str, query: str) -> list[dict[str, Any]]:
        result = await self._call(
            self._food_url,
            "search_menu",
            {"restaurantId": restaurant_id, "query": query},
        )
        return result.get("items", []) if isinstance(result, dict) else []

    async def get_food_cart(self, address_id: str) -> dict[str, Any]:
        result = await self._call(self._food_url, "get_food_cart", {"addressId": address_id})
        return result if isinstance(result, dict) else {}

    async def update_food_cart(
        self, restaurant_id: str, item_id: str, quantity: int, address_id: str
    ) -> dict[str, Any]:
        result = await self._call(
            self._food_url,
            "update_food_cart",
            {
                "restaurantId": restaurant_id,
                "itemId": item_id,
                "quantity": quantity,
                "addressId": address_id,
            },
        )
        return result if isinstance(result, dict) else {}

    async def flush_food_cart(self) -> None:
        await self._call(self._food_url, "flush_food_cart", {})

    async def fetch_food_coupons(self) -> list[dict[str, Any]]:
        result = await self._call(self._food_url, "fetch_food_coupons", {})
        return result.get("coupons", []) if isinstance(result, dict) else []

    async def apply_food_coupon(self, coupon_code: str) -> dict[str, Any]:
        result = await self._call(self._food_url, "apply_food_coupon", {"couponCode": coupon_code})
        return result if isinstance(result, dict) else {}

    async def place_food_order(self, payment_method: str = "COD") -> dict[str, Any]:
        result = await self._call(
            self._food_url, "place_food_order", {"paymentMethod": payment_method}
        )
        return result if isinstance(result, dict) else {}

    async def get_food_orders(self) -> list[dict[str, Any]]:
        result = await self._call(self._food_url, "get_food_orders", {})
        return result.get("orders", []) if isinstance(result, dict) else []

    async def track_food_order(self, order_id: str) -> dict[str, Any]:
        result = await self._call(self._food_url, "track_food_order", {"orderId": order_id})
        return result if isinstance(result, dict) else {}
