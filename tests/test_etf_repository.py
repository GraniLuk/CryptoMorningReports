"""Unit tests for ETF repository functionality."""

import os
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from etf.etf_repository import ETFRepository


class TestETFRepository:
    """Test cases for ETFRepository class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create connection and set up schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create ETFFlows table
        cursor.execute("""
            CREATE TABLE ETFFlows (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Ticker TEXT NOT NULL,
                Coin TEXT NOT NULL,
                Issuer TEXT,
                Price REAL,
                AUM REAL,
                Flows REAL,
                FlowsChange REAL,
                Volume REAL,
                FetchDate TEXT NOT NULL,
                CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(Ticker, FetchDate)
            )
        """)

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        Path(db_path).unlink()

    @pytest.fixture
    def mock_sqlite_conn(self, temp_db):
        """Create a mock SQLite connection wrapper."""
        conn = sqlite3.connect(temp_db)

        # Mock the connection wrapper
        mock_conn = MagicMock()
        mock_conn._conn = conn
        mock_conn.cursor.return_value = conn.cursor()
        mock_conn.commit = conn.commit
        mock_conn.rollback = conn.rollback
        mock_conn.close = conn.close

        # Set SQLite mode
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            yield mock_conn

        conn.close()

    def test_init_sqlite_mode(self, mock_sqlite_conn):
        """Test repository initialization in SQLite mode."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)
            assert repo.conn == mock_sqlite_conn
            assert repo.is_sqlite is True

    def test_init_azure_mode(self, mock_sqlite_conn):
        """Test repository initialization in Azure SQL mode."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "azuresql"}):
            repo = ETFRepository(mock_sqlite_conn)
            assert repo.conn == mock_sqlite_conn
            assert repo.is_sqlite is False

    def test_save_etf_flow_sqlite(self, mock_sqlite_conn):
        """Test saving ETF flow data in SQLite mode."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)

            # Test data
            test_data = {
                "ticker": "IBIT",
                "coin": "BTC",
                "issuer": "BlackRock",
                "price": 42.50,
                "aum": 1000000000,
                "flows": 50000000,
                "flows_change": 10000000,
                "volume": 200000000,
                "fetch_date": "2024-01-15",
            }

            # Save data
            repo.save_etf_flow(**test_data)

            # Verify data was saved
            cursor = mock_sqlite_conn._conn.cursor()
            cursor.execute(
                "SELECT * FROM ETFFlows WHERE Ticker = ? AND FetchDate = ?",
                (test_data["ticker"], test_data["fetch_date"]),
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[1] == test_data["ticker"]  # Ticker
            assert row[2] == test_data["coin"]  # Coin
            assert row[3] == test_data["issuer"]  # Issuer
            assert row[4] == test_data["price"]  # Price
            assert row[5] == test_data["aum"]  # AUM
            assert row[6] == test_data["flows"]  # Flows

    def test_save_etf_flow_duplicate_update(self, mock_sqlite_conn):
        """Test that duplicate ETF entries update existing records."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)

            # Insert initial data
            test_data = {
                "ticker": "IBIT",
                "coin": "BTC",
                "issuer": "BlackRock",
                "price": 42.50,
                "aum": 1000000000,
                "flows": 50000000,
                "flows_change": 10000000,
                "volume": 200000000,
                "fetch_date": "2024-01-15",
            }
            repo.save_etf_flow(**test_data)

            # Update with new flows
            updated_data = test_data.copy()
            updated_data["flows"] = 75000000
            repo.save_etf_flow(**updated_data)

            # Verify only one record exists with updated flows
            cursor = mock_sqlite_conn._conn.cursor()
            cursor.execute(
                "SELECT COUNT(*), Flows FROM ETFFlows WHERE Ticker = ? AND FetchDate = ?",
                (test_data["ticker"], test_data["fetch_date"]),
            )
            count, flows = cursor.fetchone()

            assert count == 1
            assert flows == 75000000

    def test_get_latest_etf_flows(self, mock_sqlite_conn):
        """Test retrieving latest ETF flows for a coin (only today's data)."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)

            today = datetime.now(UTC).date().isoformat()
            yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()

            # Insert test data for different dates
            test_etfs = [
                {
                    "ticker": "IBIT",
                    "coin": "BTC",
                    "issuer": "BlackRock",
                    "price": 42.50,
                    "aum": 1000000000,
                    "flows": 50000000,
                    "flows_change": 10000000,
                    "volume": 200000000,
                    "fetch_date": yesterday,  # OLD data - should be ignored
                },
                {
                    "ticker": "IBIT",
                    "coin": "BTC",
                    "issuer": "BlackRock",
                    "price": 43.00,
                    "aum": 1050000000,
                    "flows": 60000000,
                    "flows_change": 15000000,
                    "volume": 220000000,
                    "fetch_date": today,  # TODAY's data - should be returned
                },
            ]

            for etf in test_etfs:
                repo.save_etf_flow(**etf)

            # Retrieve latest BTC flows (should only get TODAY's data)
            result = repo.get_latest_etf_flows("BTC")

            assert result is not None
            assert len(result) == 1
            assert result[0]["ticker"] == "IBIT"
            assert result[0]["flows"] == 60000000
            assert result[0]["fetch_date"] == today  # Should be TODAY, not yesterday

    def test_get_latest_etf_flows_no_data(self, mock_sqlite_conn):
        """Test retrieving latest ETF flows when no data exists."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)

            result = repo.get_latest_etf_flows("BTC")
            assert result is None

    def test_get_weekly_etf_flows(self, mock_sqlite_conn):
        """Test retrieving weekly aggregated ETF flows."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)

            # Insert test data for multiple days (use recent dates)
            base_date = datetime.now(UTC).date() - timedelta(days=6)  # Start 6 days ago
            test_etfs = []

            for i in range(7):
                current_date = base_date + timedelta(days=i)
                test_etfs.append(
                    {
                        "ticker": "IBIT",
                        "coin": "BTC",
                        "issuer": "BlackRock",
                        "price": 42.50 + i,
                        "aum": 1000000000 + (i * 50000000),
                        "flows": 50000000 + (i * 5000000),
                        "flows_change": 10000000,
                        "volume": 200000000,
                        "fetch_date": current_date.isoformat(),
                    },
                )

            for etf in test_etfs:
                repo.save_etf_flow(**etf)

            # Get weekly flows
            result = repo.get_weekly_etf_flows("BTC", days=7)

            assert result is not None
            assert "total_flows" in result
            assert "avg_daily_flows" in result
            assert "days_count" in result
            assert result["days_count"] == 7
            assert result["start_date"] == base_date.isoformat()
            assert result["end_date"] == (base_date + timedelta(days=6)).isoformat()

    def test_get_etf_flows_by_issuer(self, mock_sqlite_conn, subtests):
        """Test retrieving ETF flows grouped by issuer."""
        with patch.dict(os.environ, {"DATABASE_TYPE": "sqlite"}):
            repo = ETFRepository(mock_sqlite_conn)

            # Insert test data for multiple issuers
            test_etfs = [
                {
                    "ticker": "IBIT",
                    "coin": "BTC",
                    "issuer": "BlackRock",
                    "price": 42.50,
                    "aum": 1000000000,
                    "flows": 50000000,
                    "flows_change": 10000000,
                    "volume": 200000000,
                    "fetch_date": "2024-01-15",
                },
                {
                    "ticker": "FBTC",
                    "coin": "BTC",
                    "issuer": "Fidelity",
                    "price": 42.60,
                    "aum": 800000000,
                    "flows": 30000000,
                    "flows_change": 5000000,
                    "volume": 150000000,
                    "fetch_date": "2024-01-15",
                },
            ]

            for etf in test_etfs:
                repo.save_etf_flow(**etf)

            # Get flows by issuer
            result = repo.get_etf_flows_by_issuer("BTC", "2024-01-15")

            with subtests.test(msg="Result exists"):
                assert result is not None
            with subtests.test(msg="Issuer count"):
                assert len(result) == 2

            # Test each issuer independently
            expected_issuers = {
                "BlackRock": {"total_flows": 50000000, "etf_count": 1},
                "Fidelity": {"total_flows": 30000000, "etf_count": 1},
            }

            for issuer_name, expected in expected_issuers.items():
                with subtests.test(issuer=issuer_name):
                    issuer_data = next((r for r in result if r["issuer"] == issuer_name), None)
                    assert issuer_data is not None, f"Issuer {issuer_name} not found"
                    assert issuer_data["total_flows"] == expected["total_flows"]
                    assert issuer_data["etf_count"] == expected["etf_count"]
