from collections import namedtuple

TickerPrice = namedtuple(
    "TickerPrice", ["source", "symbol", "low", "high", "last", "volume", "volume_quote"]
)

Candle = namedtuple(
    "Candle",
    [
        "symbol",
        "end_date",
        "source",
        "open",
        "close",
        "low",
        "high",
        "last",
        "volume",
        "volume_quote",
    ],
)
