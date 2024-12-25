from kucoin import Client as KucoinClient
from collections import namedtuple
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from prettytable import PrettyTable
from utils import clean_symbol, convert_to_binance_symbol
from function_app import get_kucoin_credentials

# Define constants
KUCOIN_SYMBOLS = {'AKT-USD', 'KCS-USD'}

# Define namedtuple for price data
BinancePrice = namedtuple('BinancePrice', ['symbol', 'low', 'high'])

def fetch_kucoin_price(symbol, api_key, api_secret, api_passphrase):
    """Fetch price data from Kucoin exchange."""
    # Initialize the client
    client = KucoinClient(api_key, api_secret, api_passphrase)
    try:           
        # Get 24hr stats
        ticker = client.get_24hr_stats(symbol)
        
        return BinancePrice(
            symbol=symbol,
            low=float(ticker['low']),
            high=float(ticker['high'])
        )
    except Exception as e:
        print(f"Kucoin error for {symbol}: {str(e)}")
        return None

def fetch_range_price(symbols=["AKT-USDT"]):
    results = []
    binance_client = BinanceClient()
    kucoin_credentials = get_kucoin_credentials()
    
    for symbol in symbols:
        try:
            # Check if symbol should be fetched from Kucoin
            if (symbol in KUCOIN_SYMBOLS):
                symbol = symbol.replace("-USD", "-USDT")
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
            symbol = convert_to_binance_symbol(symbol)
            ticker = binance_client.get_ticker(symbol=symbol)
            
            price_data = BinancePrice(
                symbol=symbol,
                low=float(ticker['lowPrice']),
                high=float(ticker['highPrice'])
            )
            results.append(price_data)
            
        except BinanceAPIException as e:
            print(f"Error fetching {symbol}: {e.message}")
        except Exception as e:
            print(f"Unexpected error for {symbol}: {str(e)}")
    
    range_table = PrettyTable()
    range_table.field_names = ["Symbol", "24h Low", "24h High", "Range %"]

    # Sort by price range descending 
    sorted_results = sorted(results, key=lambda x: ((x.high - x.low) / x.low) * 100, reverse=True)
    # Store rows with range calculation
    range_rows = []
    for result in sorted_results:
        symbol = clean_symbol(result.symbol)
        high = result.high
        low = result.low
        price_range = ((high - low) / low) * 100
        price_range_percent = f"{price_range:.2f}%"
        range_rows.append((clean_symbol(symbol), low, high, price_range_percent)) 

    for row in range_rows:
        range_table.add_row(row)
    return range_table

if __name__ == "__main__":
    fetch_range_price()
