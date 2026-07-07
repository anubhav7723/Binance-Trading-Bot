"""
Unit tests for bot.validators. These require no network access or API
credentials, so they can run in CI as-is.

Run with:  python -m pytest tests/  (or: python -m unittest discover)
"""

import unittest

from bot.validators import ValidationError, build_order_request


class TestValidators(unittest.TestCase):

    def test_valid_market_order(self):
        req = build_order_request("btcusdt", "buy", "market", "0.01")
        self.assertEqual(req.symbol, "BTCUSDT")
        self.assertEqual(req.side, "BUY")
        self.assertEqual(req.order_type, "MARKET")
        self.assertEqual(req.quantity, 0.01)
        self.assertIsNone(req.price)

    def test_valid_limit_order(self):
        req = build_order_request("ETHUSDT", "SELL", "LIMIT", "1.5", price="3000")
        self.assertEqual(req.order_type, "LIMIT")
        self.assertEqual(req.price, 3000.0)

    def test_limit_requires_price(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "LIMIT", "0.01")

    def test_market_rejects_price(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "MARKET", "0.01", price="100")

    def test_invalid_symbol(self):
        with self.assertRaises(ValidationError):
            build_order_request("btc-usdt", "BUY", "MARKET", "0.01")

    def test_invalid_side(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "HOLD", "MARKET", "0.01")

    def test_invalid_order_type(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "TWAP", "0.01")

    def test_negative_quantity(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "MARKET", "-1")

    def test_non_numeric_quantity(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "MARKET", "abc")

    def test_stop_order_requires_price_and_stop_price(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "STOP", "0.01", price="59000")

    def test_valid_stop_order(self):
        req = build_order_request(
            "BTCUSDT", "BUY", "STOP", "0.01", price="59000", stop_price="59500"
        )
        self.assertEqual(req.price, 59000.0)
        self.assertEqual(req.stop_price, 59500.0)


if __name__ == "__main__":
    unittest.main()
