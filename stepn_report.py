from sharedCode.commonPrice import TickerPrice
from sharedCode.binance import fetch_binance_price
from prettytable import PrettyTable
from stepn_repository import save_stepn_results, fetch_stepn_results_last_14_days
from telegram_logging_handler import app_logger
from sql_connection import Symbol
from pycoingecko import CoinGeckoAPI
import pandas as pd

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

    last_14_days_results = fetch_stepn_results_last_14_days(conn)
    ratios = [record[2] for record in last_14_days_results]  # Extracting ratios separately
    ratios.append(gmt_gst_ratio)

    ema14_results = calculate_ema14(ratios)
    
    # Save results to database
    try:
        save_stepn_results(conn, results[0].last, results[1].last, gmt_gst_ratio, ema14_results[-1])
    except Exception as e:
        app_logger.error(f"Error saving STEPN results to database: {str(e)}")
    
    # Create table for display
    stepn_table = PrettyTable()
    stepn_table.field_names = ["Symbol", "Current Price"]

    results.append(TickerPrice(symbol='GMT/GST', low=0, high=0, last=gmt_gst_ratio))
    results.append(TickerPrice(symbol='EMA14', low=0, high=0, last=ema14_results[-1]))

    # Store rows with range calculation
    range_rows = []
    for result in results:
        symbol = result.symbol
        last = result.last
        range_rows.append((symbol, last))

    for row in range_rows:
        stepn_table.add_row(row)
    return stepn_table

def calculate_ema14(ratios):
        """
        Calculates the 14-day Exponential Moving Average (EMA) for the ratio column using pandas.

        Args:
            ratios (list of float): List of ratio values.

        Returns:
            list: EMA14 values for the provided ratios.
        """
        if not ratios:
            return []

        df = pd.DataFrame(ratios, columns=["Ratio"])
        df["EMA14"] = df["Ratio"].ewm(span=14, adjust=False).mean()

        return df["EMA14"].tolist()

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