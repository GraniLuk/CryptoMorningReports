# Crypto Morning Reports

Crypto Morning Reports is an Azure Functions project that aggregates market, technical, and news data to publish daily briefings through Telegram and optional document exports.

---

## Key Capabilities

- **Automated Scheduling** – Daily and weekly jobs execute via Azure Functions timers.
- **Telegram Delivery** – Tight integration with Telegram bots for real-time notifications.
- **Document Generation** – Markdown sources can be converted to EPUB using Pandoc, which is fetched dynamically at startup (see below).
- **Flexible Data Sources** – Pulls price, volume, market cap, and sentiment signals from Binance, KuCoin, and external APIs.
- **Modular Architecture** – Shared utilities and domain-specific packages keep the codebase organized and testable.

---

## Getting Started

### Prerequisites

- Python 3.10 or later (aligned with Azure Functions Python worker support).
- Azure Functions Core Tools (for local development and testing).
- Access to an Azure SQL database.
- A Telegram bot token and chat ID for alert delivery.

### Environment Variables

Create a `.env` or configure your Function App settings with the following values:

```ini
TELEGRAM_ENABLED=true
TELEGRAM_TOKEN=<telegram_bot_token>
TELEGRAM_CHAT_ID=<telegram_chat_id>
TELEGRAM_PARSE_MODE=HTML
SQL_PASSWORD=<sql_password>
KUCOIN_API_KEY=<kucoin_api_key>
KUCOIN_API_SECRET=<kucoin_api_secret>
KUCOIN_API_PASSPHRASE=<kucoin_api_passphrase>
PERPLEXITY_API_KEY=<perplexity_api_key>
PANDOC_DOWNLOAD_DIR=<optional_custom_path>
NEWS_ARTICLE_LIMIT=10
CURRENT_REPORT_ARTICLE_LIMIT=3
```

> ℹ️ `PANDOC_DOWNLOAD_DIR` is optional. If omitted, the function uses a cache folder under the script root.
> ℹ️ `NEWS_ARTICLE_LIMIT` controls how many relevant news articles are processed during daily news aggregation (default: 10).
> ℹ️ `CURRENT_REPORT_ARTICLE_LIMIT` controls how many relevant news articles are processed for individual symbol reports (default: 3).

#### Telegram Configuration

The application uses a modular Telegram formatting package (`shared_code/telegram/`) that supports two message formats:

- **`HTML`** (default) – Recommended for most use cases. Uses `<b>`, `<i>`, `<code>`, `<a href="">` tags.
- **`MarkdownV2`** – Telegram's strict markdown format. Requires escaping many special characters.

Set `TELEGRAM_PARSE_MODE` in your environment to switch between formats. If unset or invalid, defaults to `HTML`.

**Example:**
```ini
TELEGRAM_PARSE_MODE=HTML  # or MarkdownV2
```

For detailed usage, formatter examples, and migration guidance, see [`docs/TELEGRAM_FORMATTING.md`](docs/TELEGRAM_FORMATTING.md).

### Install Dependencies

From the project root:

```pwsh
python -m pip install -r requirements.txt
```

If you are using the Azure Functions Core Tools workflow, the provided VS Code tasks handle installation automatically before starting the host.

---

## Pandoc Download Flow

To avoid container images or manual provisioning, the function ensures Pandoc is present at cold start:

1. **Lazy Check** – The first conversion request calls `_ensure_pandoc_available` in `integrations/pandoc_converter.py`.
2. **Download if Missing** – If the Pandoc binary isn't found, the helper downloads the appropriate archive to a writable cache directory using `pypandoc`.
3. **Warm Cache** – Subsequent requests reuse the cached binary. You can pre-warm the cache by invoking any conversion path during startup (e.g., via a timer trigger that creates a dummy EPUB).
4. **Custom Paths** – Override the cache directory with `PANDOC_DOWNLOAD_DIR` when you need a persistent storage mount (for example, Azure Files).

> ✅ The approach works on Consumption and Premium plans as long as outbound internet access is allowed. No container or custom image is required.

---

## Running Locally

```pwsh
func host start
```

The local host exposes HTTP endpoints (see `function_app.py`) and runs scheduled triggers according to the cron expressions defined in the function metadata.

To trigger the daily report manually during development:

```pwsh
Invoke-RestMethod "http://localhost:7071/api/manual-trigger?type=daily" -Method Get
```

---

## Project Layout

```text
CryptoMorningReports/
├── reports/               # Report generation modules (daily, weekly, current status)
├── technical_analysis/    # Indicators (RSI, MACD, moving averages, etc.)
├── news/                  # News aggregation and parsing utilities
├── integrations/          # External services (Pandoc, OneDrive, etc.)
├── infra/                 # Configuration, SQL connectivity, telemetry
├── shared_code/           # Common SDK wrappers and helpers
│   └── telegram/          # Telegram formatting package (HTML/MarkdownV2 support)
├── docs/                  # Documentation (TELEGRAM_FORMATTING.md, etc.)
└── function_app.py        # Azure Functions entry point
```

### Telegram Package

The `shared_code/telegram/` package provides a modular, testable abstraction for Telegram message formatting and sending:

- **Formatters** – Separate `HtmlFormatter` and `MarkdownV2Formatter` classes for consistent formatting
- **Configuration** – Switchable via `TELEGRAM_PARSE_MODE` environment variable
- **Text Processing** – Character escaping, link handling, list formatting utilities
- **Comprehensive Tests** – 99 unit tests with 70% coverage (API-dependent functions excluded)

See [`docs/TELEGRAM_FORMATTING.md`](docs/TELEGRAM_FORMATTING.md) for detailed usage and migration guidance.

---

## Candle Data Architecture

### Overview

The application uses a centralized, source-aware architecture for fetching cryptocurrency candle (OHLCV) data. All candle fetching logic is centralized in `shared_code/price_checker.py`, which intelligently dispatches to exchange-specific batch APIs based on the symbol's source.

### Key Features

- **Intelligent Batch Fetching** – Both Binance and KuCoin symbols use batch APIs for maximum efficiency:
  - **Binance**: Up to 1000 candles per API call
  - **KuCoin**: Up to 1500 candles per API call
- **Database-First Approach** – Checks local SQLite cache before making API calls
- **Source-Aware Dispatch** – Automatically routes to the correct exchange based on `symbol.source_id`
- **Three Timeframes** – Supports daily (1d), hourly (1h), and 15-minute (15m) candles
- **Performance Optimized** – Reduces API calls by ~97% through batch fetching and caching

### Architecture Diagram

```
Reports (daily_report.py, weekly_report.py)
    └─> price_checker.py::fetch_*_candles(symbol, start, end, conn)
            ├─> Check SQLite database for cached candles
            ├─> Identify missing candles in requested range
            ├─> Dispatch by source_id:
            │   ├─> BINANCE → binance.py::fetch_binance_*_klines_batch()
            │   ├─> KUCOIN → kucoin.py::fetch_kucoin_*_klines_batch()
            │   └─> OTHER → Individual fetch (fallback)
            ├─> Save new candles to database
            └─> Return sorted list (cached + newly fetched)
```

### Usage Pattern

```python
from shared_code.price_checker import fetch_daily_candles, fetch_hourly_candles
from datetime import date, datetime, timedelta, UTC
from infra.sql_connection import connect_to_sql

conn = connect_to_sql()

# Fetch daily candles (automatically uses batch API if BINANCE/KUCOIN)
start_date = date.today() - timedelta(days=30)
end_date = date.today()
daily_candles = fetch_daily_candles(symbol, start_date, end_date, conn)

# Fetch hourly candles
start_time = datetime.now(UTC) - timedelta(hours=48)
end_time = datetime.now(UTC)
hourly_candles = fetch_hourly_candles(symbol, start_time, end_time, conn)
```

### Performance Benefits

| Scenario | Before (Individual) | After (Batch) | Improvement |
|----------|---------------------|---------------|-------------|
| 30 daily candles | 30 API calls, ~13s | 1 API call, 0.4s | **31x faster** |
| 48 hourly candles | 48 API calls, ~24s | 1 API call, 0.5s | **47x faster** |
| API call reduction | N/A | N/A | **~97% fewer calls** |

### Implementation Details

- **Binance Batch Functions**: `shared_code/binance.py`
  - `fetch_binance_daily_klines_batch()`
  - `fetch_binance_hourly_klines_batch()`
  - `fetch_binance_fifteen_min_klines_batch()`

- **KuCoin Batch Functions**: `shared_code/kucoin.py`
  - `fetch_kucoin_daily_klines_batch()`
  - `fetch_kucoin_hourly_klines_batch()`
  - `fetch_kucoin_fifteen_min_klines_batch()`

- **Central Dispatcher**: `shared_code/price_checker.py`
  - `fetch_daily_candles()` – Fetches multiple daily candles with caching
  - `fetch_hourly_candles()` – Fetches multiple hourly candles with caching
  - `fetch_fifteen_min_candles()` – Fetches multiple 15-min candles with caching

For detailed implementation documentation, see `plan/feature-price-checker-batch-refactor.md`.

---

## Testing

Run the existing unit tests with:

```pwsh
pytest
```

Add new tests under `tests/` whenever you extend functionality. Focus on keeping external calls mocked so test runs remain fast and deterministic.

---

## Contributing

Contributions are welcome! Please:

- Open an issue describing proposed changes.
- Include tests or sample data updates where relevant.
- Verify `pytest` passes locally before submitting a pull request.

---

## License

MIT License. See [`LICENSE`](LICENSE) for details.