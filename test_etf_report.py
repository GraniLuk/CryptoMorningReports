"""Test script for ETF report functionality."""

import sys
from datetime import datetime

from infra.sql_connection import connect_to_sql_sqlite
from etf.etf_report import update_etf_data, fetch_etf_summary_report
from infra.telegram_logging_handler import app_logger


def test_etf_functionality():
    """Test the complete ETF functionality."""
    print("=" * 80)
    print("ETF Functionality Test")
    print("=" * 80)
    print()

    # Connect to database
    print("1. Connecting to database...")
    conn = connect_to_sql_sqlite()
    if conn is None:
        print("❌ Failed to connect to database")
        sys.exit(1)
    print("✅ Database connection successful")
    print()

    # Test update_etf_data (fetch or use cached)
    print("2. Testing ETF data update (will fetch from API or use cached data)...")
    try:
        success = update_etf_data(conn)
        if success:
            print("✅ ETF data update successful")
        else:
            print("⚠️ ETF data update returned False (may be using mock data)")
    except Exception as e:
        print(f"❌ ETF data update failed: {e}")
        import traceback
        traceback.print_exc()
    print()

    # Test BTC ETF report
    print("3. Testing ETF summary report generation...")
    try:
        etf_summary = fetch_etf_summary_report(conn)
        print("✅ ETF summary report generated successfully:")
        print(etf_summary)
    except Exception as e:
        print(f"❌ ETF summary report generation failed: {e}")
        import traceback
        traceback.print_exc()
    print()

    # Verify data in database
    print("4. Verifying data in database...")
    try:
        from etf.etf_repository import ETFRepository
        repo = ETFRepository(conn)

        btc_flows = repo.get_latest_etf_flows("BTC")
        eth_flows = repo.get_latest_etf_flows("ETH")

        if btc_flows:
            print(f"✅ Found {len(btc_flows)} BTC ETF records in database")
            for etf in btc_flows[:3]:  # Show first 3
                print(f"   - {etf['ticker']}: {etf['issuer']}, Flows: ${etf['flows']:,.0f}")
        else:
            print("⚠️ No BTC ETF data found in database")

        if eth_flows:
            print(f"✅ Found {len(eth_flows)} ETH ETF records in database")
            for etf in eth_flows[:3]:  # Show first 3
                print(f"   - {etf['ticker']}: {etf['issuer']}, Flows: ${etf['flows']:,.0f}")
        else:
            print("⚠️ No ETH ETF data found in database")
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        import traceback
        traceback.print_exc()
    print()

    # Close connection
    conn.close()
    print("=" * 80)
    print("Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_etf_functionality()
