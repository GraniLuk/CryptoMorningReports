"""
Module for generating current data tables with latest indicators for crypto symbols.
This module can be easily extended to add more indicators in the future.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.reports.rsi_multi_timeframe import get_rsi_for_symbol_timeframe


def get_latest_price_from_candles(
    candles_df: Optional[pd.DataFrame],
) -> Optional[float]:
    """
    Extract the latest price from candles DataFrame.

    Args:
        candles_df: DataFrame with candle data or None

    Returns:
        Latest close price or None if no data
    """
    if candles_df is None or candles_df.empty:
        return None

    try:
        return float(candles_df["Close"].iloc[-1])
    except (IndexError, KeyError, ValueError):
        return None


def get_latest_rsi_from_df(rsi_df: Optional[pd.DataFrame]) -> Optional[float]:
    """
    Extract the latest RSI value from RSI DataFrame.

    Args:
        rsi_df: DataFrame with RSI data or None

    Returns:
        Latest RSI value or None if no data
    """
    if rsi_df is None or rsi_df.empty:
        return None

    try:
        latest_rsi = rsi_df["RSI"].iloc[-1]
        if pd.notna(latest_rsi):
            return float(latest_rsi)
    except (IndexError, KeyError, ValueError):
        pass

    return None


def get_current_data_for_symbol(symbol: Symbol, conn) -> Dict[str, Any]:
    """
    Get current data for a single symbol including latest price and RSI across timeframes.

    Args:
        symbol: Symbol object
        conn: Database connection

    Returns:
        Dictionary containing current data for the symbol
    """
    data = {
        "symbol": symbol.symbol_name,
        "latest_price": None,
        "daily_rsi": None,
        "hourly_rsi": None,
        "fifteen_min_rsi": None,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        # Get RSI data for different timeframes
        daily_rsi_df = get_rsi_for_symbol_timeframe(
            symbol, conn, "daily", lookback_days=7
        )
        hourly_rsi_df = get_rsi_for_symbol_timeframe(
            symbol, conn, "hourly", lookback_days=2
        )
        fifteen_min_rsi_df = get_rsi_for_symbol_timeframe(
            symbol, conn, "fifteen_min", lookback_days=1
        )

        # Extract latest price (prefer 15min, then hourly, then daily)
        if fifteen_min_rsi_df is not None and not fifteen_min_rsi_df.empty:
            data["latest_price"] = get_latest_price_from_candles(fifteen_min_rsi_df)
        elif hourly_rsi_df is not None and not hourly_rsi_df.empty:
            data["latest_price"] = get_latest_price_from_candles(hourly_rsi_df)
        elif daily_rsi_df is not None and not daily_rsi_df.empty:
            data["latest_price"] = get_latest_price_from_candles(daily_rsi_df)

        # Extract RSI values for each timeframe
        data["daily_rsi"] = get_latest_rsi_from_df(daily_rsi_df)
        data["hourly_rsi"] = get_latest_rsi_from_df(hourly_rsi_df)
        data["fifteen_min_rsi"] = get_latest_rsi_from_df(fifteen_min_rsi_df)

        app_logger.info(f"Successfully retrieved current data for {symbol.symbol_name}")

    except Exception as e:
        app_logger.error(
            f"Error getting current data for {symbol.symbol_name}: {str(e)}"
        )

    return data


def format_current_data_table(symbol_data: Dict[str, Any]) -> str:
    """
    Format current data for a single symbol into a markdown table.

    Args:
        symbol_data: Dictionary containing current data for the symbol

    Returns:
        Markdown formatted table string
    """
    symbol_name = symbol_data.get("symbol", "Unknown")
    timestamp = symbol_data.get("timestamp", "Unknown")

    # Format price
    latest_price = symbol_data.get("latest_price")
    price_str = f"${latest_price:,.4f}" if latest_price is not None else "N/A"

    # Format RSI values
    daily_rsi = symbol_data.get("daily_rsi")
    daily_rsi_str = f"{daily_rsi:.2f}" if daily_rsi is not None else "N/A"

    hourly_rsi = symbol_data.get("hourly_rsi")
    hourly_rsi_str = f"{hourly_rsi:.2f}" if hourly_rsi is not None else "N/A"

    fifteen_min_rsi = symbol_data.get("fifteen_min_rsi")
    fifteen_min_rsi_str = (
        f"{fifteen_min_rsi:.2f}" if fifteen_min_rsi is not None else "N/A"
    )

    # Create markdown table
    table_md = f"""
## Current Market Data for {symbol_name}

*Data retrieved at: {timestamp}*

| Indicator | Value |
|-----------|-------|
| **Latest Price** | {price_str} |
| **Daily RSI** | {daily_rsi_str} |
| **Hourly RSI** | {hourly_rsi_str} |
| **15-min RSI** | {fifteen_min_rsi_str} |

"""

    return table_md


def get_current_data_summary_table(symbol: Symbol, conn) -> str:
    """
    Generate a summary table of current data for a symbol.
    This function can be easily extended to include more indicators.

    Args:
        symbol: Symbol object
        conn: Database connection

    Returns:
        Markdown formatted table with current data
    """
    try:
        # Get current data
        symbol_data = get_current_data_for_symbol(symbol, conn)

        # Format as table
        return format_current_data_table(symbol_data)

    except Exception as e:
        app_logger.error(
            f"Error generating current data summary for {symbol.symbol_name}: {str(e)}"
        )
        return f"# Error\n\nFailed to retrieve current data for {symbol.symbol_name}: {str(e)}"


def get_current_data_for_ai_prompt(symbol: Symbol, conn) -> str:
    """
    Generate current data in a format suitable for AI prompts.

    Args:
        symbol: Symbol object
        conn: Database connection

    Returns:
        Formatted string for AI prompt
    """
    try:
        # Get current data
        symbol_data = get_current_data_for_symbol(symbol, conn)

        # Format for AI prompt
        latest_price = symbol_data.get("latest_price")
        price_str = f"${latest_price:,.4f}" if latest_price is not None else "N/A"

        daily_rsi = symbol_data.get("daily_rsi")
        daily_rsi_str = f"{daily_rsi:.2f}" if daily_rsi is not None else "N/A"

        hourly_rsi = symbol_data.get("hourly_rsi")
        hourly_rsi_str = f"{hourly_rsi:.2f}" if hourly_rsi is not None else "N/A"

        fifteen_min_rsi = symbol_data.get("fifteen_min_rsi")
        fifteen_min_rsi_str = (
            f"{fifteen_min_rsi:.2f}" if fifteen_min_rsi is not None else "N/A"
        )

        timestamp = symbol_data.get("timestamp", "Unknown")

        prompt_data = f"""
CURRENT MARKET SNAPSHOT ({symbol_data.get("symbol", "Unknown")}):
- Current Price: {price_str}
- Daily RSI: {daily_rsi_str}
- Hourly RSI: {hourly_rsi_str}
- 15-minute RSI: {fifteen_min_rsi_str}
- Data timestamp: {timestamp}
"""

        return prompt_data.strip()

    except Exception as e:
        app_logger.error(
            f"Error generating AI prompt data for {symbol.symbol_name}: {str(e)}"
        )
        return (
            f"CURRENT MARKET SNAPSHOT: Error retrieving data for {symbol.symbol_name}"
        )


# Future extension functions can be added here:
#
# def add_moving_averages_to_data(symbol_data: Dict[str, Any], symbol: Symbol, conn) -> Dict[str, Any]:
#     """Add moving averages data to symbol data dictionary."""
#     pass
#
# def add_volume_data_to_data(symbol_data: Dict[str, Any], symbol: Symbol, conn) -> Dict[str, Any]:
#     """Add volume indicators to symbol data dictionary."""
#     pass
#
# def add_momentum_indicators_to_data(symbol_data: Dict[str, Any], symbol: Symbol, conn) -> Dict[str, Any]:
#     """Add MACD, Stochastic, etc. to symbol data dictionary."""
#     pass


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbol_by_name

    load_dotenv()
    conn = connect_to_sql()

    # Test with a symbol
    symbol = fetch_symbol_by_name(conn, "BTC")
    if symbol:
        print("=== Current Data Summary Table ===")
        print(get_current_data_summary_table(symbol, conn))

        print("\n=== AI Prompt Format ===")
        print(get_current_data_for_ai_prompt(symbol, conn))
    else:
        print("Symbol not found")
