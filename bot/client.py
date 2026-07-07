"""
Thin wrapper around python-binance's Client, scoped to Binance Futures Testnet.

This is the ONLY module that talks to the network. Keeping it isolated means:
- orders.py / cli.py never need to know about HTTP, auth, or the SDK directly
- it's the single place to swap in raw `requests` calls later if desired
- errors from the SDK/network are caught here and re-raised as our own
  exception types, so callers only need to handle one hierarchy
"""

import logging
import os

from binance import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from requests.exceptions import RequestException

logger = logging.getLogger("trading_bot.client")

# Binance migrated the old standalone testnet site (testnet.binancefuture.com)
# into "Demo Trading", managed from your normal Binance account at
# https://demo.binance.com/en/my/settings/api-management. The REST base URL
# also changed accordingly. We set it explicitly below rather than relying on
# python-binance's `testnet=True` flag, since older versions of that library
# still point at the deprecated host.
FUTURES_TESTNET_BASE_URL = "https://demo-fapi.binance.com"


class BotAPIError(Exception):
    """Raised when the Binance API rejects a request (bad params, rate limit, etc.)."""


class BotNetworkError(Exception):
    """Raised on connection/timeout problems reaching Binance."""


class BinanceFuturesTestnetClient:
    """
    Wraps python-binance's Client, pinned to the Futures Testnet endpoint.

    Credentials are read from environment variables so they never need to be
    hardcoded or committed:
        BINANCE_TESTNET_API_KEY
        BINANCE_TESTNET_API_SECRET
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        api_key = api_key or os.getenv("BINANCE_TESTNET_API_KEY")
        api_secret = api_secret or os.getenv("BINANCE_TESTNET_API_SECRET")

        if not api_key or not api_secret:
            raise BotAPIError(
                "Missing API credentials. Set BINANCE_TESTNET_API_KEY and "
                "BINANCE_TESTNET_API_SECRET as environment variables (see README)."
            )

        self._client = Client(api_key, api_secret)
        # Explicitly point the futures REST base at Binance's current demo
        # trading endpoint. python-binance's `testnet=True` flag is not used
        # here because older versions of the library still point at the
        # deprecated testnet.binancefuture.com host.
        self._client.FUTURES_URL = FUTURES_TESTNET_BASE_URL + "/fapi"
        logger.debug("Initialized Binance client against futures demo trading (%s)", FUTURES_TESTNET_BASE_URL)

    def get_account_balance(self):
        """Fetch USDT-M futures account balances. Useful for a quick sanity check."""
        logger.debug("Requesting futures account balance")
        try:
            balances = self._client.futures_account_balance()
            logger.debug("Balance response: %s", balances)
            return balances
        except (BinanceAPIException, BinanceOrderException) as exc:
            logger.error("API error fetching balance: %s", exc)
            raise BotAPIError(str(exc)) from exc
        except RequestException as exc:
            logger.error("Network error fetching balance: %s", exc)
            raise BotNetworkError(str(exc)) from exc

    def create_order(self, **params) -> dict:
        """
        Submit a futures order. `params` should match python-binance's
        `futures_create_order` kwargs (symbol, side, type, quantity, price, etc.).

        Logs the outgoing request and the raw response/error for auditability.
        """
        logger.info("Sending order request: %s", params)
        try:
            response = self._client.futures_create_order(**params)
            logger.info("Order accepted. Response: %s", response)
            return response
        except (BinanceAPIException, BinanceOrderException) as exc:
            logger.error("Binance API rejected order %s: %s", params, exc)
            raise BotAPIError(str(exc)) from exc
        except RequestException as exc:
            logger.error("Network error while placing order %s: %s", params, exc)
            raise BotNetworkError(
                f"Could not reach Binance Futures Testnet: {exc}"
            ) from exc

    def get_order_status(self, symbol: str, order_id: int) -> dict:
        """Look up an order after the fact (e.g. to confirm fill status)."""
        logger.debug("Querying order status for %s / orderId=%s", symbol, order_id)
        try:
            response = self._client.futures_get_order(symbol=symbol, orderId=order_id)
            logger.debug("Order status response: %s", response)
            return response
        except (BinanceAPIException, BinanceOrderException) as exc:
            logger.error("API error fetching order status: %s", exc)
            raise BotAPIError(str(exc)) from exc
        except RequestException as exc:
            logger.error("Network error fetching order status: %s", exc)
            raise BotNetworkError(str(exc)) from exc
