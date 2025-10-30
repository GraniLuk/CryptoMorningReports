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


async def send_telegram_message(telegram_token, chat_id, message):
    bot = Bot(token=telegram_token)
    async with bot:  # This handles cleanup automatically
        await bot.send_message(chat_id=chat_id.strip(), text=message)
