"""Common data structures for cryptocurrency price and candle data."""

from collections import namedtuple
from dataclasses import dataclass


TickerPrice = namedtuple(
    "TickerPrice", ["source", "symbol", "low", "high", "last", "volume", "volume_quote"],
)


@dataclass
class Candle:
    """Represents a candlestick data point for a cryptocurrency symbol."""

    symbol: str
    source: int
    end_date: str
    close: float
    high: float
    low: float
    last: float
    volume: float
    volume_quote: float
    open: float | None = None
    id: int | None = None
