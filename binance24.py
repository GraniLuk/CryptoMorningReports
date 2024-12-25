from collections import namedtuple
from binance.client import Client
from binance.exceptions import BinanceAPIException
from prettytable import PrettyTable
from utils import clean_symbol_binance, convert_to_binance_symbol

# Define namedtuple for price data
BinancePrice = namedtuple('BinancePrice', ['symbol', 'low', 'high'])

def fetch_range_price(symbols=["BTCUSDT"]):
    # Initialize Binance client (no auth needed for public endpoints)
    client = Client()
    
    results = []
    for symbol in symbols:
        try:
            # Convert symbol format
            symbol = convert_to_binance_symbol(symbol)
            
            # Get 24hr ticker price change statistics
            ticker = client.get_ticker(symbol=symbol)
            
            # Create namedtuple instance
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
        symbol = clean_symbol_binance(result.symbol)
        high = result.high
        low = result.low
        price_range = ((high - low) / low) * 100
        price_range_percent = f"{price_range:.2f}%"
        range_rows.append((clean_symbol_binance(symbol), low, high, price_range_percent)) 

    for row in range_rows:
        range_table.add_row(row)
    return range_table

if __name__ == "__main__":
    fetch_range_price()
