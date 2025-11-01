"""Utility functions for formatting candle data for AI prompts."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from source_repository import Symbol
from technical_analysis.fifteen_min_candle import fetch_fifteen_min_candles
from technical_analysis.hourly_candle import fetch_hourly_candles


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


def get_candle_data(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    hourly_limit: int = 24,
    minute_limit: int = 32,
) -> dict:
    """Fetch hourly and 15-minute candle data for cryptocurrencies.

    Args:
        symbols: List of Symbol objects
        conn: Database connection
        hourly_limit: Number of hourly candles to fetch
        minute_limit: Number of 15-minute candles to fetch

    Returns:
        dict: Dictionary containing formatted candle data for each symbol

    """
    result = {}

    # Get the current time for end time
    end_time = datetime.now(UTC)
    hourly_start_time = end_time - timedelta(hours=hourly_limit)
    fifteen_min_start_time = end_time - timedelta(minutes=minute_limit)

    # Process candles for each symbol
    for symbol in symbols:
        # Fetch candles from database
        hourly_candles = fetch_hourly_candles(
            symbol=symbol,
            start_time=hourly_start_time,
            end_time=end_time,
            conn=conn,
        )
        fifteen_min_candles = fetch_fifteen_min_candles(
            symbol=symbol,
            start_time=fifteen_min_start_time,
            end_time=end_time,
            conn=conn,
        )
        symbol_name = symbol.symbol_name

        # Candles are already filtered by symbol in the fetch functions
        symbol_hourly_candles = hourly_candles
        symbol_fifteen_min_candles = fifteen_min_candles

        # Format the candles
        hourly_data = [
            {
                "time": c.end_date
                if isinstance(c.end_date, str) and "T" in c.end_date
                else (
                    datetime.fromisoformat(c.end_date.replace("Z", "+00:00")).strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                    )
                    if isinstance(c.end_date, str)
                    else c.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                ),
                "o": c.open,
                "h": c.high,
                "l": c.low,
                "c": c.close,
                "v": c.volume,
            }
            for c in sorted(symbol_hourly_candles, key=lambda x: x.end_date)[-hourly_limit:]
        ]

        fifteen_min_data = [
            {
                "time": c.end_date
                if isinstance(c.end_date, str) and "T" in c.end_date
                else (
                    datetime.fromisoformat(c.end_date.replace("Z", "+00:00")).strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                    )
                    if isinstance(c.end_date, str)
                    else c.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                ),
                "o": c.open,
                "h": c.high,
                "l": c.low,
                "c": c.close,
                "v": c.volume,
            }
            for c in sorted(symbol_fifteen_min_candles, key=lambda x: x.end_date)[-minute_limit:]
        ]

        result[symbol_name] = {"hourly": hourly_data, "15m": fifteen_min_data}

    return result


def format_candle_data_for_prompt(candle_data: dict, max_display_candles: int = 5) -> str:
    """Format candle data as a string for prompts.

    Args:
        candle_data: Dictionary of candle data by symbol
        max_display_candles: Maximum number of candles to show in the prompt

    Returns:
        str: Formatted string for prompt

    """
    formatted_text = ""

    for symbol, data in candle_data.items():
        hourly_candles = data.get("hourly", [])
        fifteen_min_candles = data.get("15m", [])

        formatted_text += f"\n{symbol}/USDT:\n"

        # Format hourly candles
        if hourly_candles:
            total_hourly = len(hourly_candles)
            formatted_text += (
                f"- Last {total_hourly} hourly candles "
                f"(showing last {min(max_display_candles, total_hourly)}):\n"
            )
            for candle in hourly_candles[-max_display_candles:]:
                formatted_text += (
                    f"  - Time: {candle['time']}, Open: {candle['o']}, "
                    f"High: {candle['h']}, Low: {candle['l']}, "
                    f"Close: {candle['c']}, Volume: {candle['v']}\n"
                )
        else:
            formatted_text += "- No hourly candles available\n"

        # Format 15-minute candles
        if fifteen_min_candles:
            total_fifteen = len(fifteen_min_candles)
            formatted_text += (
                f"- Last {total_fifteen} fifteen-minute candles "
                f"(showing last {min(max_display_candles, total_fifteen)}):\n"
            )
            for candle in fifteen_min_candles[-max_display_candles:]:
                formatted_text += (
                    f"  - Time: {candle['time']}, Open: {candle['o']}, "
                    f"High: {candle['h']}, Low: {candle['l']}, "
                    f"Close: {candle['c']}, Volume: {candle['v']}\n"
                )
        else:
            formatted_text += "- No fifteen-minute candles available\n"

    return formatted_text


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    btc_eth = [symbol for symbol in symbols if symbol.symbol_name in ["BTC", "ETH"]]

    # Test database fetching
    candle_data = get_candle_data(btc_eth, conn)
