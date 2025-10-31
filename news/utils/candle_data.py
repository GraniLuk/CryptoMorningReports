"""Utilities for fetching and formatting candle data for AI analysis."""

import logging

from source_repository import fetch_symbols
from technical_analysis.utilities.candle_formatter import (
    format_candle_data_for_prompt,
    get_candle_data,
)


def fetch_and_format_candle_data(conn) -> str:
    """Fetch and format recent intraday candle data for all tracked symbols.

    This provides recent price action for intraday momentum analysis,
    complementing the longer-term indicators already provided.

    Args:
        conn: Database connection object. If None, returns error message.

    Returns:
        str: Formatted candle data string for AI prompts, or error message.

    """
    if not conn:
        return "No price data available (database connection not provided)."

    try:
        symbols = fetch_symbols(conn)
        # Include all symbols for comprehensive analysis
        candle_data = get_candle_data(symbols, conn, hourly_limit=6, minute_limit=8)
        price_data = format_candle_data_for_prompt(candle_data, max_display_candles=3)
        logging.info(f"Successfully fetched candle data for {len(symbols)} symbols")
        return price_data
    except Exception as e:
        logging.exception(f"Failed to fetch candle data: {e!s}")
        return "No price data available."
