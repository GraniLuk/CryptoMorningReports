"""
Mock data provider for local development without database access.
This allows running reports using cached/mock data when the database is unavailable.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional


# Mock Symbol class to match the real one
class MockSymbol:
    def __init__(self, symbol_id, symbol_name):
        self.symbol_id = symbol_id
        self.symbol_name = symbol_name
        self.id = symbol_id  # Alias for compatibility


# Mock Candle class
class MockCandle:
    def __init__(self, symbol_id, end_date, open_price, high, low, close, volume):
        self.id = symbol_id
        self.end_date = end_date
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


# Define mock symbols - add/modify as needed
MOCK_SYMBOLS = [
    MockSymbol(1, "BTC"),
    MockSymbol(2, "ETH"),
    MockSymbol(3, "XRP"),
    MockSymbol(4, "SOL"),
    MockSymbol(5, "ATOM"),
    MockSymbol(6, "DOT"),
    MockSymbol(7, "LINK"),
    MockSymbol(8, "DOGE"),
    MockSymbol(9, "TON"),
    MockSymbol(10, "HBAR"),
    MockSymbol(11, "OSMO"),
    MockSymbol(12, "VIRTUAL"),
]


def get_mock_symbols() -> List[MockSymbol]:
    """Return list of mock symbols."""
    logging.info("Using mock symbols (database unavailable)")
    return MOCK_SYMBOLS


def generate_mock_candles(symbol: MockSymbol, hours: int = 24) -> List[MockCandle]:
    """
    Generate mock candle data for a symbol.
    This creates realistic-looking price data for testing.
    """
    candles = []
    now = datetime.now(timezone.utc)

    # Base prices for different symbols
    base_prices = {
        "BTC": 108000.0,
        "ETH": 3900.0,
        "XRP": 2.45,
        "SOL": 190.0,
        "ATOM": 3.25,
        "DOT": 3.05,
        "LINK": 18.0,
        "DOGE": 0.195,
        "TON": 2.20,
        "HBAR": 0.175,
        "OSMO": 0.125,
        "VIRTUAL": 0.78,
    }

    base_price = base_prices.get(symbol.symbol_name, 100.0)

    for i in range(hours):
        end_date = now - timedelta(hours=hours - i)

        # Simulate some price movement
        variation = 0.02  # 2% max variation per hour
        import random

        change = random.uniform(-variation, variation)

        close_price = base_price * (1 + change)
        open_price = base_price
        high_price = max(open_price, close_price) * 1.005
        low_price = min(open_price, close_price) * 0.995
        volume = random.uniform(1000, 5000)

        candle = MockCandle(
            symbol_id=symbol.symbol_id,
            end_date=end_date,
            open_price=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )
        candles.append(candle)

        # Update base price for next candle
        base_price = close_price

    return candles


def get_mock_aggregated_data() -> List[dict]:
    """
    Return mock aggregated indicator data.
    This simulates the data from get_aggregated_data().
    """
    logging.info("Using mock aggregated data (database unavailable)")

    mock_data = []
    for symbol in MOCK_SYMBOLS:
        # Generate some realistic RSI, MA, EMA values
        import random

        data = {
            "symbol": symbol.symbol_name,
            "rsi": random.uniform(25, 75),
            "close": random.uniform(100, 50000)
            if symbol.symbol_name == "BTC"
            else random.uniform(0.1, 5000),
            "ma50": random.uniform(100, 52000),
            "ma200": random.uniform(95, 51000),
            "ema50": random.uniform(100, 52000),
            "ema200": random.uniform(95, 51000),
            "low": random.uniform(90, 49000),
            "high": random.uniform(105, 53000),
            "range_pct": random.uniform(2, 15),
        }
        mock_data.append(data)

    return mock_data


def format_mock_aggregated_data() -> str:
    """Format mock aggregated data as a table string."""
    data = get_mock_aggregated_data()

    header = (
        "Symbol | RSI | Close | MA50 | MA200 | EMA50 | EMA200 | Low | High | Range%\n"
    )
    header += (
        "-------|-----|-------|------|-------|-------|--------|-----|------|-------\n"
    )

    rows = []
    for item in data:
        row = f"{item['symbol']:>6} | {item['rsi']:.2f} | {item['close']:.2f} | {item['ma50']:.2f} | "
        row += f"{item['ma200']:.2f} | {item['ema50']:.2f} | {item['ema200']:.2f} | "
        row += f"{item['low']:.2f} | {item['high']:.2f} | {item['range_pct']:.2f}"
        rows.append(row)

    return header + "\n".join(rows)


# Mock connection class
class MockConnection:
    """Mock database connection that does nothing."""

    def __init__(self):
        logging.warning("Using MOCK database connection - no real database access")

    def close(self):
        pass

    def cursor(self):
        return None

    def commit(self):
        pass


def get_mock_connection():
    """Return a mock database connection."""
    return MockConnection()


# You can add more mock data functions as needed
def get_mock_current_prices():
    """Return mock current prices for symbols."""
    import random

    prices = {}
    for symbol in MOCK_SYMBOLS:
        base_prices = {
            "BTC": 108000,
            "ETH": 3900,
            "XRP": 2.45,
            "SOL": 190,
        }
        base = base_prices.get(symbol.symbol_name, 100)
        prices[symbol.symbol_name] = {
            "last": base * random.uniform(0.98, 1.02),
            "low_24h": base * 0.95,
            "high_24h": base * 1.05,
        }

    return prices
