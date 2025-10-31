"""Update latest daily candles to ensure fresh data for technical analysis.

This module ensures that daily reports use the most recent market data.
"""

import logging
import sys
from datetime import UTC, date, datetime, timedelta

from infra.sql_connection import connect_to_sql
from shared_code.price_checker import fetch_daily_candle, fetch_hourly_candle
from source_repository import fetch_symbols


logger = logging.getLogger(__name__)


def get_last_candle_date(conn, symbol):
    """Get the most recent date in DailyCandles table for a specific symbol.

    Args:
        conn: Database connection
        symbol: Symbol object with symbol_id

    Returns:
        date object of the last candle, or None if no candles exist

    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT MAX(Date) as LastDate
        FROM DailyCandles
        WHERE SymbolId = ?
        """,
        (symbol.symbol_id,),
    )
    result = cursor.fetchone()

    if result and result[0]:
        last_date = result[0]
        # If it's already a date object, return it; otherwise parse from string
        if isinstance(last_date, date):
            return last_date
        return date.fromisoformat(last_date)

    return None


def update_latest_daily_candles(conn, days_to_update=3):
    """Update missing daily candles for all symbols up to today.

    Intelligently fetches only missing data:
    - Checks database for last available date per symbol
    - Fetches only missing dates between last_date and today
    - If no data exists, falls back to fetching last N days

    This ensures that:
    1. Yesterday's candle has the final close price (not intraday)
    2. Today's candle exists (even if incomplete)
    3. Technical indicators reflect current market conditions
    4. No unnecessary API calls for data we already have

    Args:
        conn: Database connection
        days_to_update: Fallback - days to fetch if no data exists (default 3)

    """
    logger.info("Checking database for missing daily candles...")

    symbols = fetch_symbols(conn)
    today = datetime.now(UTC).date()

    total_updated = 0
    total_failed = 0
    total_skipped = 0

    for symbol in symbols:
        symbol_updated = 0

        # Check last available date in database
        last_date = get_last_candle_date(conn, symbol)

        if last_date:
            # We have data - only fetch missing dates
            if last_date >= today:
                logger.info(f"✓ {symbol.symbol_name}: Already up-to-date (last: {last_date})")
                total_skipped += 1
                continue

            # Start from day after last available date
            start_date = last_date + timedelta(days=1)
            logger.info(
                f"📅 {symbol.symbol_name}: Fetching from {start_date} to {today} "
                f"(last in DB: {last_date})"
            )
        else:
            # No data exists - fetch last N days as fallback
            start_date = today - timedelta(days=days_to_update - 1)
            logger.info(
                f"📅 {symbol.symbol_name}: No existing data, fetching last {days_to_update} days"
            )

        # Fetch missing dates
        current_date = start_date
        while current_date <= today:
            try:
                # Fetch fresh candle data from Binance
                candle = fetch_daily_candle(symbol, current_date, conn)

                if candle:
                    symbol_updated += 1
                    logger.debug(f"  ✓ {current_date}: Close={candle.close:.2f}")
                else:
                    logger.debug(f"  ⊘ {current_date}: No data available")

            except Exception as e:
                logger.error(f"  ✗ {current_date}: Failed - {e}")
                total_failed += 1

            current_date += timedelta(days=1)

        if symbol_updated > 0:
            total_updated += symbol_updated
            logger.info(f"✓ {symbol.symbol_name}: Updated {symbol_updated} day(s)")

    logger.info(
        f"Latest data update complete: {total_updated} candles updated, "
        f"{total_skipped} symbols already current, {total_failed} failed"
    )

    return total_updated, total_failed


def get_last_hourly_candle_time(conn, symbol):
    """Get the most recent timestamp in HourlyCandles table for a specific symbol.

    Args:
        conn: Database connection
        symbol: Symbol object with symbol_id

    Returns:
        datetime object of the last candle, or None if no candles exist

    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT MAX(OpenTime) as LastTime
        FROM HourlyCandles
        WHERE SymbolId = ?
        """,
        (symbol.symbol_id,),
    )
    result = cursor.fetchone()

    if result and result[0]:
        last_time = result[0]

        # If it's already a datetime object, ensure UTC timezone
        if isinstance(last_time, datetime):
            if last_time.tzinfo is None:
                return last_time.replace(tzinfo=UTC)
            return last_time

        # Otherwise parse from string
        last_time_str = last_time
        if "+" in last_time_str or "Z" in last_time_str:
            last_time = datetime.fromisoformat(last_time_str.replace("Z", "+00:00"))
        else:
            last_time = datetime.fromisoformat(last_time_str).replace(tzinfo=UTC)
        return last_time

    return None


def update_latest_hourly_candles(conn, hours_to_update=24):
    """Update missing hourly candles for all symbols up to current hour.

    Intelligently fetches only missing data:
    - Checks database for last available hour per symbol
    - Fetches only missing hours between last_hour and now
    - If no data exists, falls back to fetching last N hours

    Args:
        conn: Database connection
        hours_to_update: Fallback - hours to fetch if no data exists (default 24)

    """
    logger.info("Checking database for missing hourly candles...")

    symbols = fetch_symbols(conn)
    end_time = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    total_updated = 0
    total_failed = 0
    total_skipped = 0

    for symbol in symbols:
        symbol_updated = 0

        # Check last available hour in database
        last_time = get_last_hourly_candle_time(conn, symbol)

        if last_time:
            # We have data - only fetch missing hours
            if last_time >= end_time:
                logger.info(
                    f"✓ {symbol.symbol_name}: Already up-to-date "
                    f"(last: {last_time.strftime('%Y-%m-%d %H:%M')})"
                )
                total_skipped += 1
                continue

            # Start from hour after last available
            start_time = last_time + timedelta(hours=1)
            hours_diff = int((end_time - start_time).total_seconds() / 3600) + 1
            logger.info(
                f"📅 {symbol.symbol_name}: Fetching {hours_diff} missing hour(s) "
                f"(last in DB: {last_time.strftime('%Y-%m-%d %H:%M')})"
            )
        else:
            # No data exists - fetch last N hours as fallback
            start_time = end_time - timedelta(hours=hours_to_update - 1)
            logger.info(
                f"📅 {symbol.symbol_name}: No existing data, fetching last {hours_to_update} hours"
            )

        # Fetch missing hours
        current_time = start_time
        while current_time <= end_time:
            try:
                candle = fetch_hourly_candle(symbol, current_time, conn)

                if candle:
                    symbol_updated += 1
                    logger.debug(
                        f"  ✓ {current_time.strftime('%Y-%m-%d %H:%M')}: Close={candle.close:.2f}"
                    )

            except Exception as e:
                logger.error(f"  ✗ {current_time.strftime('%Y-%m-%d %H:%M')}: Failed - {e}")
                total_failed += 1

            current_time += timedelta(hours=1)

        if symbol_updated > 0:
            total_updated += symbol_updated
            logger.info(f"✓ {symbol.symbol_name}: Updated {symbol_updated} hourly candle(s)")

    logger.info(
        f"Hourly data update complete: {total_updated} candles updated, "
        f"{total_skipped} symbols already current, {total_failed} failed"
    )

    return total_updated, total_failed


if __name__ == "__main__":
    """
    Run this script to manually update the latest candles.
    Intelligently fetches only missing data since last database update.

    Usage: python -m database.update_latest_data
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    from dotenv import load_dotenv

    load_dotenv()

    conn = connect_to_sql()

    if not conn:
        logger.error("Failed to connect to database")
        sys.exit(1)

    try:
        print("\n" + "=" * 70)
        print("📊 SMART DATA UPDATE - Fetching Only Missing Candles")
        print("=" * 70 + "\n")

        # Update daily candles (only missing since last update)
        daily_updated, daily_failed = update_latest_daily_candles(conn, days_to_update=3)

        print()  # Blank line between daily and hourly updates

        # Update hourly candles (only missing since last update)
        hourly_updated, hourly_failed = update_latest_hourly_candles(conn, hours_to_update=24)

        print("\n" + "=" * 70)
        print("📈 UPDATE SUMMARY")
        print("=" * 70)
        print(f"✓ Daily candles:  {daily_updated} updated, {daily_failed} failed")
        print(f"✓ Hourly candles: {hourly_updated} updated, {hourly_failed} failed")

        if daily_updated == 0 and hourly_updated == 0 and daily_failed == 0 and hourly_failed == 0:
            print("\n💡 All symbols already up-to-date - no API calls needed!")

        print("=" * 70 + "\n")

    finally:
        conn.close()
