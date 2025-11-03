"""Module for generating current data tables with latest indicators for crypto symbols.

This module can be easily extended to add more indicators in the future.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pandas as pd

from infra.telegram_logging_handler import app_logger
from shared_code.telegram import (
    TelegramFormatter,
    format_funding_rate_with_emoji,
    format_rsi_with_emoji,
    get_formatter,
)
from source_repository import SourceID, Symbol
from technical_analysis.reports.rsi_multi_timeframe import get_rsi_for_symbol_timeframe
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.funding_rate_repository import (
    FundingRateRepository,
)
from technical_analysis.repositories.moving_averages_repository import (
    fetch_moving_averages_for_symbol,
)
from technical_analysis.repositories.open_interest_repository import (
    OpenInterestRepository,
)


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


def get_latest_price_from_candles(
    candles_df: pd.DataFrame | None,
) -> float | None:
    """Extract the latest price from candles DataFrame.

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


def get_latest_rsi_from_df(rsi_df: pd.DataFrame | None) -> float | None:
    """Extract the latest RSI value from RSI DataFrame.

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
        app_logger.debug("Could not extract latest RSI value from dataframe")

    return None


def _extract_latest_price(
    daily_rsi_df: pd.DataFrame | None,
    hourly_rsi_df: pd.DataFrame | None,
    fifteen_min_rsi_df: pd.DataFrame | None,
) -> float | None:
    """Extract latest price from RSI dataframes, preferring higher timeframes."""
    if fifteen_min_rsi_df is not None and not fifteen_min_rsi_df.empty:
        return get_latest_price_from_candles(fifteen_min_rsi_df)
    if hourly_rsi_df is not None and not hourly_rsi_df.empty:
        return get_latest_price_from_candles(hourly_rsi_df)
    if daily_rsi_df is not None and not daily_rsi_df.empty:
        return get_latest_price_from_candles(daily_rsi_df)
    return None


def _extract_moving_averages(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    symbol_id: int,
) -> dict[str, float | None]:
    """Extract latest moving averages for a symbol."""
    ma_data: dict[str, float | None] = {"ma50": None, "ma200": None, "ema50": None, "ema200": None}
    try:
        ma_df = fetch_moving_averages_for_symbol(conn, symbol_id, lookback_days=1)
        if not ma_df.empty:
            latest_ma = ma_df.iloc[-1]
            ma_data["ma50"] = float(latest_ma["MA50"]) if pd.notna(latest_ma.get("MA50")) else None
            ma_data["ma200"] = (
                float(latest_ma["MA200"]) if pd.notna(latest_ma.get("MA200")) else None
            )
            ma_data["ema50"] = (
                float(latest_ma["EMA50"]) if pd.notna(latest_ma.get("EMA50")) else None
            )
            ma_data["ema200"] = (
                float(latest_ma["EMA200"]) if pd.notna(latest_ma.get("EMA200")) else None
            )
    except (KeyError, ValueError, TypeError, IndexError) as ma_error:
        app_logger.warning(f"Could not fetch moving averages for symbol_id {symbol_id}: {ma_error}")
    return ma_data


def get_current_data_for_symbol(  # noqa: PLR0915, PLR0912
    symbol: Symbol,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> dict[str, Any]:
    """Get current data for a single symbol including latest price and RSI across timeframes.

    Args:
        symbol: Symbol object
        conn: Database connection

    Returns:
        Dictionary containing current data for the symbol

    """
    if conn is None:
        return {
            "symbol": symbol.symbol_name,
            "latest_price": None,
            "daily_rsi": None,
            "hourly_rsi": None,
            "fifteen_min_rsi": None,
            "ma50": None,
            "ma200": None,
            "ema50": None,
            "ema200": None,
            "daily_high": None,
            "daily_low": None,
            "daily_range": None,
            "daily_range_pct": None,
            "daily_ranges_7d": [],
            "open_interest": None,
            "open_interest_value": None,
            "funding_rate": None,
            "next_funding_time": None,
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    data: dict[str, Any] = {
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
        # Derivatives data
        "open_interest": None,
        "open_interest_value": None,
        "funding_rate": None,
        "next_funding_time": None,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        # Get RSI data for different timeframes
        daily_rsi_df = get_rsi_for_symbol_timeframe(symbol, conn, "daily", lookback_days=7)
        hourly_rsi_df = get_rsi_for_symbol_timeframe(symbol, conn, "hourly", lookback_days=2)
        fifteen_min_rsi_df = get_rsi_for_symbol_timeframe(
            symbol,
            conn,
            "fifteen_min",
            lookback_days=1,
        )

        # Extract latest price (prefer 15min, then hourly, then daily)
        data["latest_price"] = _extract_latest_price(
            daily_rsi_df,
            hourly_rsi_df,
            fifteen_min_rsi_df,
        )

        # Extract RSI values for each timeframe
        data["daily_rsi"] = get_latest_rsi_from_df(daily_rsi_df)
        data["hourly_rsi"] = get_latest_rsi_from_df(hourly_rsi_df)
        data["fifteen_min_rsi"] = get_latest_rsi_from_df(fifteen_min_rsi_df)

        # Fetch moving averages data (latest values)
        ma_data = _extract_moving_averages(conn, symbol.symbol_id)
        data.update(ma_data)

        # Fetch daily candles (look back 7 days) to compute daily range and recent history
        try:
            daily_repo = DailyCandleRepository(conn)
            now_utc = datetime.now(UTC)
            start = now_utc - timedelta(days=7)
            candles = daily_repo.get_candles(symbol, start, now_utc)
            if candles:
                # Latest candle for headline metrics
                last_candle = candles[-1]
                high = float(last_candle.high)
                low = float(last_candle.low)
                if low > 0:
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
                    date_str = "unknown"  # Initialize in case of early exception
                    try:
                        c_high = float(c.high)
                        c_low = float(c.low)

                        # Parse end_date string to datetime for formatting
                        if isinstance(c.end_date, str):
                            date_str = c.end_date.split("T")[0]  # Extract date part
                        else:
                            date_str = c.end_date.strftime("%Y-%m-%d")

                        if c_low > 0:
                            c_range = c_high - c_low
                            c_range_pct = (c_range / c_low) * 100.0
                        else:
                            c_range = None
                            c_range_pct = None
                        ranges.append(
                            {
                                "date": date_str,
                                "high": c_high,
                                "low": c_low,
                                "range": c_range,
                                "range_pct": c_range_pct,
                            },
                        )
                    except (ValueError, TypeError, AttributeError) as e:
                        app_logger.warning(
                            "Could not compute daily range for date %s: %s",
                            date_str,
                            e,
                        )
                        continue
                data["daily_ranges_7d"] = ranges
        except (KeyError, ValueError, TypeError, IndexError) as inner_e:
            app_logger.warning(f"Could not compute daily range for {symbol.symbol_name}: {inner_e}")

        # Fetch derivatives data (Open Interest and Funding Rate) - only for Binance symbols
        if symbol.source_id == SourceID.BINANCE:
            try:
                oi_repo = OpenInterestRepository(conn)
                fr_repo = FundingRateRepository(conn)

                # Get latest Open Interest
                oi_data = oi_repo.get_latest_open_interest(symbol.symbol_id)
                if oi_data:
                    oi_val = oi_data.get("open_interest")
                    oi_val_value = oi_data.get("open_interest_value")
                    if oi_val is not None and not isinstance(oi_val, datetime):
                        data["open_interest"] = float(oi_val)
                    if oi_val_value is not None and not isinstance(oi_val_value, datetime):
                        data["open_interest_value"] = float(oi_val_value)

                # Get latest Funding Rate
                fr_data = fr_repo.get_latest_funding_rate(symbol.symbol_id)
                if fr_data:
                    fr_val = fr_data.get("funding_rate")
                    if fr_val is not None and not isinstance(fr_val, datetime):
                        data["funding_rate"] = float(fr_val)
                    if fr_data.get("funding_time"):
                        data["next_funding_time"] = fr_data["funding_time"]

            except (KeyError, ValueError, TypeError) as deriv_error:
                app_logger.warning(
                    f"Could not fetch derivatives data for {symbol.symbol_name}: {deriv_error}",
                )

        app_logger.info(f"Successfully retrieved current data for {symbol.symbol_name}")

    except (KeyError, ValueError, TypeError, AttributeError) as e:
        app_logger.error(f"Error getting current data for {symbol.symbol_name}: {e!s}")

    return data


def format_current_data_for_telegram(  # noqa: PLR0915
    symbol_data: dict[str, Any],
    formatter: TelegramFormatter | None = None,
) -> str:
    """Format current data for a single symbol for Telegram.

    Args:
        symbol_data: Dictionary containing current data for the symbol
        formatter: TelegramFormatter instance (HTML or MarkdownV2).
            Defaults to HTML if not provided.

    Returns:
        Formatted string for Telegram (HTML or MarkdownV2 depending on formatter)

    """
    # Use HTML formatter by default if none provided
    if formatter is None:
        formatter = get_formatter("HTML")

    symbol_name = symbol_data.get("symbol", "Unknown")
    timestamp = symbol_data.get("timestamp", "Unknown")

    # Format price
    latest_price = symbol_data.get("latest_price")
    price_str = f"${latest_price:,.4f}" if latest_price is not None else "N/A"

    # Format RSI values with emojis using imported function
    daily_rsi = symbol_data.get("daily_rsi")
    hourly_rsi = symbol_data.get("hourly_rsi")
    fifteen_min_rsi = symbol_data.get("fifteen_min_rsi")

    daily_rsi_str = format_rsi_with_emoji(daily_rsi)
    hourly_rsi_str = format_rsi_with_emoji(hourly_rsi)
    fifteen_min_rsi_str = format_rsi_with_emoji(fifteen_min_rsi)

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
        high_str, low_str = "N/A", "N/A"

    if daily_range is not None and daily_range_pct is not None:
        range_str = f"${daily_range:,.4f} ({daily_range_pct:.2f}%)"
    else:
        range_str = "N/A"

    # Last 7 days ranges
    ranges_7d = symbol_data.get("daily_ranges_7d", [])
    history_section = ""
    if ranges_7d:
        history_section = "\n" + formatter.format_bold("📊 Last 7 Days Price Ranges:") + "\n"
        history_section += formatter.format_code_block(
            "\n".join(
                f"{day_data.get('date', 'N/A')}: "
                f"${day_data.get('range', 0):,.4f} "
                f"({day_data.get('range_pct', 0):.2f}%)"
                for day_data in ranges_7d
            ),
        )

    # Format derivatives data (Open Interest and Funding Rate)
    derivatives_section = ""
    open_interest = symbol_data.get("open_interest")
    open_interest_value = symbol_data.get("open_interest_value")
    funding_rate = symbol_data.get("funding_rate")
    next_funding_time = symbol_data.get("next_funding_time")

    if any([open_interest, funding_rate]):
        derivatives_section = "\n" + formatter.format_bold("📈 Derivatives Data:") + "\n"

        if open_interest is not None:
            oi_str = f"{open_interest:,.0f}"
            derivatives_section += f"├ Open Interest: {formatter.format_code(oi_str)}\n"

        if open_interest_value is not None:
            oi_value_str = f"${open_interest_value:,.0f}"
            derivatives_section += f"├ OI Value: {formatter.format_code(oi_value_str)}\n"

        if funding_rate is not None:
            funding_formatted = format_funding_rate_with_emoji(funding_rate)
            derivatives_section += f"├ Funding Rate: {funding_formatted}\n"

        if next_funding_time:
            if isinstance(next_funding_time, datetime):
                funding_time_str = next_funding_time.strftime("%H:%M UTC")
            else:
                funding_time_str = str(next_funding_time)
            derivatives_section += f"└ Next Funding: {formatter.format_code(funding_time_str)}\n"
        elif funding_rate is not None:
            # Add a closing character if we have funding rate but no time
            derivatives_section = derivatives_section.replace("├ Funding Rate:", "└ Funding Rate:")

    # Create formatted message using formatter
    return f"""{formatter.format_bold(f"📈 Current Market Data for {symbol_name}")}

{formatter.format_italic(f"⏰ {timestamp}")}

{formatter.format_bold("💰 Price Information:")}
├ Latest Price: {formatter.format_code(price_str)}
├ Daily High: {formatter.format_code(high_str)}
├ Daily Low: {formatter.format_code(low_str)}
└ Daily Range: {formatter.format_code(range_str)}

{formatter.format_bold("📊 RSI Indicators:")}
├ Daily RSI: {daily_rsi_str}
├ Hourly RSI: {hourly_rsi_str}
└ 15-min RSI: {fifteen_min_rsi_str}

{formatter.format_bold("📉 Moving Averages:")}
├ MA50: {formatter.format_code(ma50_str)}
├ MA200: {formatter.format_code(ma200_str)}
├ EMA50: {formatter.format_code(ema50_str)}
└ EMA200: {formatter.format_code(ema200_str)}
{derivatives_section}{history_section}
"""


# Backward compatibility - old function name (deprecated)
def format_current_data_for_telegram_html(symbol_data: dict[str, Any]) -> str:
    """Format current data for Telegram in HTML format.

    .. deprecated::
        Use :func:`format_current_data_for_telegram` with formatter parameter instead.

    Args:
        symbol_data: Dictionary containing current data for the symbol

    Returns:
        HTML formatted string for Telegram

    """
    return format_current_data_for_telegram(symbol_data, formatter=get_formatter("HTML"))


def get_current_data_summary_table(
    symbol: Symbol,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> str:
    """Generate a summary table of current data for a symbol in HTML format for Telegram.

    Args:
        symbol: Symbol object
        conn: Database connection

    Returns:
        HTML formatted table with current data for Telegram

    """
    try:
        # Get current data
        symbol_data = get_current_data_for_symbol(symbol, conn)

        # Format for Telegram (defaults to HTML formatter)
        return format_current_data_for_telegram(symbol_data)

    except (KeyError, ValueError, TypeError) as e:
        app_logger.error(f"Error generating current data summary for {symbol.symbol_name}: {e!s}")
        return f"<b>Error:</b> Unable to generate summary for {symbol.symbol_name}"


def get_current_data_for_ai_prompt(
    symbol: Symbol,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> str:
    """Generate current data in a format suitable for AI prompts.

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
        fifteen_min_rsi_str = f"{fifteen_min_rsi:.2f}" if fifteen_min_rsi is not None else "N/A"

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
            ranges_lines.append("Last 7 Daily Ranges (Date | High | Low | Range | Range %):")
            for r in ranges_7d:
                high_str = f"${r['high']:,.4f}" if r.get("high") is not None else "N/A"
                low_str = f"${r['low']:,.4f}" if r.get("low") is not None else "N/A"
                rng_val = r.get("range")
                rng_pct_val = r.get("range_pct")
                rng_str = f"${rng_val:,.4f}" if rng_val is not None else "N/A"
                rng_pct_str = f"{rng_pct_val:.2f}%" if rng_pct_val is not None else "N/A"
                ranges_lines.append(
                    f"- {r.get('date', '')}: {high_str} | {low_str} | {rng_str} | {rng_pct_str}",
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

    except (KeyError, ValueError, TypeError) as e:
        app_logger.error(f"Error generating AI prompt data for {symbol.symbol_name}: {e!s}")
        return f"CURRENT MARKET SNAPSHOT: Error retrieving data for {symbol.symbol_name}"


# Future extension functions can be added here:
#
# def add_moving_averages_to_data(symbol_data: Dict[str, Any],
#                                  symbol: Symbol, conn) -> Dict[str, Any]:
#     """Add moving averages data to symbol data dictionary."""
#     pass
#
# def add_volume_data_to_data(symbol_data: Dict[str, Any], symbol: Symbol, conn) -> Dict[str, Any]:
#     """Add volume indicators to symbol data dictionary."""
#     pass
#
# def add_momentum_indicators_to_data(symbol_data: Dict[str, Any],
#                                     symbol: Symbol, conn) -> Dict[str, Any]:
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
        pass
    else:
        pass
