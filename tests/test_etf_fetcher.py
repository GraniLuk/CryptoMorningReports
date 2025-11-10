"""Integration tests for ETF fetcher functionality."""

from unittest.mock import MagicMock, patch

import requests

from etf.etf_fetcher import (
    _safe_float_parse,
    fetch_etf_data,
    get_etf_summary_stats,
    parse_etf_data,
)


class TestETFFetcher:
    """Test cases for ETF fetcher functions."""

    @patch("etf.etf_fetcher.yf.download")
    def test_fetch_etf_data_success(self, mock_download):
        """Test successful API fetch."""
        # Mock successful response from yfinance with multi-index columns
        import pandas as pd

        # YFinance returns multi-indexed columns: (ticker, field)
        # Create sample data for IBIT and ETHE
        dates = pd.date_range("2024-01-15", periods=1)
        mock_data = pd.DataFrame(
            {
                ("IBIT", "Close"): [42.50],
                ("IBIT", "Volume"): [200000000],
                ("ETHE", "Close"): [25.30],
                ("ETHE", "Volume"): [100000000],
            },
            index=dates,
        )

        mock_download.return_value = mock_data

        result = fetch_etf_data()

        assert result is not None
        assert len(result) == 2
        # Find IBIT and ETHE in results (order may vary)
        ibit = next((r for r in result if r["Ticker"] == "IBIT"), None)
        ethe = next((r for r in result if r["Ticker"] == "ETHE"), None)
        assert ibit is not None
        assert ethe is not None
        assert ibit["Price"] == 42.50
        assert ethe["Price"] == 25.30

    @patch("etf.etf_fetcher.yf.download")
    def test_fetch_etf_data_http_error(self, mock_download):
        """Test API fetch with error - should return None (no mock fallback)."""
        # Simulate yfinance raising an exception
        mock_download.side_effect = Exception("YFinance error")

        result = fetch_etf_data()

        # Should return None on error (we removed mock data fallback)
        assert result is None

    @patch("etf.etf_fetcher.yf.download")
    def test_fetch_etf_data_timeout(self, mock_download):
        """Test API fetch with timeout - should return None (no mock fallback)."""
        mock_download.side_effect = Exception("Timeout")

        result = fetch_etf_data()

        # Should return None on error (we removed mock data fallback)
        assert result is None

    @patch("etf.etf_fetcher.yf.download")
    def test_fetch_etf_data_invalid_json(self, mock_download):
        """Test API fetch with invalid data - should return None (no mock fallback)."""
        # Simulate yfinance returning invalid data (e.g., not a DataFrame)
        mock_download.return_value = None

        result = fetch_etf_data()

        # Should return None on error (we removed mock data fallback)
        assert result is None

    @patch("etf.etf_fetcher.yf.download")
    def test_fetch_defillama_etf_data_empty_response(self, mock_download):
        """Test API fetch with empty response."""
        import pandas as pd

        mock_download.return_value = pd.DataFrame([])

        result = fetch_etf_data()

        # Empty DataFrame should return None (not empty list)
        assert result is None

    def test_parse_etf_data(self):
        """Test parsing ETF data into organized structure."""
        raw_data = [
            {
                "Ticker": "IBIT",
                "Coin": "BTC",
                "Issuer": "BlackRock",
                "Price": 42.50,
                "AUM": 1000000000,
                "Flows": 50000000,
                "FlowsChange": 10000000,
                "Volume": 200000000,
                "Date": 1705276800,  # 2024-01-15
            },
            {
                "Ticker": "ETHE",
                "Coin": "ETH",
                "Issuer": "Grayscale",
                "Price": 25.30,
                "AUM": 500000000,
                "Flows": 25000000,
                "FlowsChange": 5000000,
                "Volume": 100000000,
                "Date": 1705276800,
            },
            {
                "Ticker": "FBTC",
                "Coin": "BTC",
                "Issuer": "Fidelity",
                "Price": 42.60,
                "AUM": 800000000,
                "Flows": 30000000,
                "FlowsChange": 5000000,
                "Volume": 150000000,
                "Date": 1705276800,
            },
        ]

        result = parse_etf_data(raw_data)

        assert "BTC" in result
        assert "ETH" in result
        assert len(result["BTC"]) == 2
        assert len(result["ETH"]) == 1

        # Check BTC ETFs
        btc_etfs = result["BTC"]
        ibit = next(etf for etf in btc_etfs if etf["ticker"] == "IBIT")
        assert ibit["coin"] == "BTC"
        assert ibit["issuer"] == "BlackRock"
        assert ibit["price"] == 42.50
        assert ibit["flows"] == 50000000
        assert ibit["fetch_date"] == "2024-01-15"

        fbtc = next(etf for etf in btc_etfs if etf["ticker"] == "FBTC")
        assert fbtc["issuer"] == "Fidelity"
        assert fbtc["flows"] == 30000000

        # Check ETH ETFs
        eth_etfs = result["ETH"]
        assert len(eth_etfs) == 1
        ethe = eth_etfs[0]
        assert ethe["ticker"] == "ETHE"
        assert ethe["coin"] == "ETH"
        assert ethe["issuer"] == "Grayscale"

    def test_parse_etf_data_invalid_coin(self):
        """Test parsing ETF data with invalid coin type."""
        raw_data = [
            {
                "Ticker": "INVALID",
                "Coin": "INVALID",
                "Issuer": "Test",
                "Price": 1.00,
                "AUM": 1000000,
                "Flows": 10000,
                "FlowsChange": 1000,
                "Volume": 50000,
                "Date": 1705276800,
            },
        ]

        result = parse_etf_data(raw_data)

        # Invalid coin should be filtered out
        assert len(result["BTC"]) == 0
        assert len(result["ETH"]) == 0

    def test_parse_etf_data_missing_fields(self):
        """Test parsing ETF data with missing required fields."""
        raw_data = [
            {
                "Coin": "BTC",
                "Issuer": "Test",
                # Missing Ticker
                "Price": 42.50,
                "AUM": 1000000000,
                "Flows": 50000000,
                "Date": 1705276800,
            },
        ]

        result = parse_etf_data(raw_data)

        # ETF with missing ticker should be skipped
        assert len(result["BTC"]) == 0

    def test_get_etf_summary_stats(self):
        """Test generating summary statistics for ETF data."""
        etf_data = {
            "BTC": [
                {
                    "ticker": "IBIT",
                    "coin": "BTC",
                    "issuer": "BlackRock",
                    "flows": 50000000,
                    "aum": 1000000000,
                },
                {
                    "ticker": "FBTC",
                    "coin": "BTC",
                    "issuer": "Fidelity",
                    "flows": 30000000,
                    "aum": 800000000,
                },
            ],
            "ETH": [
                {
                    "ticker": "ETHE",
                    "coin": "ETH",
                    "issuer": "Grayscale",
                    "flows": 25000000,
                    "aum": 500000000,
                },
            ],
        }

        result = get_etf_summary_stats(etf_data)

        assert "BTC" in result
        assert "ETH" in result

        btc_stats = result["BTC"]
        assert btc_stats["count"] == 2
        assert btc_stats["total_flows"] == 80000000  # 50M + 30M
        assert btc_stats["avg_flows"] == 40000000  # 80M / 2
        assert btc_stats["total_aum"] == 1800000000  # 1B + 800M
        assert "BlackRock" in btc_stats["issuers"]
        assert "Fidelity" in btc_stats["issuers"]

        eth_stats = result["ETH"]
        assert eth_stats["count"] == 1
        assert eth_stats["total_flows"] == 25000000
        assert eth_stats["total_aum"] == 500000000

    def test_safe_float_parse(self):
        """Test safe float parsing with various inputs."""
        # Valid numbers
        assert _safe_float_parse(42.5) == 42.5
        assert _safe_float_parse("42.5") == 42.5
        assert _safe_float_parse(100) == 100.0

        # Invalid/None values
        assert _safe_float_parse(None) is None
        assert _safe_float_parse("") is None
        assert _safe_float_parse("nan") is None
        assert _safe_float_parse("NaN") is None
        assert _safe_float_parse("null") is None
        assert _safe_float_parse(float("nan")) is None
        assert _safe_float_parse(float("inf")) is None

        # Edge cases
        assert _safe_float_parse("  42.5  ") == 42.5  # Whitespace
        assert _safe_float_parse(0) == 0.0
        assert _safe_float_parse(-42.5) == -42.5
