"""TDD Test: ETF report should NEVER show old data when today's fetch fails.

Test Requirements:
1. If today's data exists in DB → use it
2. If today's data NOT in DB → fetch from API
3. If API fails → show NO DATA (not old data from yesterday)
4. NEVER show data from previous days when today's fetch fails

This test should FAIL with current code because it falls back to old data.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from etf.etf_report import fetch_etf_summary_report, update_etf_data
from etf.etf_repository import ETFRepository
from reports.daily_report import _build_etf_flows_section


if TYPE_CHECKING:
    from sqlite3 import Connection


# Azure SQL schema uses PascalCase column names
CREATE_TABLE_SQL = """
    CREATE TABLE ETFFlows (
        Ticker TEXT NOT NULL,
        Coin TEXT NOT NULL,
        Issuer TEXT,
        Price REAL,
        AUM REAL,
        Flows REAL,
        FlowsChange REAL,
        Volume REAL,
        FetchDate TEXT NOT NULL,
        PRIMARY KEY (Ticker, FetchDate)
    )
"""


class MockConnection:
    """Mock connection wrapper that matches production SQLiteConnectionWrapper."""

    def __init__(self, conn: Connection) -> None:  # noqa: D107
        self._conn = conn

    def cursor(self):  # noqa: D102
        return self._conn.cursor()

    def execute(self, sql, params=None):  # noqa: D102
        if params:
            return self._conn.execute(sql, params)
        return self._conn.execute(sql)

    def commit(self) -> None:  # noqa: D102
        self._conn.commit()

    def rollback(self) -> None:  # noqa: D102
        self._conn.rollback()


class TestETFNoOldDataFallback:
    """Test that ETF report never shows old data when today's fetch fails."""

    def test_etf_report_uses_only_todays_data_from_database(self, tmp_path):
        """Test 1: When today's data exists in DB, use it (don't call API)."""
        # Setup database with TODAY's data
        db_path = tmp_path / "test_etf.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(CREATE_TABLE_SQL)

        today = datetime.now(UTC).date().isoformat()

        # Insert TODAY's data (with specific flows)
        conn.execute(
            """
            INSERT INTO ETFFlows
            (Ticker, Coin, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            ("IBIT", "BTC", "BlackRock", 42.50, 1000000000, 100000000, 5000000, 200000000, today),
        )
        conn.execute(
            """
            INSERT INTO ETFFlows
            (Ticker, Coin, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            ("ETHE", "ETH", "Grayscale", 25.30, 500000000, 50000000, 2000000, 100000000, today),
        )
        conn.commit()

        wrapped_conn = MockConnection(conn)

        # Get summary report
        report = fetch_etf_summary_report(wrapped_conn)  # type: ignore[arg-type]
        report_str = str(report)

        # Should show TODAY's data
        assert "BTC" in report_str
        assert "ETH" in report_str

        conn.close()

    @patch("etf.etf_fetcher.fetch_yfinance_etf_data")
    @patch("etf.etf_fetcher.scrape_defillama_etf")
    def test_etf_report_shows_no_data_when_api_fails_and_no_today_data(
        self,
        mock_scrape,
        mock_yfinance,
        tmp_path,
    ):
        """Test 2: When API fails and NO today's data in DB → show 'No data' (not old data)."""
        # Setup database with YESTERDAY's data (OLD DATA)
        db_path = tmp_path / "test_etf.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(CREATE_TABLE_SQL)

        yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()

        # Insert YESTERDAY's data with FIXED VALUES ($75M BTC, $45M ETH)
        conn.execute(
            """
            INSERT INTO ETFFlows
            (Ticker, Coin, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "IBIT",
                "BTC",
                "BlackRock",
                42.50,
                1000000000,
                75000000,  # THE PROBLEMATIC $75M
                5000000,
                200000000,
                yesterday,
            ),
        )
        conn.execute(
            """
            INSERT INTO ETFFlows
            (Ticker, Coin, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "ETHE",
                "ETH",
                "Grayscale",
                25.30,
                500000000,
                45000000,  # THE PROBLEMATIC $45M
                2000000,
                100000000,
                yesterday,
            ),
        )
        conn.commit()

        wrapped_conn = MockConnection(conn)

        # Simulate both API failures (DefiLlama and YFinance fallback)
        mock_scrape.side_effect = Exception("DefiLlama scraping failed")
        mock_yfinance.return_value = None  # YFinance fallback also fails

        # Try to update ETF data (should fail)
        success = update_etf_data(wrapped_conn)  # type: ignore[arg-type]

        # CRITICAL: Update should fail
        assert success is False, "update_etf_data should return False when API fails"

        # Get summary report
        report = fetch_etf_summary_report(wrapped_conn)  # type: ignore[arg-type]
        report_str = str(report)

        print("\n" + "=" * 80)
        print("REPORT OUTPUT:")
        print(report_str)
        print("=" * 80)

        # CRITICAL ASSERTIONS:
        # 1. Should NOT show the old $75M value
        assert "75M" not in report_str, "❌ FAIL: Report is showing OLD $75M data from yesterday!"
        assert "75,000,000" not in report_str, "❌ FAIL: Report is showing OLD $75M data!"

        # 2. Should NOT show the old $45M value
        assert "45M" not in report_str, "❌ FAIL: Report is showing OLD $45M data from yesterday!"
        assert "45,000,000" not in report_str, "❌ FAIL: Report is showing OLD $45M data!"

        # 3. Should show "No data" since today's fetch failed
        assert "No data" in report_str or "$0" in report_str or "unavailable" in report_str, (
            "❌ FAIL: Report should show 'No data' or '$0' when today's fetch fails!"
        )

        # 4. Make sure it's not showing yesterday's date
        assert yesterday not in report_str, "❌ FAIL: Report is showing yesterday's date!"

        conn.close()

    def test_etf_repository_get_latest_returns_only_today(self, tmp_path):
        """Test 3: ETFRepository.get_latest_etf_flows should ONLY return today's data."""
        # Setup database with multiple dates
        db_path = tmp_path / "test_etf.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(CREATE_TABLE_SQL)

        today = datetime.now(UTC).date().isoformat()
        yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        two_days_ago = (datetime.now(UTC).date() - timedelta(days=2)).isoformat()

        # Insert data for multiple days
        for date, flows in [(two_days_ago, 50000000), (yesterday, 75000000), (today, 100000000)]:
            conn.execute(
                """
                INSERT INTO ETFFlows
                (Ticker, Coin, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                ("IBIT", "BTC", "BlackRock", 42.50, 1000000000, flows, 5000000, 200000000, date),
            )
        conn.commit()

        wrapped_conn = MockConnection(conn)
        repo = ETFRepository(wrapped_conn)  # type: ignore[arg-type]

        # Get latest flows
        latest = repo.get_latest_etf_flows("BTC")

        # CRITICAL: Should only return TODAY's data
        assert latest is not None, "Should return data"
        assert len(latest) == 1, "Should return only 1 record (today's)"

        etf = latest[0]
        assert etf["fetch_date"] == today, f"Should return today's data, not {etf['fetch_date']}"
        assert etf["flows"] == 100000000, f"Should return today's flows (100M), not {etf['flows']}"

        # Should NOT return yesterday's $75M or two days ago $50M
        assert etf["flows"] != 75000000, "Should NOT return yesterday's $75M!"
        assert etf["flows"] != 50000000, "Should NOT return old $50M!"

        conn.close()

    def test_build_etf_flows_section_with_no_data(self, tmp_path):
        """Test 4: _build_etf_flows_section should show 'No data' when no today's data exists."""
        # Setup EMPTY database
        db_path = tmp_path / "test_etf.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()

        wrapped_conn = MockConnection(conn)

        # Build ETF flows section
        section = _build_etf_flows_section(wrapped_conn)  # type: ignore[arg-type]

        print("\n" + "=" * 80)
        print("ETF FLOWS SECTION OUTPUT:")
        print(section)
        print("=" * 80)

        # CRITICAL: Should show something indicating no data
        assert (
            "unavailable" in section.lower()
            or "no data" in section.lower()
            or "no etf data" in section.lower()
            or "$0" in section
        ), "Should show data is unavailable when no data exists"

        # Should NOT show any dollar amounts
        assert "$75" not in section, "Should not show $75M"
        assert "$45" not in section, "Should not show $45M"

        conn.close()


if __name__ == "__main__":
    # Run the tests to see them FAIL with current code
    pytest.main([__file__, "-v", "-s"])
