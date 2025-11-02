"""Test script for fetch_binance_daily_klines_batch function.

This script validates the new batch function for daily candles.
"""

from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from shared_code.binance import fetch_binance_daily_klines_batch
from source_repository import SourceID, Symbol, fetch_symbols


def test_batch_fetch():
    """Test the batch fetch function with various date ranges."""
    load_dotenv()
    conn = connect_to_sql()

    # Get BTC symbol from database
    symbols = fetch_symbols(conn)
    btc = next((s for s in symbols if s.symbol_name == "BTC"), None)

    if not btc:
        print("❌ BTC symbol not found in database")
        return

    print(f"Testing with symbol: {btc.symbol_name} (source: {btc.source_id})")
    print("=" * 80)

    # Test 1: Fetch last 7 days
    print("\n📊 Test 1: Fetching last 7 days of daily candles...")
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=6)
    candles = fetch_binance_daily_klines_batch(btc, start_date, end_date)

    if candles:
        print(f"✅ Success! Fetched {len(candles)} candles")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   First candle: {candles[0].end_date} - Close: ${candles[0].close:.2f}")
        print(f"   Last candle:  {candles[-1].end_date} - Close: ${candles[-1].close:.2f}")
    else:
        print("❌ Failed to fetch candles")

    # Test 2: Fetch last 30 days
    print("\n📊 Test 2: Fetching last 30 days of daily candles...")
    start_date = end_date - timedelta(days=29)
    candles = fetch_binance_daily_klines_batch(btc, start_date, end_date)

    if candles:
        print(f"✅ Success! Fetched {len(candles)} candles")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   First candle: {candles[0].end_date} - Close: ${candles[0].close:.2f}")
        print(f"   Last candle:  {candles[-1].end_date} - Close: ${candles[-1].close:.2f}")
    else:
        print("❌ Failed to fetch candles")

    # Test 3: Fetch last 180 days
    print("\n📊 Test 3: Fetching last 180 days of daily candles...")
    start_date = end_date - timedelta(days=179)
    candles = fetch_binance_daily_klines_batch(btc, start_date, end_date)

    if candles:
        print(f"✅ Success! Fetched {len(candles)} candles")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   First candle: {candles[0].end_date} - Close: ${candles[0].close:.2f}")
        print(f"   Last candle:  {candles[-1].end_date} - Close: ${candles[-1].close:.2f}")
    else:
        print("❌ Failed to fetch candles")

    # Test 4: Test with > 1000 days (should limit to 1000)
    print("\n📊 Test 4: Fetching 1100 days (should limit to 1000)...")
    start_date = end_date - timedelta(days=1099)
    candles = fetch_binance_daily_klines_batch(btc, start_date, end_date)

    if candles:
        print(f"✅ Success! Fetched {len(candles)} candles (should be ≤ 1000)")
        print(f"   Requested range: {start_date} to {end_date}")
        if len(candles) <= 1000:
            print(f"   ✓ Correctly limited to {len(candles)} candles")
        else:
            print(f"   ⚠️ Warning: Fetched {len(candles)} candles (expected ≤ 1000)")
    else:
        print("❌ Failed to fetch candles")

    # Test 5: Verify data structure
    print("\n📊 Test 5: Verifying candle data structure...")
    start_date = end_date - timedelta(days=1)
    candles = fetch_binance_daily_klines_batch(btc, start_date, end_date)

    if candles and len(candles) > 0:
        candle = candles[0]
        print(f"✅ Candle structure verification:")
        print(f"   Symbol: {candle.symbol}")
        print(f"   Source: {candle.source}")
        print(f"   End Date: {candle.end_date}")
        print(f"   Open: ${candle.open:.2f}")
        print(f"   High: ${candle.high:.2f}")
        print(f"   Low: ${candle.low:.2f}")
        print(f"   Close: ${candle.close:.2f}")
        print(f"   Volume: {candle.volume:.2f}")
        print(f"   Volume Quote: ${candle.volume_quote:.2f}")

        # Verify all required fields are present
        required_fields = ["symbol", "source", "end_date", "open", "high", "low", "close", "volume"]
        all_present = all(hasattr(candle, field) for field in required_fields)
        if all_present:
            print(f"   ✓ All required fields present")
        else:
            print(f"   ⚠️ Some fields missing")
    else:
        print("❌ Failed to fetch candles for verification")

    print("\n" + "=" * 80)
    print("✅ All tests completed!")


if __name__ == "__main__":
    test_batch_fetch()
