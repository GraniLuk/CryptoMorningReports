from datetime import datetime, timedelta
from configuration import get_kucoin_credentials
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
    
def fetch_daily_ranges(symbol: str, start_date: str, end_date: str, api_key, api_secret, api_passphrase):
    """
    Fetches the daily high and low prices for a given symbol within a date range.

    Args:
        symbol (str): Trading pair symbol (e.g., 'BTC-USDT').
        start_date (str): Start date in the format 'YYYY-MM-DD'.
        end_date (str): End date in the format 'YYYY-MM-DD'.

    Returns:
        list of dict: A list containing date, high, and low prices for each day.
    """
    client = KucoinClient(api_key, api_secret, api_passphrase)
    date_ranges = []
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    while current_date <= end_date:
        start_time = int(current_date.timestamp() * 1000)
        end_time = int((current_date + timedelta(days=1)).timestamp() * 1000)

        candles = client.get_kline_data(symbol, "1day", startAt=start_time // 1000, endAt=end_time // 1000)
        if candles:
            # KuCoin returns data in [time, open, close, high, low, volume, turnover] format
            _, _, _, high, low, _, _ = candles[0]
            date_ranges.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "high": float(high),
                "low": float(low)
            })

        current_date += timedelta(days=1)

    return date_ranges

if __name__ == "__main__":
    symbol = "KCS-USDT"  # Specify the trading pair
    start_date = "2025-01-11"  # Start date (YYYY-MM-DD)
    end_date = "2025-01-14"    # End date (YYYY-MM-DD)
    kucoin_credentials = get_kucoin_credentials()
    kucoin_credentials['api_key'],
    kucoin_credentials['api_secret'],
    kucoin_credentials['api_passphrase']

    daily_ranges = fetch_daily_ranges(symbol, start_date, end_date)
    for day_range in daily_ranges:
        print(f"Date: {day_range['date']}, High: {day_range['high']}, Low: {day_range['low']}")