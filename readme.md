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
SQL_PASSWORD=<sql_password>
KUCOIN_API_KEY=<kucoin_api_key>
KUCOIN_API_SECRET=<kucoin_api_secret>
KUCOIN_API_PASSPHRASE=<kucoin_api_passphrase>
PERPLEXITY_API_KEY=<perplexity_api_key>
PANDOC_DOWNLOAD_DIR=<optional_custom_path>
```

> ℹ️ `PANDOC_DOWNLOAD_DIR` is optional. If omitted, the function uses a cache folder under the script root.

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
├── sharedCode/            # Common SDK wrappers and helpers
└── function_app.py        # Azure Functions entry point
```

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