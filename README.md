# Binance Futures Testnet Trading Bot

A small, structured Python CLI application for placing MARKET, LIMIT, and
STOP (bonus) orders on **Binance Futures Testnet (USDT-M)**.

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance API client wrapper (the only module that touches the network)
    orders.py           # Builds order params from validated input, prints summaries
    validators.py        # Input validation + normalization (no network dependency)
    logging_config.py    # Rotating file + console logging setup
  tests/
    test_validators.py   # Unit tests for validation logic (no API keys needed)
  cli.py                 # CLI entry point (argparse)
  requirements.txt
  .env.example
  README.md
  logs/                  # trading_bot.log written here at runtime
```

The code is split into three layers so each piece can be tested/reused
independently:
- **`validators.py`** — pure functions, no I/O. Turns raw CLI strings into a
  validated `OrderRequest`, or raises `ValidationError` with a specific message.
- **`client.py`** — the API layer. Wraps `python-binance`'s `Client`, pinned to
  the futures testnet, and translates SDK/network exceptions into two clean
  types: `BotAPIError` and `BotNetworkError`.
- **`orders.py`** — the command layer. Takes a validated `OrderRequest`,
  builds the exact API payload, calls the client, and prints a clean
  request/response summary.
- **`cli.py`** — wires the above together and maps exceptions to CLI exit
  codes and friendly error messages.

## Setup

### 1. Create a Binance Futures Demo Trading (Testnet) API key

> **Note:** Binance migrated the old standalone testnet site
> (`testnet.binancefuture.com`) into a **"Demo Trading"** feature built into
> your regular Binance account. The REST base URL also changed to
> `https://demo-fapi.binance.com`. This project targets that current setup.

1. Log in to your regular Binance account and go to
   **https://demo.binance.com/en/my/settings/api-management** (or: Binance
   account → Demo Trading → API Management).
2. Generate an API key/secret pair scoped to Demo Trading. Copy both
   immediately — the secret is only shown once.
3. Demo Trading gives you a virtual balance to place test orders with; use
   the reset/faucet option there if you run low.

### 2. Clone and install dependencies

```bash
git clone <your-repo-url>
cd trading_bot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in your testnet keys, then export them
before running (this project reads plain environment variables — no
`.env`-parsing library is included, to keep dependencies minimal):

```bash
export BINANCE_TESTNET_API_KEY="your_testnet_api_key"
export BINANCE_TESTNET_API_SECRET="your_testnet_api_secret"
```

On Windows PowerShell:
```powershell
$env:BINANCE_TESTNET_API_KEY="your_testnet_api_key"
$env:BINANCE_TESTNET_API_SECRET="your_testnet_api_secret"
```

> If you'd rather auto-load a `.env` file, install `python-dotenv` and add
> `from dotenv import load_dotenv; load_dotenv()` at the top of `cli.py`.
> This was left out intentionally to keep `requirements.txt` minimal.

## Usage

### Market order (BUY)
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order (SELL)
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-limit order (bonus order type)
```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP --quantity 0.01 \
  --price 59000 --stop-price 59500
```

### All CLI options
```
--symbol        Trading pair, e.g. BTCUSDT           (required)
--side          BUY or SELL                          (required)
--type          MARKET, LIMIT, or STOP                (required)
--quantity      Order quantity in base asset units    (required)
--price         Limit price                           (required for LIMIT/STOP)
--stop-price    Stop trigger price                     (required for STOP)
--time-in-force GTC / IOC / FOK, default GTC           (LIMIT/STOP only)
```

Run `python cli.py --help` for the full list.

### Example output

```
--- Order Request Summary ---
  symbol      : BTCUSDT
  side        : BUY
  type        : MARKET
  quantity    : 0.01
------------------------------

--- Order Response ---
  orderId      : 123456789
  status       : FILLED
  executedQty  : 0.01
  avgPrice     : 65123.40
-----------------------

✅ SUCCESS: Order 123456789 placed with status 'FILLED'.
```

On failure (bad params, insufficient balance, network issue, etc.) the CLI
prints a clear `❌` message and exits with a non-zero status code, and the
full error is recorded in `logs/trading_bot.log`.

## Logging

Every order request, the raw API response (or error), and any exceptions are
logged to `logs/trading_bot.log` (rotating at 2MB, 5 backups kept). Console
output stays limited to INFO and above so it's not noisy, while the log file
captures DEBUG-level detail (full request/response payloads) for auditing.

Sample log lines:
```
2026-07-07 10:15:02,113 | INFO     | trading_bot.orders | Placing MARKET BUY order for BTCUSDT: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.01}
2026-07-07 10:15:02,114 | INFO     | trading_bot.client | Sending order request: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.01}
2026-07-07 10:15:02,530 | INFO     | trading_bot.client | Order accepted. Response: {'orderId': 123456789, 'status': 'FILLED', 'executedQty': '0.01', 'avgPrice': '65123.40', ...}
```

## Running tests

Validation logic is unit-tested and requires no API keys or network access:

```bash
python -m unittest discover tests
```

## Error handling

| Scenario                          | Behavior                                                   |
|-----------------------------------|--------------------------------------------------------------|
| Invalid symbol/side/type/quantity | Caught by `validators.py`, prints `❌ Invalid input: ...`, exit code 1, nothing sent to the API |
| Missing price on LIMIT/STOP       | Same as above — caught before any API call                 |
| Missing/invalid API credentials   | `BotAPIError` raised at client init, clear config error message |
| Binance rejects order (e.g. bad symbol, insufficient margin) | `BotAPIError`, logged with the raw exception, friendly CLI message |
| Network/timeout issue             | `BotNetworkError`, logged, friendly CLI message              |
| Anything unexpected                | Caught at the top level, full traceback logged via `logger.exception`, generic friendly message shown |

## Assumptions

- All orders are for **USDT-M perpetual futures** (`futures_create_order`),
  not spot or COIN-M.
- Uses Binance's current Demo Trading endpoint (`https://demo-fapi.binance.com`),
  which replaced the deprecated standalone testnet site.
- Quantities/prices are passed as-is to Binance; the bot does not attempt to
  auto-round to each symbol's `LOT_SIZE`/`PRICE_FILTER` step size. If you get
  a filter-related rejection from Binance, adjust the quantity/price
  precision for that symbol (visible via `/fapi/v1/exchangeInfo` or the
  testnet UI).
- `--time-in-force` defaults to `GTC` and only applies to LIMIT/STOP orders.
- The STOP order type here maps to Binance's `STOP` (stop-limit) futures
  order, requiring both `price` and `stopPrice`.
- Credentials are read from environment variables rather than a config file,
  to avoid ever committing secrets.
- Leverage/margin type are assumed to already be configured on the testnet
  account (via the Binance testnet UI) using their default settings; this
  bot does not set leverage before placing orders.

## Bonus implemented

- **Third order type**: STOP (stop-limit), see `--type STOP` above.
- Structured error hierarchy (`BotAPIError` / `BotNetworkError` /
  `ValidationError`) for precise, non-generic error messages.
- Unit tests for the validation layer.

## Notes on generating the required log-file deliverables

This repository is submitted with the code only; the two log files
(one MARKET order, one LIMIT order) required as deliverables should be
generated by running the commands under **Usage** above against your own
Binance Futures Testnet credentials, then copying the relevant lines from
`logs/trading_bot.log` (or attaching the whole file) alongside this
repository.
