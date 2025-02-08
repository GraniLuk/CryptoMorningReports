from telegram import Bot


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


# Mapping of yfinance to binance symbols
YFINANCE_TO_BINANCE = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "XRP-USD": "XRPUSDT",
    "ATOM-USD": "ATOMUSDT",
    "DOT-USD": "DOTUSDT",
    "HBAR-USD": "HBARUSDT",
    "KCS-USD": "KCSUSDT",
    "FLOW-USD": "FLOWUSDT",
    "POL-USD": "POLUSDT",
    "AKT-USD": "AKTUSDT",
    "NEXO-USD": "NEXOUSDT",
    "DYM-USD": "DYMUSDT",
    "OSMO-USD": "OSMOUSDT",
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


async def send_telegram_message(telegram_token, chat_id, message):
    bot = Bot(token=telegram_token)
    async with bot:  # This handles cleanup automatically
        await bot.send_message(chat_id=chat_id.strip(), text=message)
