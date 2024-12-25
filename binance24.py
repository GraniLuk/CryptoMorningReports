from collections import namedtuple
import requests
import json
from prettytable import PrettyTable
from utils import clean_symbol_binance, convert_to_binance_symbol

# Define namedtuple for price data
BinancePrice = namedtuple('BinancePrice', ['symbol', 'low', 'high'])

def fetch_range_price(symbols=["BTCUSDT"]):
    # Binance API endpoint
    url = "https://api.binance.com/api/v3/ticker/24hr"
    
    results = []
    for symbol in symbols:
        # Parameters for the request
        symbol = convert_to_binance_symbol(symbol)
        params = {
            "symbol": symbol
        }
        
        try:
            # Make the GET request
            response = requests.get(url, params=params)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = json.loads(response.text)
                
                # Create namedtuple instance
                price_data = BinancePrice(
                    symbol=symbol,
                    low=float(data['lowPrice']),
                    high=float(data['highPrice']),
                )
                
                results.append(price_data)
                
                # Print the results
                print(f"{symbol} 24h Low Price: ${price_data.low:,.2f}")
                print(f"{symbol} 24h High Price: ${price_data.high:,.2f}")
            else:
                print(f"Error: Unable to fetch data for {symbol}. Status code: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {symbol}: {e}")
        except json.JSONDecodeError:
            print(f"Error: Unable to parse JSON response for {symbol}")
        except KeyError:
            print(f"Error: Required data not found in response for {symbol}")
    
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
