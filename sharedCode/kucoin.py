from sql_connection import Symbol
from sharedCode.commonPrice import TickerPrice
from kucoin import Client as KucoinClient
from telegram_logging_handler import app_logger


def fetch_kucoin_price(symbol : Symbol, api_key, api_secret, api_passphrase):
    """Fetch price data from Kucoin exchange."""
    # Initialize the client
    client = KucoinClient(api_key, api_secret, api_passphrase)
    try:           
        # Get 24hr stats
        ticker = client.get_24hr_stats(symbol.kucoin_name)
        
        return TickerPrice(
            symbol=symbol.symbol_name,
            low=float(ticker['low']),
            high=float(ticker['high']),
            last=float(ticker['last'])
        )
    except Exception as e:
        app_logger.error(f"Kucoin error for {symbol}: {str(e)}")
        return None