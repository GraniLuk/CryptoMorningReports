from collections import namedtuple

TickerPrice = namedtuple('TickerPrice', ['source','symbol', 'low', 'high', 'last', 'volume', 'volume_quote'])