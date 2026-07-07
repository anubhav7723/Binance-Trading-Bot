"""
Input validation for order parameters.

Kept separate from the CLI and API layers so the same rules can be
reused/tested independently, and so argparse stays purely about parsing.
"""

import re
from dataclasses import dataclass
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}  # STOP = bonus stop-limit type
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(Exception):
    """Raised when user-supplied order parameters fail validation."""


@dataclass
class OrderRequest:
    """A validated, normalized order request ready to send to the API layer."""

    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected a format like 'BTCUSDT' "
            "(5-20 uppercase letters/digits)."
        )
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {quantity}.")
    return quantity


def validate_price(price, field_name: str = "price") -> float:
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError(f"{field_name} must be greater than 0, got {price}.")
    return price


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    stop_price=None,
    time_in_force: str = "GTC",
) -> OrderRequest:
    """
    Validate all raw CLI inputs together and return a normalized OrderRequest.

    Raises ValidationError with a clear, specific message on the first problem found.
    """
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)

    parsed_price = None
    parsed_stop_price = None

    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("price is required for LIMIT orders.")
        parsed_price = validate_price(price, "price")

    elif order_type == "STOP":
        if price is None:
            raise ValidationError("price is required for STOP (stop-limit) orders.")
        if stop_price is None:
            raise ValidationError("stop_price is required for STOP (stop-limit) orders.")
        parsed_price = validate_price(price, "price")
        parsed_stop_price = validate_price(stop_price, "stop_price")

    elif order_type == "MARKET":
        if price is not None:
            raise ValidationError("price must not be supplied for MARKET orders.")

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=parsed_price,
        stop_price=parsed_stop_price,
        time_in_force=time_in_force,
    )
