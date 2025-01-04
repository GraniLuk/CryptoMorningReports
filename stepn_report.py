from sharedCode.commonPrice import TickerPrice
from sharedCode.binance import fetch_binance_price
from prettytable import PrettyTable
from telegram_logging_handler import app_logger
from sql_connection import Symbol, connect_to_sql, save_stepn_results
from pycoingecko import CoinGeckoAPI

def fetch_stepn_report(conn) -> PrettyTable:
    symbols = [
    Symbol(symbol_id=1, symbol_name='GMT', full_name='STEPN Token'),
    Symbol(symbol_id=2, symbol_name='GST', full_name='green-satoshi-token-bsc')
    ]
    results = []
    
    try:
        gmt_price = fetch_binance_price(symbols[0])
        results.append(gmt_price)
    except Exception as e:
        app_logger.error(f"Unexpected error for GMT: {str(e)}")
        raise
    
    try: 
        gst_price = fetch_coingecko_price(symbols[1])
        results.append(gst_price)
    except Exception as e:
        app_logger.error(f"Unexpected error for GST: {str(e)}")
        raise
             
    # Calculate ratio
    gmt_gst_ratio = results[0].last/results[1].last
    
    # Save results to database
    try:
        save_stepn_results(conn, results[0].last, results[1].last, gmt_gst_ratio)
    except Exception as e:
        app_logger.error(f"Error saving STEPN results to database: {str(e)}")
    
    # Create table for display
    stepn_table = PrettyTable()
    stepn_table.field_names = ["Symbol", "Current Price"]

    results.append(TickerPrice(symbol='GMT/GST', low=0, high=0, last=gmt_gst_ratio))

    # Store rows with range calculation
    range_rows = []
    for result in results:
        symbol = result.symbol
        last = result.last
        range_rows.append((symbol, last))

    for row in range_rows:
        stepn_table.add_row(row)
    return stepn_table

def fetch_coingecko_price(symbol: Symbol) -> TickerPrice:
    """Fetch current price from CoinGecko API and return as BinancePrice object"""
    try:
        cg = CoinGeckoAPI()
        price_data = cg.get_price(ids=symbol.full_name, vs_currencies='usd')
        return TickerPrice(
            symbol=symbol.symbol_name,
            low=price_data[symbol.full_name]['usd'],
            high=price_data[symbol.full_name]['usd'],
            last=price_data[symbol.full_name]['usd']
        )
    except Exception as e:
        app_logger.error(f"Error fetching price from CoinGecko: {e}")
        raise

if __name__ == "__main__":
    fetch_stepn_report()