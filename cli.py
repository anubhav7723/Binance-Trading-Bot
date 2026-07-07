#!/usr/bin/env python3
"""
CLI entry point for the simplified Binance Futures Testnet trading bot.

Examples:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
    python cli.py --symbol BTCUSDT --side BUY --type STOP --quantity 0.01 \\
        --price 59000 --stop-price 59500
"""

import argparse
import sys

from bot.client import BinanceFuturesTestnetClient, BotAPIError, BotNetworkError
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import ValidationError, build_order_request

logger = setup_logging()
cli_logger = logger.getChild("cli")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET / LIMIT / STOP orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity (base asset units)")
    parser.add_argument("--price", required=False, default=None, help="Limit price (required for LIMIT/STOP)")
    parser.add_argument(
        "--stop-price", dest="stop_price", required=False, default=None,
        help="Stop trigger price (required for STOP orders)",
    )
    parser.add_argument(
        "--time-in-force", dest="time_in_force", default="GTC",
        choices=["GTC", "IOC", "FOK"], help="Time in force for LIMIT/STOP orders (default: GTC)",
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # 1. Validate input
    try:
        order_request = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        cli_logger.error("Validation failed: %s", exc)
        print(f"❌ Invalid input: {exc}")
        return 1

    # 2. Build client + order manager
    try:
        client = BinanceFuturesTestnetClient()
        manager = OrderManager(client)
    except BotAPIError as exc:
        cli_logger.error("Client initialization failed: %s", exc)
        print(f"❌ Configuration error: {exc}")
        return 1

    # 3. Place the order
    try:
        manager.place_order(order_request)
        return 0
    except BotAPIError as exc:
        cli_logger.error("Order rejected by API: %s", exc)
        print(f"❌ Order failed (API error): {exc}")
        return 1
    except BotNetworkError as exc:
        cli_logger.error("Network failure: %s", exc)
        print(f"❌ Order failed (network error): {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - last-resort safety net, always logged
        cli_logger.exception("Unexpected error placing order")
        print(f"❌ Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
