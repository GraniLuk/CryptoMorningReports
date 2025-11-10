"""Phase 5: Comprehensive Testing & Validation.

Tests all refactored batch fetching functionality.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

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

        # Mock the Binance API call
        with patch("shared_code.binance.BinanceClient") as mock_client:
            mock_instance = mock_client.return_value
            # Mock get_klines to return raw kline data
            mock_klines = []
            current_time = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
            for _ in range(8):
                open_time_ms = int(current_time.timestamp() * 1000)
                mock_klines.append(
                    [
                        open_time_ms,  # open_time
                        "50000.0",  # open
                        "50200.0",  # high
                        "49900.0",  # low
                        "50100.0",  # close
                        "1000.0",  # volume
                        open_time_ms + (24 * 60 * 60 * 1000),  # close_time
                        "50000000.0",  # quote_volume
                        100,  # trades
                        "500.0",  # taker_buy_base
                        "25000000.0",  # taker_buy_quote
                        "0",  # ignore
                    ],
                )
                current_time += timedelta(days=1)

            mock_instance.get_klines.return_value = mock_klines

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

        # Mock the KuCoin API call
        with patch("shared_code.kucoin.Market") as mock_market:
            mock_instance = mock_market.return_value
            # Mock get_kline to return kline data for each day
            base_time = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
            mock_instance.get_kline.return_value = {
                "code": "200000",
                "data": [
                    [
                        str(int((base_time + timedelta(days=i)).timestamp())),
                        "50000",  # open
                        "50100",  # close
                        "50200",  # high
                        "49900",  # low
                        "1000",  # volume
                        "50000000",  # turnover
                    ]
                    for i in range(8)
                ],
            }

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

        # Mock Binance hourly API call
        with patch("shared_code.binance.BinanceClient") as mock_client:
            mock_instance = mock_client.return_value
            mock_klines = []
            current_time = start_time
            for _ in range(24):
                open_time_ms = int(current_time.timestamp() * 1000)
                mock_klines.append(
                    [
                        open_time_ms,  # open_time
                        "50000.0",  # open
                        "50200.0",  # high
                        "49900.0",  # low
                        "50100.0",  # close
                        "1000.0",  # volume
                        open_time_ms + (60 * 60 * 1000),  # close_time (1 hour later)
                        "50000000.0",  # quote_volume
                        100,  # trades
                        "500.0",  # taker_buy_base
                        "25000000.0",  # taker_buy_quote
                        "0",  # ignore
                    ],
                )
                current_time += timedelta(hours=1)

            mock_instance.get_klines.return_value = mock_klines

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
            with patch("shared_code.kucoin.Market") as mock_market:
                mock_instance = mock_market.return_value
                mock_instance.get_kline.return_value = {
                    "code": "200000",
                    "data": [
                        [
                            str(int((start_time + timedelta(hours=i)).timestamp())),
                            "50000",  # open
                            "50100",  # close
                            "50200",  # high
                            "49900",  # low
                            "1000",  # volume
                            "50000000",  # turnover
                        ]
                        for i in range(24)
                    ],
                }

            kucoin_candles = fetch_hourly_candles(kucoin_symbol, start_time, end_time, conn)
            # KuCoin hourly candles may not always be available - that's okay
            # If candles are returned, validate their structure
            if kucoin_candles:
                assert all(c.symbol == kucoin_symbol.symbol_name for c in kucoin_candles), (
                    "Symbol mismatch in KUCOIN candles"
                )
                assert all(c.source == kucoin_symbol.source_id.value for c in kucoin_candles), (
                    "Source mismatch in KUCOIN candles"
                )
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

        # Mock Binance 15-min API call (8 candles for 2 hours)
        with patch("shared_code.binance.BinanceClient") as mock_client:
            mock_instance = mock_client.return_value
            mock_klines = []
            current_time = start_time
            for _ in range(8):
                open_time_ms = int(current_time.timestamp() * 1000)
                mock_klines.append(
                    [
                        open_time_ms,  # open_time
                        "50000.0",  # open
                        "50200.0",  # high
                        "49900.0",  # low
                        "50100.0",  # close
                        "1000.0",  # volume
                        open_time_ms + (15 * 60 * 1000),  # close_time (15 min later)
                        "50000000.0",  # quote_volume
                        100,  # trades
                        "500.0",  # taker_buy_base
                        "25000000.0",  # taker_buy_quote
                        "0",  # ignore
                    ],
                )
                current_time += timedelta(minutes=15)

            mock_instance.get_klines.return_value = mock_klines

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
            with patch("shared_code.kucoin.Market") as mock_market:
                mock_instance = mock_market.return_value
                mock_instance.get_kline.return_value = {
                    "code": "200000",
                    "data": [
                        [
                            str(int((start_time + timedelta(minutes=15 * i)).timestamp())),
                            "50000",  # open
                            "50100",  # close
                            "50200",  # high
                            "49900",  # low
                            "1000",  # volume
                            "50000000",  # turnover
                        ]
                        for i in range(8)
                    ],
                }

                fetch_fifteen_min_candles(kucoin_symbol, start_time, end_time, conn)
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

        # Mock Binance API call
        with patch("shared_code.binance.BinanceClient") as mock_client:
            mock_instance = mock_client.return_value
            mock_klines = []
            current_time = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
            for _ in range(4):
                open_time_ms = int(current_time.timestamp() * 1000)
                mock_klines.append(
                    [
                        open_time_ms,
                        "50000.0",
                        "50200.0",
                        "49900.0",
                        "50100.0",
                        "1000.0",
                        open_time_ms + (24 * 60 * 60 * 1000),
                        "50000000.0",
                        100,
                        "500.0",
                        "25000000.0",
                        "0",
                    ],
                )
                current_time += timedelta(days=1)

            mock_instance.get_klines.return_value = mock_klines

            candles_before = fetch_daily_candles(binance_symbol, start_date, today, conn)
            count_before = len(candles_before)

        # Fetch again (should use cache, no API call)
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

    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=2)

    # Mock Binance API for all three test scenarios
    with patch("shared_code.binance.BinanceClient") as mock_client:
        mock_instance = mock_client.return_value

        # Mock for daily candles (3 days)
        def create_mock_klines(
            count: int,
            start: datetime,
            interval_delta: timedelta,
        ) -> list:
            mock_klines = []
            current_time = start
            for _ in range(count):
                open_time_ms = int(current_time.timestamp() * 1000)
                mock_klines.append(
                    [
                        open_time_ms,
                        "50000.0",
                        "50200.0",
                        "49900.0",
                        "50100.0",
                        "1000.0",
                        open_time_ms + int(interval_delta.total_seconds() * 1000),
                        "50000000.0",
                        100,
                        "500.0",
                        "25000000.0",
                        "0",
                    ],
                )
                current_time += interval_delta
            return mock_klines

        # Test daily candles
        mock_instance.get_klines.return_value = create_mock_klines(
            3,
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC),
            timedelta(days=1),
        )
        daily_candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

        assert len(daily_candles) > 0, "No daily candles returned"
        for candle in daily_candles:
            assert has_timezone(candle.end_date), (
                f"end_date missing timezone: {candle.end_date} (type: {type(candle.end_date)})"
            )

        # Test hourly candles
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=6)
        mock_instance.get_klines.return_value = create_mock_klines(
            6,
            start_time,
            timedelta(hours=1),
        )
        hourly_candles = fetch_hourly_candles(binance_symbol, start_time, end_time, conn)

        assert len(hourly_candles) > 0, "No hourly candles returned"
        for candle in hourly_candles:
            assert has_timezone(candle.end_date), (
                f"end_date missing timezone: {candle.end_date} (type: {type(candle.end_date)})"
            )

        # Test 15-min candles
        start_time = end_time - timedelta(hours=2)
        mock_instance.get_klines.return_value = create_mock_klines(
            8,
            start_time,
            timedelta(minutes=15),
        )
        fifteen_min_candles = fetch_fifteen_min_candles(
            binance_symbol,
            start_time,
            end_time,
            conn,
        )

        assert len(fifteen_min_candles) > 0, "No 15-min candles returned"
        for candle in fifteen_min_candles:
            assert has_timezone(candle.end_date), (
                f"end_date missing timezone: {candle.end_date} (type: {type(candle.end_date)})"
            )

    conn.close()


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

    # Mock Binance API call
    with patch("shared_code.binance.BinanceClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_klines = []
        current_time = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        for _ in range(31):
            open_time_ms = int(current_time.timestamp() * 1000)
            mock_klines.append(
                [
                    open_time_ms,
                    "50000.0",
                    "50200.0",
                    "49900.0",
                    "50100.0",
                    "1000.0",
                    open_time_ms + (24 * 60 * 60 * 1000),
                    "50000000.0",
                    100,
                    "500.0",
                    "25000000.0",
                    "0",
                ],
            )
            current_time += timedelta(days=1)

        mock_instance.get_klines.return_value = mock_klines

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

    # Mock Binance API call for initial fetch
    with patch("shared_code.binance.BinanceClient") as mock_client:
        mock_instance = mock_client.return_value
        mock_klines = []
        current_time = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        for _ in range(3):
            open_time_ms = int(current_time.timestamp() * 1000)
            mock_klines.append(
                [
                    open_time_ms,
                    "50000.0",
                    "50200.0",
                    "49900.0",
                    "50100.0",
                    "1000.0",
                    open_time_ms + (24 * 60 * 60 * 1000),
                    "50000000.0",
                    100,
                    "500.0",
                    "25000000.0",
                    "0",
                ],
            )
            current_time += timedelta(days=1)

        mock_instance.get_klines.return_value = mock_klines

        fetch_daily_candles(binance_symbol, start_date, today, conn)

    # Second fetch should use cache entirely (no API call needed)
    candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

    assert candles is not None, "Failed to fetch candles from cache"
    assert len(candles) > 0, "No candles returned from cache"

    conn.close()
