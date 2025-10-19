"""
Module for generating current data tables with latest indicators for crypto symbols.
This module can be easily extended to add more indicators in the future.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pandas as pd

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.reports.rsi_multi_timeframe import get_rsi_for_symbol_timeframe
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.moving_averages_repository import (
    fetch_moving_averages_for_symbol,
)


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
        # Moving averages
        "ma50": None,
        "ma200": None,
        "ema50": None,
        "ema200": None,
        # Daily range related fields
        "daily_high": None,
        "daily_low": None,
        "daily_range": None,
        "daily_range_pct": None,
        "daily_ranges_7d": [],
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

        # Fetch moving averages data (latest values)
        try:
            ma_df = fetch_moving_averages_for_symbol(
                conn, symbol.symbol_id, lookback_days=1
            )
            if ma_df is not None and not ma_df.empty:
                latest_ma = ma_df.iloc[-1]
                data["ma50"] = (
                    float(latest_ma["MA50"])
                    if pd.notna(latest_ma.get("MA50"))
                    else None
                )
                data["ma200"] = (
                    float(latest_ma["MA200"])
                    if pd.notna(latest_ma.get("MA200"))
                    else None
                )
                data["ema50"] = (
                    float(latest_ma["EMA50"])
                    if pd.notna(latest_ma.get("EMA50"))
                    else None
                )
                data["ema200"] = (
                    float(latest_ma["EMA200"])
                    if pd.notna(latest_ma.get("EMA200"))
                    else None
                )
        except Exception as ma_error:
            app_logger.warning(
                f"Could not fetch moving averages for {symbol.symbol_name}: {ma_error}"
            )

        # Fetch daily candles (look back 7 days) to compute daily range and recent history
        try:
            daily_repo = DailyCandleRepository(conn)
            now_utc = datetime.now(timezone.utc)
            start = now_utc - timedelta(days=7)
            candles = daily_repo.get_candles(symbol, start, now_utc)
            if candles:
                # Latest candle for headline metrics
                last_candle = candles[-1]
                high = float(last_candle.high)
                low = float(last_candle.low)
                if low is not None and high is not None and low > 0:
                    rng = high - low
                    rng_pct = (rng / low) * 100.0
                    data["daily_high"] = high
                    data["daily_low"] = low
                    data["daily_range"] = rng
                    data["daily_range_pct"] = rng_pct

                # Build 7-day history (up to 7 most recent candles)
                recent = candles[-7:]
                ranges = []
                for c in recent:
                    try:
                        c_high = float(c.high)
                        c_low = float(c.low)
                        if c_low is not None and c_high is not None and c_low > 0:
                            c_range = c_high - c_low
                            c_range_pct = (c_range / c_low) * 100.0
                        else:
                            c_range = None
                            c_range_pct = None
                        ranges.append(
                            {
                                "date": c.end_date.strftime("%Y-%m-%d"),
                                "high": c_high if c_high is not None else None,
                                "low": c_low if c_low is not None else None,
                                "range": c_range,
                                "range_pct": c_range_pct,
                            }
                        )
                    except Exception:
                        continue
                data["daily_ranges_7d"] = ranges
        except Exception as inner_e:
            app_logger.warning(
                f"Could not compute daily range for {symbol.symbol_name}: {inner_e}"
            )

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

    # Format moving averages
    ma50 = symbol_data.get("ma50")
    ma50_str = f"${ma50:,.4f}" if ma50 is not None else "N/A"

    ma200 = symbol_data.get("ma200")
    ma200_str = f"${ma200:,.4f}" if ma200 is not None else "N/A"

    ema50 = symbol_data.get("ema50")
    ema50_str = f"${ema50:,.4f}" if ema50 is not None else "N/A"

    ema200 = symbol_data.get("ema200")
    ema200_str = f"${ema200:,.4f}" if ema200 is not None else "N/A"

    # Daily range values
    daily_high = symbol_data.get("daily_high")
    daily_low = symbol_data.get("daily_low")
    daily_range = symbol_data.get("daily_range")
    daily_range_pct = symbol_data.get("daily_range_pct")

    if daily_high is not None and daily_low is not None:
        high_str = f"${daily_high:,.4f}"
        low_str = f"${daily_low:,.4f}"
    else:
        high_str = low_str = "N/A"

    if daily_range is not None and daily_range_pct is not None:
        range_str = f"${daily_range:,.4f} ({daily_range_pct:.2f}%)"
    else:
        range_str = "N/A"

    # Last 7 days ranges table
    ranges_7d = symbol_data.get("daily_ranges_7d", [])
    if ranges_7d:
        history_table = "\n### Last 7 Daily Ranges\n\n| Date | High | Low | Range | Range % |\n|------|------|-----|-------|---------|\n"
        for r in ranges_7d:
            high_str = f"${r['high']:,.4f}" if r.get("high") is not None else "N/A"
            low_str = f"${r['low']:,.4f}" if r.get("low") is not None else "N/A"
            rng_val = r.get("range")
            rng_pct_val = r.get("range_pct")
            rng_str = f"${rng_val:,.4f}" if rng_val is not None else "N/A"
            rng_pct_str = f"{rng_pct_val:.2f}%" if rng_pct_val is not None else "N/A"
            history_table += f"| {r.get('date', '')} | {high_str} | {low_str} | {rng_str} | {rng_pct_str} |\n"
    else:
        history_table = "\n_No recent daily range data available_\n"

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
| **MA50** | {ma50_str} |
| **MA200** | {ma200_str} |
| **EMA50** | {ema50_str} |
| **EMA200** | {ema200_str} |
| **Daily High** | {high_str} |
| **Daily Low** | {low_str} |
| **Daily Range (H-L)** | {range_str} |

{history_table}

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

        # Format moving averages
        ma50 = symbol_data.get("ma50")
        ma50_str = f"${ma50:,.4f}" if ma50 is not None else "N/A"

        ma200 = symbol_data.get("ma200")
        ma200_str = f"${ma200:,.4f}" if ma200 is not None else "N/A"

        ema50 = symbol_data.get("ema50")
        ema50_str = f"${ema50:,.4f}" if ema50 is not None else "N/A"

        ema200 = symbol_data.get("ema200")
        ema200_str = f"${ema200:,.4f}" if ema200 is not None else "N/A"

        timestamp = symbol_data.get("timestamp", "Unknown")

        # Build last 7 days range lines
        ranges_lines = []
        ranges_7d = symbol_data.get("daily_ranges_7d", [])
        if ranges_7d:
            ranges_lines.append(
                "Last 7 Daily Ranges (Date | High | Low | Range | Range %):"
            )
            for r in ranges_7d:
                high_str = f"${r['high']:,.4f}" if r.get("high") is not None else "N/A"
                low_str = f"${r['low']:,.4f}" if r.get("low") is not None else "N/A"
                rng_val = r.get("range")
                rng_pct_val = r.get("range_pct")
                rng_str = f"${rng_val:,.4f}" if rng_val is not None else "N/A"
                rng_pct_str = (
                    f"{rng_pct_val:.2f}%" if rng_pct_val is not None else "N/A"
                )
                ranges_lines.append(
                    f"- {r.get('date', '')}: {high_str} | {low_str} | {rng_str} | {rng_pct_str}"
                )
        else:
            ranges_lines.append("No recent daily range data available")

        ranges_block = "\n".join(ranges_lines)

        prompt_data = f"""
CURRENT MARKET SNAPSHOT ({symbol_data.get("symbol", "Unknown")}):
- Current Price: {price_str}
- Daily RSI: {daily_rsi_str}
- Hourly RSI: {hourly_rsi_str}
- 15-minute RSI: {fifteen_min_rsi_str}
- MA50: {ma50_str}
- MA200: {ma200_str}
- EMA50: {ema50_str}
- EMA200: {ema200_str}
- Data timestamp: {timestamp}
- Daily ranges: {ranges_block}
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
