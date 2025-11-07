"""ETF data fetcher for DefiLlama API integration."""

import math
import time
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import requests

from infra.telegram_logging_handler import app_logger


# DefiLlama ETF API endpoint
ETF_API_URL = "https://defillama.com/api/etfs"


def fetch_defillama_etf_data(max_retries: int = 3) -> list[dict[str, Any]] | None:
    """Fetch ETF data from DefiLlama API.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        List of ETF data dictionaries or None if failed
    """
    headers = _get_api_headers()

    for attempt in range(max_retries):
        try:
            app_logger.info(
                f"Fetching ETF data from DefiLlama API (attempt {attempt + 1}/{max_retries})",
            )

            response = requests.get(ETF_API_URL, headers=headers, timeout=30)

            # Handle HTTP errors
            result = _handle_http_response(response, attempt, max_retries)
            if result is not None:
                return result

            # Parse and validate JSON
            data = _parse_and_validate_json(response, attempt, max_retries)
            if data is None:
                continue

            # Validate ETF data structure
            if not _validate_etf_data_structure(data, attempt, max_retries):
                continue

        except requests.exceptions.Timeout:
            if not _handle_retry(attempt, max_retries, "Timeout fetching ETF data"):
                return _get_mock_etf_data()
            continue

        except requests.exceptions.RequestException as e:
            app_logger.error(f"Network error fetching ETF data: {e!s}")
            if not _handle_retry(attempt, max_retries, None):
                return None
            continue

        except Exception as e:  # noqa: BLE001
            if not _handle_retry(attempt, max_retries, f"Unexpected error: {e!s}"):
                return _get_mock_etf_data()
            continue

        else:
            # Log success and return data
            _log_success_statistics(data)
            return data

    # All retries exhausted
    app_logger.error("Failed to fetch ETF data after all retry attempts")
    app_logger.warning("Using mock ETF data as fallback")
    return _get_mock_etf_data()


def _get_api_headers() -> dict[str, str]:
    """Get headers to mimic a real browser and bypass Cloudflare."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def _handle_http_response(
    response: requests.Response,
    attempt: int,
    max_retries: int,
) -> list[dict[str, Any]] | None:
    """Handle HTTP response status codes.

    Returns:
        Mock data if final attempt failed, None to continue retry loop
    """
    if response.status_code == HTTPStatus.OK:
        return None  # Continue with normal processing

    app_logger.error(
        f"DefiLlama API returned HTTP {response.status_code}: {response.text}",
    )

    if attempt < max_retries - 1:
        _retry_with_backoff(attempt)
        return None

    app_logger.warning("All HTTP error retries failed, using mock data as fallback")
    return _get_mock_etf_data()


def _parse_and_validate_json(
    response: requests.Response,
    attempt: int,
    max_retries: int,
) -> list[dict[str, Any]] | None:
    """Parse JSON response and validate structure.

    Returns:
        Parsed data if successful, None if should retry
    """
    try:
        data = response.json()
    except ValueError as e:
        app_logger.error(f"Failed to parse JSON response: {e!s}")
        if attempt >= max_retries - 1:
            app_logger.warning(
                "JSON parsing failed after all retries, using mock data as fallback",
            )
            return _get_mock_etf_data()
        _retry_with_backoff(attempt)
        return None

    # Validate response is a list
    if not isinstance(data, list):
        app_logger.error(f"Unexpected response format: expected list, got {type(data)}")
        if attempt >= max_retries - 1:
            app_logger.warning(
                "Response validation failed after all retries, using mock data as fallback",
            )
            return _get_mock_etf_data()
        _retry_with_backoff(attempt)
        return None

    # Empty data is valid but noteworthy
    if not data:
        app_logger.warning("DefiLlama API returned empty ETF data")

    return data


def _validate_etf_data_structure(
    data: list[dict[str, Any]],
    attempt: int,
    max_retries: int,
) -> bool:
    """Validate that ETF data has required fields.

    Returns:
        True if validation passed, False if should retry
    """
    if not data:
        return True  # Empty data is valid

    first_etf = data[0]
    required_fields = ["Ticker", "Coin", "Flows", "Date"]
    missing_fields = [field for field in required_fields if field not in first_etf]

    if not missing_fields:
        return True

    app_logger.error(f"ETF data missing required fields: {missing_fields}")

    if attempt >= max_retries - 1:
        app_logger.warning(
            "Data validation failed after all retries, using mock data as fallback",
        )
        return False

    _retry_with_backoff(attempt)
    return False


def _log_success_statistics(data: list[dict[str, Any]]) -> None:
    """Log statistics about successfully fetched ETF data."""
    btc_count = sum(1 for etf in data if etf.get("Coin") == "BTC")
    eth_count = sum(1 for etf in data if etf.get("Coin") == "ETH")

    app_logger.info(
        f"Successfully fetched {len(data)} ETFs: {btc_count} BTC ETFs, {eth_count} ETH ETFs",
    )


def _handle_retry(attempt: int, max_retries: int, error_msg: str | None) -> bool:
    """Handle retry logic with exponential backoff.

    Args:
        attempt: Current attempt number
        max_retries: Maximum retry attempts
        error_msg: Optional error message to log

    Returns:
        True if should continue retry loop, False if exhausted
    """
    if error_msg:
        app_logger.error(f"{error_msg} (attempt {attempt + 1})")

    if attempt < max_retries - 1:
        _retry_with_backoff(attempt)
        return True

    return False


def _retry_with_backoff(attempt: int) -> None:
    """Sleep with exponential backoff before retry."""
    sleep_time = 2**attempt
    app_logger.info(f"Retrying in {sleep_time} seconds...")
    time.sleep(sleep_time)


def parse_etf_data(etf_data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Parse and organize ETF data by coin type.

    Args:
        etf_data: Raw ETF data from DefiLlama API

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


def _get_mock_etf_data() -> list[dict[str, Any]]:
    """Return mock ETF data for fallback when API is unavailable.

    Returns:
        List of mock ETF data dictionaries
    """
    # Current timestamp
    current_timestamp = int(datetime.now(UTC).timestamp())

    mock_data = [
        {
            "Ticker": "IBIT",
            "Coin": "BTC",
            "Issuer": "BlackRock",
            "Price": 42.50,
            "AUM": 1000000000,
            "Flows": 50000000,
            "FlowsChange": 10000000,
            "Volume": 200000000,
            "Date": current_timestamp,
        },
        {
            "Ticker": "GBTC",
            "Coin": "BTC",
            "Issuer": "Grayscale",
            "Price": 38.75,
            "AUM": 800000000,
            "Flows": 25000000,
            "FlowsChange": 5000000,
            "Volume": 150000000,
            "Date": current_timestamp,
        },
        {
            "Ticker": "ETHE",
            "Coin": "ETH",
            "Issuer": "Grayscale",
            "Price": 25.30,
            "AUM": 500000000,
            "Flows": 30000000,
            "FlowsChange": 8000000,
            "Volume": 120000000,
            "Date": current_timestamp,
        },
        {
            "Ticker": "ETHW",
            "Coin": "ETH",
            "Issuer": "Bitwise",
            "Price": 22.15,
            "AUM": 300000000,
            "Flows": 15000000,
            "FlowsChange": 3000000,
            "Volume": 80000000,
            "Date": current_timestamp,
        },
    ]

    app_logger.info(f"Using mock ETF data with {len(mock_data)} entries")
    return mock_data
