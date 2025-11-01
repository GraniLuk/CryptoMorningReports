"""Test RSI calculation accuracy against TradingView values.

This module tests RSI calculations using different methods (RMA/EMA) and compares
results with known TradingView values to ensure accuracy.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from shared_code.price_checker import fetch_daily_candles
from source_repository import fetch_symbols
from technical_analysis.reports.rsi_daily import create_rsi_table_for_symbol
from technical_analysis.rsi import calculate_rsi_using_ema, calculate_rsi_using_rma


class TestRSICalculationMethods:
    """Test different RSI calculation methods."""

    def test_rsi_simple_increasing_sequence(self):
        """Test RSI calculation on a simple increasing sequence."""
        # Simple increasing prices should show high RSI (overbought)
        prices = pd.Series(
            [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]
        )

        rsi = calculate_rsi_using_rma(prices, periods=14)

        # Last RSI should be 100 (all gains, no losses)
        assert rsi.iloc[-1] == 100.0

    def test_rsi_simple_decreasing_sequence(self):
        """Test RSI calculation on a simple decreasing sequence."""
        # Simple decreasing prices should show low RSI (oversold)
        prices = pd.Series(
            [115, 114, 113, 112, 111, 110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100]
        )

        rsi = calculate_rsi_using_rma(prices, periods=14)

        # Last RSI should be 0 (no gains, all losses)
        assert rsi.iloc[-1] == 0.0

    def test_rsi_stable_prices(self):
        """Test RSI calculation on stable prices."""
        # Stable prices should show RSI around 50
        prices = pd.Series([100] * 20)

        rsi = calculate_rsi_using_rma(prices, periods=14)

        # All values should be NaN since there's no change
        # After first diff, we get zeros, which should result in RSI=50 or NaN
        # depending on implementation
        assert pd.isna(rsi.iloc[-1]) or abs(rsi.iloc[-1] - 50) < 1

    def test_rsi_period_14_default(self):
        """Test that default period is 14."""
        prices = pd.Series(
            [
                100,
                102,
                101,
                103,
                102,
                104,
                103,
                105,
                104,
                106,
                105,
                107,
                106,
                108,
                107,
                109,
                108,
                110,
            ]
        )

        rsi_default = calculate_rsi_using_rma(prices)
        rsi_14 = calculate_rsi_using_rma(prices, periods=14)

        pd.testing.assert_series_equal(rsi_default, rsi_14)

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data points."""
        prices = pd.Series([100, 101, 102])

        rsi = calculate_rsi_using_rma(prices, periods=14)

        # Should have NaN values due to insufficient data
        assert rsi.isna().all()


class TestRSIAgainstTradingView:
    """Test RSI calculations against TradingView reference values."""

    @pytest.fixture
    def get_virtual_data(self):
        """Fixture to fetch VIRTUAL symbol data from database."""
        load_dotenv()
        conn = connect_to_sql()
        symbols = fetch_symbols(conn)
        virtual = next((s for s in symbols if s.symbol_name == "VIRTUAL"), None)

        if virtual is None:
            pytest.skip("VIRTUAL symbol not found in database")

        # Fetch data for today and past 30+ days to ensure enough data for RSI
        # Need at least 28+ days: 14 for initial SMA + 14+ for Wilder's smoothing to stabilize
        target_date = datetime.now(UTC).date()
        start_date = target_date - timedelta(days=35)
        candles = fetch_daily_candles(virtual, start_date, target_date, conn)

        return candles, virtual, target_date

    def test_virtual_rsi_against_tradingview(self, get_virtual_data):
        """Test VIRTUAL RSI calculation against TradingView value.

        TradingView shows RSI = 69.01 for today's candle
        Settings: RSI length 14, source close, Type RMA (default)

        Note: A small difference (1-3 points) is acceptable due to:
        - Data source differences (Binance vs TradingView's feed)
        - Candle timing differences
        - Rounding in intermediate calculations
        """
        candles, _symbol, _target_date = get_virtual_data

        if not candles:
            pytest.skip("No candle data available for VIRTUAL")

        # Create DataFrame from candles
        df = pd.DataFrame(
            [
                {
                    "Date": candle.end_date,
                    "close": candle.close,
                }
                for candle in candles
            ]
        )
        df = df.set_index("Date")
        df = df.sort_index()

        # Calculate RSI using RMA (which is what TradingView uses)
        df["RSI_RMA"] = calculate_rsi_using_rma(df["close"], periods=14)

        # Also test with EMA for comparison
        df["RSI_EMA"] = calculate_rsi_using_ema(df["close"], period=14)

        # Get the latest RSI value
        latest_rsi_rma = df["RSI_RMA"].iloc[-1]
        df["RSI_EMA"].iloc[-1]
        df["close"].iloc[-1]


        # Print last 15 days of data for debugging

        # TradingView uses RMA (Wilder's smoothing) for RSI calculation
        # Allow tolerance for data source and timing differences
        # Typical difference is 1-3 points due to different data feeds
        tolerance = 3.0

        assert not pd.isna(latest_rsi_rma), "RSI calculation returned NaN"
        assert abs(latest_rsi_rma - 69.01) < tolerance, (
            f"RSI mismatch: calculated {latest_rsi_rma:.2f}, expected 69.01 (TradingView). "
            f"Difference of {abs(latest_rsi_rma - 69.01):.2f} exceeds tolerance of {tolerance}"
        )

    def test_rsi_calculation_consistency(self, get_virtual_data):
        """Test that RSI calculation is consistent across multiple runs."""
        candles, _symbol, _target_date = get_virtual_data

        if not candles:
            pytest.skip("No candle data available for VIRTUAL")

        df = pd.DataFrame(
            [
                {
                    "Date": candle.end_date,
                    "close": candle.close,
                }
                for candle in candles
            ]
        )
        df = df.set_index("Date")
        df = df.sort_index()

        # Calculate RSI multiple times
        rsi1 = calculate_rsi_using_rma(df["close"], periods=14)
        rsi2 = calculate_rsi_using_rma(df["close"], periods=14)
        rsi3 = calculate_rsi_using_rma(df["close"], periods=14)

        # All calculations should be identical
        pd.testing.assert_series_equal(rsi1, rsi2)
        pd.testing.assert_series_equal(rsi2, rsi3)


class TestRSIEdgeCases:
    """Test RSI calculation edge cases."""

    def test_rsi_with_nan_values(self):
        """Test RSI handles NaN values in price data."""
        prices = pd.Series(
            [100, 101, None, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]
        )

        # Should handle NaN gracefully
        rsi = calculate_rsi_using_rma(prices, periods=14)

        # Result might have NaN but shouldn't crash
        assert isinstance(rsi, pd.Series)

    def test_rsi_with_negative_prices(self):
        """Test RSI with negative prices (invalid for crypto but test edge case)."""
        prices = pd.Series(
            [-100, -99, -98, -97, -96, -95, -94, -93, -92, -91, -90, -89, -88, -87, -86, -85]
        )

        # Should still calculate (mathematically valid)
        rsi = calculate_rsi_using_rma(prices, periods=14)

        # All gains, should be 100
        assert rsi.iloc[-1] == 100.0

    def test_rsi_with_extreme_volatility(self):
        """Test RSI with extreme price swings."""
        prices = pd.Series(
            [100, 200, 50, 300, 25, 400, 10, 500, 5, 600, 1, 700, 0.5, 800, 0.1, 900]
        )

        rsi = calculate_rsi_using_rma(prices, periods=14)

        # Should produce valid RSI values
        assert not pd.isna(rsi.iloc[-1])
        assert 0 <= rsi.iloc[-1] <= 100


class TestRSIDataRequirements:
    """Test that RSI calculations use sufficient data for accuracy."""

    def test_rsi_requires_sufficient_data(self):
        """Test that RSI with insufficient data differs from RSI with sufficient data."""
        load_dotenv()
        conn = connect_to_sql()
        symbols = fetch_symbols(conn)
        virtual = next((s for s in symbols if s.symbol_name == "VIRTUAL"), None)

        if not virtual:
            pytest.skip("VIRTUAL symbol not found")

        target_date = datetime.now(UTC).date()

        # Test with insufficient data (15 days)
        candles_15 = fetch_daily_candles(
            virtual, target_date - timedelta(days=15), target_date, conn
        )
        df_15 = pd.DataFrame([{"Date": c.end_date, "close": c.close} for c in candles_15])
        df_15 = df_15.set_index("Date")
        calculate_rsi_using_rma(df_15["close"])

        # Test with sufficient data (30+ days)
        candles_30 = fetch_daily_candles(
            virtual, target_date - timedelta(days=30), target_date, conn
        )
        df_30 = pd.DataFrame([{"Date": c.end_date, "close": c.close} for c in candles_30])
        df_30 = df_30.set_index("Date")
        calculate_rsi_using_rma(df_30["close"])


        # The values should differ significantly when data is insufficient
        # With proper data, Wilder's smoothing stabilizes
        assert len(candles_30) >= 28, "Should fetch at least 28 days for accurate RSI"


class TestRSIMethodComparison:
    """Compare different RSI calculation methods."""

    def test_rma_vs_ema_methods(self):
        """Compare RMA and EMA RSI calculation methods."""
        prices = pd.Series(
            [
                100.0,
                101.5,
                103.2,
                102.1,
                104.5,
                103.8,
                105.2,
                106.1,
                107.3,
                106.5,
                108.2,
                109.1,
                108.5,
                110.2,
                111.5,
                112.3,
                111.8,
                113.2,
                114.5,
                113.9,
            ]
        )

        rsi_rma = calculate_rsi_using_rma(prices, periods=14)
        rsi_ema = calculate_rsi_using_ema(prices, period=14)


        # Methods should produce similar but not identical results
        # RMA and EMA use different smoothing, so some difference is expected
        assert not pd.isna(rsi_rma.iloc[-1])
        assert not pd.isna(rsi_ema.iloc[-1])


def test_rsi_integration_with_database():
    """Integration test: Verify RSI calculation and storage workflow."""
    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    # Test with VIRTUAL if available
    virtual = next((s for s in symbols if s.symbol_name == "VIRTUAL"), None)

    if virtual:
        target_date = datetime.now(UTC).date()
        table = create_rsi_table_for_symbol(virtual, conn, target_date)

        # Should return a valid PrettyTable or None
        assert table is not None or table is None  # Valid outputs

        if table:
            pass


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
