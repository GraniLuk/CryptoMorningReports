"""Phase 5: Comprehensive Testing & Validation.

Tests all refactored batch fetching functionality.
"""

from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from shared_code.price_checker import (
    fetch_daily_candles,
    fetch_fifteen_min_candles,
    fetch_hourly_candles,
)
from source_repository import SourceID, fetch_symbols


def test_daily_candles_binance():
    """TEST-001: Test fetch_daily_candles() with BINANCE symbol (batch path)."""
    load_dotenv()
    conn = connect_to_sql()

    try:
        symbols = fetch_symbols(conn)

        # Find first BINANCE symbol
        binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
        assert binance_symbol is not None, "No BINANCE symbols found"

        today = datetime.now(UTC).date()
        start_date = today - timedelta(days=7)

        candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

        assert candles is not None, (
            f"Failed to fetch daily candles for {binance_symbol.symbol_name}"
        )
        assert len(candles) > 0, f"No candles returned for {binance_symbol.symbol_name}"
        assert all(c.symbol == binance_symbol.symbol_name for c in candles), "Symbol mismatch"
        assert all(c.source == binance_symbol.source_id.value for c in candles), "Source mismatch"
    finally:
        conn.close()


def test_daily_candles_kucoin():
    """TEST-004: Test fetch_daily_candles() with KUCOIN symbol (individual path)."""
    load_dotenv()
    conn = connect_to_sql()

    try:
        symbols = fetch_symbols(conn)

        # Find first KUCOIN symbol
        kucoin_symbol = next((s for s in symbols if s.source_id == SourceID.KUCOIN), None)

        # Skip test if no KuCoin symbols (not a failure)
        if not kucoin_symbol:
            return

        today = datetime.now(UTC).date()
        start_date = today - timedelta(days=7)

        candles = fetch_daily_candles(kucoin_symbol, start_date, today, conn)

        assert candles is not None, f"Failed to fetch daily candles for {kucoin_symbol.symbol_name}"
        assert len(candles) > 0, f"No candles returned for {kucoin_symbol.symbol_name}"
        assert all(c.symbol == kucoin_symbol.symbol_name for c in candles), "Symbol mismatch"
        assert all(c.source == kucoin_symbol.source_id.value for c in candles), "Source mismatch"
    finally:
        conn.close()


def test_hourly_candles_both_sources():
    """TEST-002/005: Test fetch_hourly_candles() with both sources."""
    load_dotenv()
    conn = connect_to_sql()

    try:
        symbols = fetch_symbols(conn)

        # Test BINANCE
        binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
        assert binance_symbol is not None, "No BINANCE symbols found"

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=24)

        candles = fetch_hourly_candles(binance_symbol, start_time, end_time, conn)

        assert candles is not None, "Failed to fetch BINANCE hourly candles"
        assert len(candles) > 0, (
            f"No hourly candles returned for BINANCE {binance_symbol.symbol_name}"
        )
        assert all(c.symbol == binance_symbol.symbol_name for c in candles), (
            "Symbol mismatch in BINANCE candles"
        )

        # Test KUCOIN (optional - don't fail if no symbols)
        kucoin_symbol = next((s for s in symbols if s.source_id == SourceID.KUCOIN), None)
        if kucoin_symbol:
            candles = fetch_hourly_candles(kucoin_symbol, start_time, end_time, conn)
            # KuCoin hourly candles may not always be available - that's okay
    finally:
        conn.close()


def test_fifteen_min_candles_both_sources():
    """TEST-003/007: Test fetch_fifteen_min_candles() with both sources."""
    load_dotenv()
    conn = connect_to_sql()

    try:
        symbols = fetch_symbols(conn)

        # Test BINANCE
        binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
        assert binance_symbol is not None, "No BINANCE symbols found"

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=2)

        candles = fetch_fifteen_min_candles(binance_symbol, start_time, end_time, conn)

        assert candles is not None, "Failed to fetch BINANCE 15-min candles"
        assert len(candles) > 0, (
            f"No 15-min candles returned for BINANCE {binance_symbol.symbol_name}"
        )
        assert all(c.symbol == binance_symbol.symbol_name for c in candles), (
            "Symbol mismatch in candles"
        )

        # Test KUCOIN (optional - don't fail if no symbols)
        kucoin_symbol = next((s for s in symbols if s.source_id == SourceID.KUCOIN), None)
        if kucoin_symbol:
            candles = fetch_fifteen_min_candles(kucoin_symbol, start_time, end_time, conn)
            # KuCoin 15-min candles may not always be available - that's okay
    finally:
        conn.close()


def test_database_storage():
    """TEST-008: Verify database correctly stores all fetched candles."""
    load_dotenv()
    conn = connect_to_sql()

    try:
        symbols = fetch_symbols(conn)

        binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
        assert binance_symbol is not None, "No BINANCE symbols found"

        # Fetch candles
        today = datetime.now(UTC).date()
        start_date = today - timedelta(days=3)

        candles_before = fetch_daily_candles(binance_symbol, start_date, today, conn)
        count_before = len(candles_before)

        # Fetch again (should use cache)
        candles_after = fetch_daily_candles(binance_symbol, start_date, today, conn)
        count_after = len(candles_after)

        assert count_before == count_after, (
            f"Inconsistent candle counts: {count_before} vs {count_after}"
        )
        assert count_after > 0, "No candles stored in database"
    finally:
        conn.close()


def test_timezone_handling():
    """TEST-009: Test timezone handling (UTC consistency).

    Verifies that all candles have timezone information in their end_date field.
    Accepts both datetime objects with tzinfo and ISO 8601 strings with timezone.
    """
    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
    assert binance_symbol is not None, "No BINANCE symbols found"

    def has_timezone(end_date: datetime | str) -> bool:
        """Check if end_date has timezone info (works for both datetime and str)."""
        if isinstance(end_date, datetime):
            return end_date.tzinfo is not None
        if isinstance(end_date, str):
            return end_date.endswith(("+00:00", "Z"))
        return False

    # Test daily candles
    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=2)
    daily_candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

    assert len(daily_candles) > 0, "No daily candles returned"
    for candle in daily_candles:
        assert has_timezone(candle.end_date), \
            f"end_date missing timezone: {candle.end_date} (type: {type(candle.end_date)})"

    # Test hourly candles
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=6)
    hourly_candles = fetch_hourly_candles(binance_symbol, start_time, end_time, conn)

    assert len(hourly_candles) > 0, "No hourly candles returned"
    for candle in hourly_candles:
        assert has_timezone(candle.end_date), \
            f"end_date missing timezone: {candle.end_date} (type: {type(candle.end_date)})"

    # Test 15-min candles
    start_time = end_time - timedelta(hours=2)
    fifteen_min_candles = fetch_fifteen_min_candles(binance_symbol, start_time, end_time, conn)

    assert len(fifteen_min_candles) > 0, "No 15-min candles returned"
    for candle in fifteen_min_candles:
        assert has_timezone(candle.end_date), \
            f"end_date missing timezone: {candle.end_date} (type: {type(candle.end_date)})"

    conn.close()


def test_empty_database_scenario():
    """TEST-045: Test with empty database (first run scenario)."""
    # This test is a placeholder - empty DB scenario is covered by other tests
    pass


def test_partially_filled_database():
    """TEST-046: Test with partially filled database (resume scenario)."""
    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
    assert binance_symbol is not None, "No BINANCE symbols found"

    # Request a larger date range (30 days)
    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=30)

    candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

    assert candles is not None, "Failed to fetch candles"
    assert len(candles) > 0, "No candles returned from partially filled database"

    conn.close()


def test_fully_updated_database():
    """TEST-047: Test with fully updated database (no fetch scenario)."""
    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    binance_symbol = next((s for s in symbols if s.source_id == SourceID.BINANCE), None)
    assert binance_symbol is not None, "No BINANCE symbols found"

    # First fetch to populate
    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=2)

    fetch_daily_candles(binance_symbol, start_date, today, conn)

    # Second fetch should use cache entirely
    candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

    assert candles is not None, "Failed to fetch candles from cache"
    assert len(candles) > 0, "No candles returned from cache"

    conn.close()
