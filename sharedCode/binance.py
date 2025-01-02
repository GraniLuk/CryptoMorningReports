# Define namedtuple for price data
from datetime import datetime, timedelta
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
import pandas as pd
from sql_connection import Symbol
from telegram_logging_handler import app_logger
from sharedCode.commonPrice import TickerPrice


def fetch_binance_price(symbol : Symbol) -> TickerPrice:
    """Fetch price data from Binance exchange."""
    # Initialize the client
    client = BinanceClient()
    try:
        # Get 24hr stats
        ticker = client.get_ticker(symbol=symbol.binance_name)
        
        return TickerPrice(
            symbol=symbol.symbol_name,
            low=float(ticker['lowPrice']),
            high=float(ticker['highPrice']),
            last=float(ticker['lastPrice'])
        )
    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return None
    
def fetch_close_prices_from_Binance(symbol: str, lookback_days: int = 14) -> pd.DataFrame:
    client = BinanceClient()
    
    try:
        start_time = datetime.now() - timedelta(days=lookback_days)
        
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            start_str=start_time.strftime('%d %b %Y'),
            limit=lookback_days
        )
        
        # Create DataFrame with numeric types
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 
            'volume', 'close_time', 'quote_volume', 
            'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Convert price columns to float
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except BinanceAPIException as e:
        app_logger.error(f"Error fetching data for {symbol}: {e.message}")
        return pd.DataFrame()
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return pd.DataFrame()