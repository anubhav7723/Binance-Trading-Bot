"""
Order placement logic: turns a validated OrderRequest into a Binance API
call, and turns the API response into a clean summary for the user.
"""

import logging

from bot.client import BinanceFuturesTestnetClient, BotAPIError, BotNetworkError
from bot.validators import OrderRequest

logger = logging.getLogger("trading_bot.orders")


class OrderManager:
    """Coordinates validated order requests against the Binance client."""

    def __init__(self, client: BinanceFuturesTestnetClient):
        self._client = client

    def _build_api_params(self, req: OrderRequest) -> dict:
        params = {
            "symbol": req.symbol,
            "side": req.side,
            "type": req.order_type,
            "quantity": req.quantity,
        }

        if req.order_type == "LIMIT":
            params["price"] = req.price
            params["timeInForce"] = req.time_in_force

        elif req.order_type == "STOP":
            # Binance futures stop-limit order: requires stopPrice + price + timeInForce
            params["price"] = req.price
            params["stopPrice"] = req.stop_price
            params["timeInForce"] = req.time_in_force

        # MARKET orders need only symbol/side/type/quantity.
        return params

    def place_order(self, req: OrderRequest) -> dict:
        """
        Place an order on Binance Futures Testnet.

        Returns the raw API response dict on success.
        Raises BotAPIError / BotNetworkError on failure (caller handles presentation).
        """
        params = self._build_api_params(req)

        print("\n--- Order Request Summary ---")
        for key, value in params.items():
            print(f"  {key:12s}: {value}")
        print("------------------------------")

        logger.info("Placing %s %s order for %s: %s", req.order_type, req.side, req.symbol, params)

        response = self._client.create_order(**params)

        self._print_response_summary(response)
        return response

    @staticmethod
    def _print_response_summary(response: dict) -> None:
        order_id = response.get("orderId")
        status = response.get("status")
        executed_qty = response.get("executedQty")
        avg_price = response.get("avgPrice")

        print("\n--- Order Response ---")
        print(f"  orderId      : {order_id}")
        print(f"  status       : {status}")
        print(f"  executedQty  : {executed_qty}")
        if avg_price is not None:
            print(f"  avgPrice     : {avg_price}")
        print("-----------------------")

        if status in ("NEW", "FILLED", "PARTIALLY_FILLED"):
            print(f"\n✅ SUCCESS: Order {order_id} placed with status '{status}'.\n")
        else:
            print(f"\n⚠️  Order {order_id} returned status '{status}'. Check details above.\n")
