from kucoin import Client as KucoinClient
from collections import namedtuple
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from prettytable import PrettyTable
from KUCOIN_SYMBOLS import KUCOIN_SYMBOLS
from configuration import get_kucoin_credentials
from telegram_logging_handler import app_logger
from typing import List
from sql_connection import Symbol

# Define namedtuple for price data
BinancePrice = namedtuple('BinancePrice', ['symbol', 'low', 'high'])

def fetch_kucoin_price(symbol : Symbol, api_key, api_secret, api_passphrase):
    """Fetch price data from Kucoin exchange."""
    # Initialize the client
    client = KucoinClient(api_key, api_secret, api_passphrase)
    try:           
        # Get 24hr stats
        ticker = client.get_24hr_stats(symbol.kucoin_name)
        
        return BinancePrice(
            symbol=symbol.symbol_name,
            low=float(ticker['low']),
            high=float(ticker['high'])
        )
    except Exception as e:
        app_logger.error(f"Kucoin error for {symbol}: {str(e)}")
        return None
    
def fetch_binance_price(symbol : Symbol) -> BinancePrice:
    """Fetch price data from Binance exchange."""
    # Initialize the client
    client = BinanceClient()
    try:
        # Get 24hr stats
        ticker = client.get_ticker(symbol=symbol.binance_name)
        
        return BinancePrice(
            symbol=symbol.symbol_name,
            low=float(ticker['lowPrice']),
            high=float(ticker['highPrice'])
        )
    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return None

def fetch_range_price(symbols : List[Symbol]) -> PrettyTable:
    results = []
    kucoin_credentials = get_kucoin_credentials()
    
    for symbol in symbols:
        try:
            # Check if symbol should be fetched from Kucoin
            if (symbol.symbol_name in KUCOIN_SYMBOLS):
                price_data = fetch_kucoin_price(
                    symbol,
                    kucoin_credentials['api_key'],
                    kucoin_credentials['api_secret'],
                    kucoin_credentials['api_passphrase']
                )
                if price_data:
                    results.append(price_data)
                continue
                
            # Regular Binance fetch
            price_data = fetch_binance_price(symbol)
            results.append(price_data)
            
        except BinanceAPIException as e:
            app_logger.error(f"Error fetching {symbol.symbol_name}: {e.message}")
        except Exception as e:
            app_logger.error(f"Unexpected error for {symbol.symbol_name}: {str(e)}")
    
    range_table = PrettyTable()
    range_table.field_names = ["Symbol", "24h Low", "24h High", "Range %"]

    # Sort by price range descending 
    sorted_results = sorted(results, key=lambda x: ((x.high - x.low) / x.low) * 100, reverse=True)
    # Store rows with range calculation
    range_rows = []
    for result in sorted_results:
        symbol = result.symbol
        high = result.high
        low = result.low
        price_range = ((high - low) / low) * 100
        price_range_percent = f"{price_range:.2f}%"
        range_rows.append((symbol, low, high, price_range_percent))

    for row in range_rows:
        range_table.add_row(row)
    return range_table

if __name__ == "__main__":
    fetch_range_price()
