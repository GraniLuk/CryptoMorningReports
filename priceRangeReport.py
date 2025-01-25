from priceRangeRepository import save_price_range_results
from sharedCode.binance import fetch_binance_price
from prettytable import PrettyTable
from configuration import get_kucoin_credentials
from sharedCode.kucoin import fetch_kucoin_price
from telegram_logging_handler import app_logger
from typing import List
from source_repository import SourceID, Symbol


def fetch_range_price(symbols : List[Symbol], conn) -> PrettyTable:
    results = []
    kucoin_credentials = get_kucoin_credentials()
    
    for symbol in symbols:
        try:
            # Check if symbol should be fetched from Kucoin
            if (symbol.source_id == SourceID.KUCOIN):
                price_data = fetch_kucoin_price(
                    symbol,
                    kucoin_credentials['api_key'],
                    kucoin_credentials['api_secret'],
                    kucoin_credentials['api_passphrase']
                )
                if price_data:
                    results.append(price_data)
            else:
                # Regular Binance fetch
                price_data = fetch_binance_price(symbol)
                results.append(price_data)
            
            # Save to database if connection is available
            if conn and price_data:
                try:
                    price_range_percent = ((price_data.high - price_data.low) / price_data.low) * 100
                    save_price_range_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        low_price=price_data.low,
                        high_price=price_data.high,
                        range_percent=price_range_percent
                    )
                except Exception as e:
                    app_logger.error(f"Failed to save price range results for {symbol.symbol_name}: {str(e)}")
            
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
