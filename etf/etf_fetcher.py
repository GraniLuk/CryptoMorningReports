"""ETF data fetcher with DefiLlama scraping and YFinance fallback."""

import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import yfinance as yf

from etf.defillama_scraper import scrape_defillama_etf
from infra.telegram_logging_handler import app_logger


# Configure yfinance with new config method (v1.0+)
# Enable retries for transient network errors with exponential backoff
yf.config.network.retries = 3  # type: ignore[attr-defined]
# Enable debug logging for troubleshooting network issues
yf.config.debug.logging = False  # type: ignore[attr-defined]


# ETF ticker symbols by coin type
BTC_ETF_TICKERS = {
    "IBIT": "BlackRock",
    "FBTC": "Fidelity",
    "GBTC": "Grayscale",
    "ARKB": "ARK Invest",
    "BITB": "Bitwise",
    "HODL": "VanEck",
    "BTCO": "Invesco",
    "BRRR": "Valkyrie",
    "EZBC": "Franklin",
}

ETH_ETF_TICKERS = {
    "ETHA": "BlackRock",
    "FETH": "Fidelity",
    "ETHE": "Grayscale",
    "ETHW": "Bitwise",
    "ETHV": "VanEck",
    "QETH": "Invesco",
}


def fetch_yfinance_etf_data() -> list[dict[str, Any]] | None:
    """Fetch ETF data from YFinance API using batch download.

    WARNING: YFinance batch download does NOT provide ETF AUM or flow data.
    This will result in missing/zero flow and AUM values in the database,
    which defeats the purpose of ETF flow tracking. Consider integrating
    an alternative data source for ETF flows and AUM if tracking is required.

    Uses yf.download() to fetch all tickers in a single API call,
    which is much more efficient and avoids rate limiting.

    Returns:
        List of ETF data dictionaries or None if failed
    """
    try:
        app_logger.info("Fetching ETF data from YFinance API (batch mode)...")

        # Combine all tickers
        all_tickers = list(BTC_ETF_TICKERS.keys()) + list(ETH_ETF_TICKERS.keys())
        ticker_list = ", ".join(all_tickers)
        app_logger.info(f"Fetching {len(all_tickers)} ETF tickers in batch: {ticker_list}")

        # Batch download - single API call for all tickers
        # period="1d" gets the most recent trading day
        # group_by='ticker' organizes data by ticker symbol
        data = yf.download(
            tickers=all_tickers,
            period="1d",
            group_by="ticker",
            progress=False,
        )

        if data is None or data.empty:
            app_logger.error("No data returned from YFinance batch download")
            return None

        # Parse the batch data
        etf_data = []
        current_timestamp = int(datetime.now(UTC).timestamp())

        # Process BTC ETFs
        for ticker, issuer in BTC_ETF_TICKERS.items():
            etf_info = _parse_ticker_data(ticker, "BTC", issuer, data, current_timestamp)
            if etf_info:
                etf_data.append(etf_info)

        # Process ETH ETFs
        for ticker, issuer in ETH_ETF_TICKERS.items():
            etf_info = _parse_ticker_data(ticker, "ETH", issuer, data, current_timestamp)
            if etf_info:
                etf_data.append(etf_info)

        if not etf_data:
            app_logger.error("No valid ETF data parsed from batch download")
            return None

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error fetching ETF data from YFinance: {e!s}")
        return None

    else:
        app_logger.info(f"✓ Successfully fetched {len(etf_data)} ETF records from YFinance")
        return etf_data


def _parse_ticker_data(
    ticker: str,
    coin: str,
    issuer: str,
    data: pd.DataFrame,
    timestamp: int,
) -> dict[str, Any] | None:
    """Parse data for a single ticker from batch download results.

    Args:
        ticker: ETF ticker symbol
        coin: Coin type ('BTC' or 'ETH')
        issuer: ETF issuer name
        data: Batch download DataFrame from yfinance
        timestamp: Current Unix timestamp

    Returns:
        Dictionary with ETF data or None if failed
    """
    try:
        # For multi-ticker downloads, data is organized as:
        # data[ticker]['Close'], data[ticker]['Volume'], etc.
        if ticker not in data.columns.get_level_values(0):
            app_logger.debug(f"No data available for {ticker}")
            return None

        ticker_data = data[ticker]

        # Get the most recent closing price
        if "Close" in ticker_data.columns and not ticker_data["Close"].empty:
            price = float(ticker_data["Close"].iloc[-1])
        else:
            app_logger.debug(f"No closing price for {ticker}")
            return None

        # Get volume if available
        volume = None
        if "Volume" in ticker_data.columns and not ticker_data["Volume"].empty:
            volume = float(ticker_data["Volume"].iloc[-1])

        # Note: YFinance batch download doesn't provide AUM or flow data
        # These would need to be fetched separately or calculated
        aum = None
        flows = None
        flows_change = None
        app_logger.warning(
            f"AUM and flows data are not available for {ticker} from YFinance batch download. "
            "Consider integrating an alternative data source for ETF flows and AUM.",
        )

        app_logger.debug(f"Parsed {ticker}: price=${price:.2f}, volume={volume}")

    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Error parsing {ticker}: {e!s}")
        return None
    else:
        return {
            "Ticker": ticker,
            "Coin": coin,
            "Issuer": issuer,
            "Price": price,
            "AUM": aum,
            "Flows": flows,
            "FlowsChange": flows_change,
            "Volume": volume,
            "Date": timestamp,
        }


def fetch_etf_data() -> list[dict[str, Any]] | None:
    """Fetch ETF data using DefiLlama scraping with YFinance fallback.

    Tries to fetch complete ETF data (including flows and AUM) from DefiLlama
    first. If that fails, falls back to YFinance which provides only price
    and volume data.

    Returns:
        List of ETF data dictionaries or None if all sources failed
    """
    # Try DefiLlama scraping first (complete data with flows and AUM)
    app_logger.info("Attempting to fetch ETF data from DefiLlama...")
    try:
        defillama_data = scrape_defillama_etf()

        # Check if we got data from DefiLlama
        if defillama_data is not None:
            if len(defillama_data) > 0:
                app_logger.info(
                    f"✓ Successfully fetched {len(defillama_data)} ETF records from DefiLlama "
                    "(includes flows and AUM data)",
                )
                return defillama_data
            # Empty list means successful scrape but no data - return empty list, don't fallback
            app_logger.warning("DefiLlama returned empty data - no ETFs found")
            return None
    except Exception as e:  # noqa: BLE001
        app_logger.warning(f"DefiLlama scraping encountered error: {e!s}")

    # Fallback to YFinance (limited data: price and volume only)
    app_logger.warning(
        "DefiLlama scraping failed - falling back to YFinance "
        "(WARNING: YFinance does not provide flows/AUM data)",
    )
    return fetch_yfinance_etf_data()


def parse_etf_data(etf_data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Parse and organize ETF data by coin type.

    Args:
        etf_data: Raw ETF data from YFinance API

    Returns:
        Dictionary with 'BTC' and 'ETH' keys containing filtered ETF lists
    """
    btc_etfs = []
    eth_etfs = []

    for etf in etf_data:
        try:
            # Extract and validate required fields
            ticker = etf.get("Ticker", "").strip()
            coin = etf.get("Coin", "").strip().upper()

            if not ticker or not coin:
                app_logger.warning(f"Skipping ETF with missing ticker or coin: {etf}")
                continue

            if coin not in ["BTC", "ETH"]:
                app_logger.debug(f"Skipping non-BTC/ETH ETF: {ticker} ({coin})")
                continue

            # Parse numeric fields with proper handling
            price = _safe_float_parse(etf.get("Price"))
            aum = _safe_float_parse(etf.get("AUM"))
            flows = _safe_float_parse(etf.get("Flows"))
            flows_change = _safe_float_parse(etf.get("FlowsChange"))
            volume = _safe_float_parse(etf.get("Volume"))

            # Parse date (DefiLlama uses Unix timestamp)
            date_timestamp = etf.get("Date")
            if isinstance(date_timestamp, (int, float)):
                fetch_date = datetime.fromtimestamp(date_timestamp, tz=UTC).strftime("%Y-%m-%d")
            else:
                # Fallback to current date if no timestamp
                fetch_date = datetime.now(UTC).date().isoformat()

            # Create structured ETF entry
            etf_entry = {
                "ticker": ticker,
                "coin": coin,
                "issuer": etf.get("Issuer", "").strip() or None,
                "price": price,
                "aum": aum,
                "flows": flows,
                "flows_change": flows_change,
                "volume": volume,
                "fetch_date": fetch_date,
                "raw_data": etf,  # Keep original data for debugging
            }

            # Add to appropriate list
            if coin == "BTC":
                btc_etfs.append(etf_entry)
            else:  # ETH
                eth_etfs.append(etf_entry)

        except Exception as e:  # noqa: BLE001
            app_logger.error(f"Error parsing ETF entry {etf.get('Ticker', 'unknown')}: {e!s}")
            continue

    app_logger.info(f"Parsed ETF data: {len(btc_etfs)} BTC ETFs, {len(eth_etfs)} ETH ETFs")

    return {
        "BTC": btc_etfs,
        "ETH": eth_etfs,
    }


def _safe_float_parse(value: float | int | str | None) -> float | None:
    """Safely parse a value to float, handling None, NaN, and invalid strings.

    Args:
        value: Value to parse

    Returns:
        Float value or None if invalid
    """
    if value is None:
        return None

    try:
        # Handle string representations
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() in ["nan", "null", "none"]:
                return None

        # Convert to float
        result = float(value)

        # Check for NaN or Infinity
        if math.isnan(result) or math.isinf(result):
            return None

    except (ValueError, TypeError, OverflowError):
        return None
    else:
        return result


def get_etf_summary_stats(etf_data: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Generate summary statistics for ETF data.

    Args:
        etf_data: Parsed ETF data by coin type

    Returns:
        Summary statistics for BTC and ETH ETFs
    """
    summary = {}

    for coin, etfs in etf_data.items():
        if not etfs:
            summary[coin] = {
                "count": 0,
                "total_flows": 0,
                "avg_flows": 0,
                "total_aum": 0,
                "issuers": [],
            }
            continue

        total_flows = sum(etf["flows"] for etf in etfs if etf["flows"] is not None)
        total_aum = sum(etf["aum"] for etf in etfs if etf["aum"] is not None)
        issuers = {etf["issuer"] for etf in etfs if etf["issuer"]}

        summary[coin] = {
            "count": len(etfs),
            "total_flows": total_flows,
            "avg_flows": total_flows / len(etfs) if etfs else 0,
            "total_aum": total_aum,
            "issuers": issuers,
        }

    return summary
