"""
Module for generating current data tables with latest indicators for crypto symbols.
This module can be easily extended to add more indicators in the future.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from infra.telegram_logging_handler import app_logger
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


def get_latest_price_from_candles(
    candles_df: pd.DataFrame | None,
) -> float | None:
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


def get_latest_rsi_from_df(rsi_df: pd.DataFrame | None) -> float | None:
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


def get_current_data_for_symbol(symbol: Symbol, conn) -> dict[str, Any]:  # noqa: PLR0915
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
            ma_df = fetch_moving_averages_for_symbol(conn, symbol.symbol_id, lookback_days=1)
            latest_ma = ma_df.iloc[-1]
            data["ma50"] = float(latest_ma["MA50"]) if pd.notna(latest_ma.get("MA50")) else None
            data["ma200"] = float(latest_ma["MA200"]) if pd.notna(latest_ma.get("MA200")) else None
            data["ema50"] = float(latest_ma["EMA50"]) if pd.notna(latest_ma.get("EMA50")) else None
            data["ema200"] = (
                float(latest_ma["EMA200"]) if pd.notna(latest_ma.get("EMA200")) else None
            )
        except Exception as ma_error:
            app_logger.warning(
                f"Could not fetch moving averages for {symbol.symbol_name}: {ma_error}"
            )

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
                            }
                        )
                    except Exception:
                        continue
                data["daily_ranges_7d"] = ranges
        except Exception as inner_e:
            app_logger.warning(f"Could not compute daily range for {symbol.symbol_name}: {inner_e}")

        # Fetch derivatives data (Open Interest and Funding Rate) - only for Binance symbols
        if symbol.source_id == SourceID.BINANCE:
            try:
                oi_repo = OpenInterestRepository(conn)
                fr_repo = FundingRateRepository(conn)

                # Get latest Open Interest
                oi_data = oi_repo.get_latest_open_interest(symbol.symbol_id)
                if oi_data:
                    data["open_interest"] = float(oi_data["open_interest"])
                    data["open_interest_value"] = float(oi_data["open_interest_value"])

                # Get latest Funding Rate
                fr_data = fr_repo.get_latest_funding_rate(symbol.symbol_id)
                if fr_data:
                    data["funding_rate"] = float(fr_data["funding_rate"])
                    if fr_data.get("funding_time"):
                        data["next_funding_time"] = fr_data["funding_time"]

            except Exception as deriv_error:
                app_logger.warning(
                    f"Could not fetch derivatives data for {symbol.symbol_name}: {deriv_error}"
                )

        app_logger.info(f"Successfully retrieved current data for {symbol.symbol_name}")

    except Exception as e:
        app_logger.error(f"Error getting current data for {symbol.symbol_name}: {e!s}")

    return data


def format_current_data_for_telegram_html(symbol_data: dict[str, Any]) -> str:  # noqa: PLR0915
    """
    Format current data for a single symbol into HTML for Telegram.

    Args:
        symbol_data: Dictionary containing current data for the symbol

    Returns:
        HTML formatted string for Telegram
    """
    symbol_name = symbol_data.get("symbol", "Unknown")
    timestamp = symbol_data.get("timestamp", "Unknown")

    # Format price
    latest_price = symbol_data.get("latest_price")
    price_str = f"${latest_price:,.4f}" if latest_price is not None else "N/A"

    # Format RSI values with emojis
    def format_rsi_with_emoji(rsi_value):
        RSI_OVERBOUGHT_THRESHOLD = 70
        RSI_OVERSOLD_THRESHOLD = 30
        if rsi_value is None:
            return "N/A"
        rsi_str = f"{rsi_value:.2f}"
        if rsi_value >= RSI_OVERBOUGHT_THRESHOLD:
            return f"🔴 {rsi_str} (Overbought)"
        if rsi_value <= RSI_OVERSOLD_THRESHOLD:
            return f"🟢 {rsi_str} (Oversold)"
        return f"🟡 {rsi_str}"

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
    history_html = ""
    if ranges_7d:
        history_html = "\n<b>📊 Last 7 Days Price Ranges:</b>\n<pre>"
        for day_data in ranges_7d:
            date_str = day_data.get("date", "N/A")
            day_range = day_data.get("range", 0)
            day_range_pct = day_data.get("range_pct", 0)
            day_range_str = f"${day_range:,.4f}" if day_range is not None else "N/A"
            day_range_pct_str = f"{day_range_pct:.2f}%" if day_range_pct is not None else "N/A"
            history_html += f"{date_str}: {day_range_str} ({day_range_pct_str})\n"
        history_html += "</pre>"

    # Format derivatives data (Open Interest and Funding Rate)
    derivatives_html = ""
    open_interest = symbol_data.get("open_interest")
    open_interest_value = symbol_data.get("open_interest_value")
    funding_rate = symbol_data.get("funding_rate")
    next_funding_time = symbol_data.get("next_funding_time")

    if any([open_interest, funding_rate]):
        derivatives_html = "\n<b>📈 Derivatives Data:</b>\n"

        if open_interest is not None:
            oi_str = f"{open_interest:,.0f}"
            derivatives_html += f"├ Open Interest: <code>{oi_str}</code>\n"

        if open_interest_value is not None:
            oi_value_str = f"${open_interest_value:,.0f}"
            derivatives_html += f"├ OI Value: <code>{oi_value_str}</code>\n"

        FUNDING_RATE_HIGH_THRESHOLD = 0.01
        FUNDING_RATE_LOW_THRESHOLD = -0.01
        if funding_rate is not None:
            fr_pct = funding_rate * 100
            fr_str = f"{fr_pct:+.4f}%"
            emoji = (
                "🔴"
                if funding_rate > FUNDING_RATE_HIGH_THRESHOLD
                else "🟢"
                if funding_rate < FUNDING_RATE_LOW_THRESHOLD
                else "🟡"
            )
            derivatives_html += f"├ Funding Rate: {emoji} <code>{fr_str}</code>\n"

        if next_funding_time:
            if isinstance(next_funding_time, datetime):
                funding_time_str = next_funding_time.strftime("%H:%M UTC")
            else:
                funding_time_str = str(next_funding_time)
            derivatives_html += f"└ Next Funding: <code>{funding_time_str}</code>\n"
        elif funding_rate is not None:
            # Add a closing character if we have funding rate but no time
            derivatives_html = derivatives_html.replace("├ Funding Rate:", "└ Funding Rate:")

    # Create HTML formatted message
    return f"""<b>📈 Current Market Data for {symbol_name}</b>

<i>⏰ {timestamp}</i>

<b>💰 Price Information:</b>
├ Latest Price: <code>{price_str}</code>
├ Daily High: <code>{high_str}</code>
├ Daily Low: <code>{low_str}</code>
└ Daily Range: <code>{range_str}</code>

<b>📊 RSI Indicators:</b>
├ Daily RSI: {daily_rsi_str}
├ Hourly RSI: {hourly_rsi_str}
└ 15-min RSI: {fifteen_min_rsi_str}

<b>📉 Moving Averages:</b>
├ MA50: <code>{ma50_str}</code>
├ MA200: <code>{ma200_str}</code>
├ EMA50: <code>{ema50_str}</code>
└ EMA200: <code>{ema200_str}</code>
{derivatives_html}{history_html}
"""


def get_current_data_summary_table(symbol: Symbol, conn) -> str:
    """
    Generate a summary table of current data for a symbol in HTML format for Telegram.

    Args:
        symbol: Symbol object
        conn: Database connection

    Returns:
        HTML formatted table with current data for Telegram
    """
    try:
        # Get current data
        symbol_data = get_current_data_for_symbol(symbol, conn)

        # Format as HTML
        return format_current_data_for_telegram_html(symbol_data)

    except Exception as e:
        app_logger.error(f"Error generating current data summary for {symbol.symbol_name}: {e!s}")
        return f"<b>Error:</b> Unable to generate summary for {symbol.symbol_name}"


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
        app_logger.error(f"Error generating AI prompt data for {symbol.symbol_name}: {e!s}")
        return f"CURRENT MARKET SNAPSHOT: Error retrieving data for {symbol.symbol_name}"


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
