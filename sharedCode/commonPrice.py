from collections import namedtuple

TickerPrice = namedtuple(
    "TickerPrice", ["source", "symbol", "low", "high", "last", "volume", "volume_quote"]
)


class Candle:
    def __init__(
        self,
        symbol: str,
        source: int,
        end_date,
        open: float,
        close: float,
        high: float,
        low: float,
        last: float,
        volume: float,
        volume_quote: float,
        id: int = None,
    ):
        self.symbol = symbol
        self.source = source
        self.end_date = end_date
        self.open = open
        self.close = close
        self.high = high
        self.low = low
        self.last = last
        self.volume = volume
        self.volume_quote = volume_quote
        self.id = id
