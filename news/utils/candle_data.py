"""Utilities for fetching and formatting candle data for AI analysis."""

import logging

from source_repository import fetch_symbols
from technical_analysis.utilities.candle_formatter import (
    format_candle_data_for_prompt,
    get_candle_data,
)


def fetch_and_format_candle_data(conn) -> str:
    """
    Fetch and format candle data for BTC and ETH.
    
    Args:
        conn: Database connection object. If None, returns error message.
        
    Returns:
        str: Formatted candle data string for AI prompts, or error message.
    """
    if not conn:
        return "No price data available (database connection not provided)."
    
    try:
        symbols = fetch_symbols(conn)
        # Filter for BTC and ETH
        btc_eth = [
            symbol for symbol in symbols if symbol.symbol_name in ["BTC", "ETH"]
        ]
        candle_data = get_candle_data(btc_eth, conn)
        price_data = format_candle_data_for_prompt(candle_data)
        logging.info("Successfully fetched candle data for analysis")
        return price_data
    except Exception as e:
        logging.error(f"Failed to fetch candle data: {str(e)}")
        return "No price data available."
