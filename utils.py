def clean_symbol(symbol: str) -> str:
    """Clean and validate trading symbol string.
    
    Args:
        symbol (str): Trading symbol like 'BTCUSDT'
    Returns:
        str: Cleaned symbol string
    """
    if not symbol:
        return ""
    return symbol.strip().upper()

def clean_symbol_binance(symbol: str) -> str:
    """Remove USDT suffix from binance symbol.
    
    Args:
        symbol (str): Symbol with USDT (e.g. 'BTCUSDT')
    Returns:
        str: Clean symbol (e.g. 'BTC')
    """
    if not symbol:
        return ""
    return symbol.replace("USDT", "")

# Mapping of yfinance to binance symbols
YFINANCE_TO_BINANCE = {
    'BTC-USD': 'BTCUSDT',
    'ETH-USD': 'ETHUSDT',
    'XRP-USD': 'XRPUSDT',
    'ATOM-USD': 'ATOMUSDT',
    'DOT-USD': 'DOTUSDT',
    'HBAR-USD': 'HBARUSDT',
    'KCS-USD': 'KCSUSDT',
    'FLOW-USD': 'FLOWUSDT',
    'POL-USD': 'POLUSDT',
    'AKT-USD': 'AKTUSDT',
    'NEXO-USD': 'NEXOUSDT',
    'DYM-USD': 'DYMUSDT',
    'OSMO-USD': 'OSMOUSDT'
}

def convert_to_binance_symbol(yfinance_symbol: str) -> str:
    """Convert yfinance symbol format to binance format.
    
    Args:
        yfinance_symbol (str): Symbol in yfinance format (e.g. 'BTC-USD')
    Returns:
        str: Symbol in binance format (e.g. 'BTCUSDT')
    Raises:
        KeyError: If symbol mapping is not found
    """
    try:
        return YFINANCE_TO_BINANCE[yfinance_symbol]
    except KeyError:
        raise KeyError(f"No binance symbol mapping found for {yfinance_symbol}")