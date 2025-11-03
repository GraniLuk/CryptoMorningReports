"""Utility functions for the Crypto Morning Reports application."""


def clean_symbol(symbol: str) -> str:
    """Clean and validate trading symbol string.

    Args:
        symbol (str): Trading symbol like 'BTCUSDT'
    Returns:
        str: Cleaned symbol string

    """
    if not symbol:
        return ""
    symbol = symbol.replace("-USDT", "")
    symbol = symbol.replace("-USD", "")
    symbol = symbol.replace("USDT", "")
    return symbol.replace("USD", "")
