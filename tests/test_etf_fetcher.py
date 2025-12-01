"""Integration tests for ETF fetcher functionality."""

from unittest.mock import patch

from etf.etf_fetcher import (
    _safe_float_parse,
    fetch_etf_data,
    get_etf_summary_stats,
    parse_etf_data,
)


class TestETFFetcher:
    """Test cases for ETF fetcher functions."""

    @patch("etf.etf_fetcher.scrape_defillama_etf")
    def test_fetch_etf_data_success(self, mock_scrape):
        """Test successful API fetch from DefiLlama."""
        # Mock successful response from DefiLlama scraper
        mock_data = [
            {
                "Ticker": "IBIT",
                "Coin": "BTC",
                "Issuer": "Blackrock",
                "Price": None,
                "AUM": 81884166749.0,
                "Flows": 0.0,
                "FlowsChange": None,
                "Volume": 1876045860.0,
                "Date": 1762959436,
            },
            {
                "Ticker": "BTC_TOTAL",
                "Coin": "BTC",
                "Issuer": "Total",
                "Price": None,
                "AUM": 112046212026.0,
                "Flows": 524000000.0,
                "FlowsChange": None,
                "Volume": 0.0,
                "Date": 1762959436,
            },
        ]

        mock_scrape.return_value = mock_data

        result = fetch_etf_data()

        assert result is not None
        assert len(result) == 2
        # Find IBIT and BTC_TOTAL in results
        ibit = next((r for r in result if r["Ticker"] == "IBIT"), None)
        btc_total = next((r for r in result if r["Ticker"] == "BTC_TOTAL"), None)
        assert ibit is not None
        assert btc_total is not None
        assert ibit["AUM"] == 81884166749.0
        assert btc_total["Flows"] == 524000000.0

    @patch("etf.etf_fetcher.fetch_yfinance_etf_data")
    @patch("etf.etf_fetcher.scrape_defillama_etf")
    def test_fetch_etf_data_http_error(self, mock_scrape, mock_yfinance):
        """Test API fetch with error - should fallback to YFinance."""
        # Simulate DefiLlama scraper raising an exception
        mock_scrape.side_effect = Exception("Scraping error")

        # Mock YFinance fallback returning None (also failed)
        mock_yfinance.return_value = None

        result = fetch_etf_data()

        # Should return None when both sources fail
        assert result is None
        # Verify YFinance fallback was attempted
        mock_yfinance.assert_called_once()

    @patch("etf.etf_fetcher.fetch_yfinance_etf_data")
    @patch("etf.etf_fetcher.scrape_defillama_etf")
    def test_fetch_etf_data_timeout(self, mock_scrape, mock_yfinance):
        """Test API fetch with timeout - should fallback to YFinance."""
        mock_scrape.side_effect = Exception("Timeout")

        # Mock YFinance fallback returning None (also failed)
        mock_yfinance.return_value = None

        result = fetch_etf_data()

        # Should return None when both sources fail
        assert result is None
        # Verify YFinance fallback was attempted
        mock_yfinance.assert_called_once()

    @patch("etf.etf_fetcher.fetch_yfinance_etf_data")
    @patch("etf.etf_fetcher.scrape_defillama_etf")
    def test_fetch_etf_data_invalid_json(self, mock_scrape, mock_yfinance):
        """Test API fetch with invalid data - should return None."""
        # Simulate scraper returning None
        mock_scrape.return_value = None
        # Mock YFinance fallback also returning None
        mock_yfinance.return_value = None

        result = fetch_etf_data()

        # Should return None when both sources fail
        assert result is None
        # Verify YFinance fallback was attempted
        mock_yfinance.assert_called_once()

    @patch("etf.etf_fetcher.scrape_defillama_etf")
    def test_fetch_defillama_etf_data_empty_response(self, mock_scrape):
        """Test API fetch with empty response."""
        mock_scrape.return_value = []

        result = fetch_etf_data()

        # Empty list means successful scrape but no data - should return None
        assert result is None

    def test_parse_etf_data(self, subtests):
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

        # Test coin presence
        with subtests.test(msg="BTC coin presence"):
            assert "BTC" in result
        with subtests.test(msg="ETH coin presence"):
            assert "ETH" in result
        with subtests.test(msg="BTC ETF count"):
            assert len(result["BTC"]) == 2
        with subtests.test(msg="ETH ETF count"):
            assert len(result["ETH"]) == 1

        # Check each BTC ETF independently
        btc_etfs = result["BTC"]
        for ticker in ["IBIT", "FBTC"]:
            with subtests.test(ticker=ticker, coin="BTC"):
                etf = next((e for e in btc_etfs if e["ticker"] == ticker), None)
                assert etf is not None, f"ETF {ticker} not found"
                assert etf["coin"] == "BTC"
                if ticker == "IBIT":
                    assert etf["issuer"] == "BlackRock"
                    assert etf["price"] == 42.50
                    assert etf["flows"] == 50000000
                    assert etf["fetch_date"] == "2024-01-15"
                elif ticker == "FBTC":
                    assert etf["issuer"] == "Fidelity"
                    assert etf["flows"] == 30000000

        # Check ETH ETF
        with subtests.test(ticker="ETHE", coin="ETH"):
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

    def test_safe_float_parse(self, subtests):
        """Test safe float parsing with various inputs."""
        # Valid numbers
        valid_cases = [
            (42.5, 42.5, "float"),
            ("42.5", 42.5, "string"),
            (100, 100.0, "int"),
            ("  42.5  ", 42.5, "whitespace"),
            (0, 0.0, "zero"),
            (-42.5, -42.5, "negative"),
        ]
        for input_val, expected, desc in valid_cases:
            with subtests.test(input=input_val, desc=desc):
                assert _safe_float_parse(input_val) == expected

        # Invalid/None values
        invalid_cases = [
            (None, "None"),
            ("", "empty string"),
            ("nan", "nan string"),
            ("NaN", "NaN string"),
            ("null", "null string"),
            (float("nan"), "nan float"),
            (float("inf"), "inf float"),
        ]
        for input_val, desc in invalid_cases:
            with subtests.test(input=input_val, desc=desc):
                assert _safe_float_parse(input_val) is None
