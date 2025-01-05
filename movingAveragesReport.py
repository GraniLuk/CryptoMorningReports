from collections import namedtuple
import yfinance as yf
from prettytable import PrettyTable
from moving_averages_repository import save_moving_averages_results
from telegram_logging_handler import app_logger
from sql_connection import Symbol
from typing import List

def create_average_table(symbols: List[Symbol], conn) -> PrettyTable:
    all_values = []
    CryptoData = namedtuple('CryptoData', ['symbol', 'current_price', 'ma50', 'ma200'])

    for symbol in symbols:
        try:
            app_logger.info('Processing symbol: %s', symbol.symbol_name)
            ticker = yf.Ticker(symbol.yf_name)
            df = ticker.history(interval="1d", period="max")
            app_logger.info('Retrieved %d data points for %s', len(df), symbol.symbol_name)
            
            df['MA50'] = df['Close'].rolling(window=50).mean()
            today_MA50 = round(df['MA50'].iloc[-1], 3)
            
            df['MA200'] = df['Close'].rolling(window=200).mean()
            today_MA200 = round(df['MA200'].iloc[-1], 3)
            
            today_price = round(df['Close'].iloc[-1], 3)
            
            # Store the results
            all_values.append(CryptoData(
                symbol=symbol.symbol_name,
                current_price=today_price,
                ma50=today_MA50,
                ma200=today_MA200
            ))
            
            # Save to database if connection is available
            if conn:
                try:
                    save_moving_averages_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        current_price=today_price,
                        ma50=today_MA50,
                        ma200=today_MA200
                    )
                except Exception as e:
                    app_logger.error(f"Failed to save moving averages results for {symbol.symbol_name}: {str(e)}")
                    
        except Exception as e:
            app_logger.error('Error processing symbol %s: %s', symbol.symbol_name, str(e))

    average_table = PrettyTable()
    average_table.field_names = ["Symbol", "Current", "MA50", "MA200"]

    for row in all_values:
        symbol = row.symbol
        price = row.current_price
        ma50 = row.ma50
        ma200 = row.ma200
        average_table.add_row([symbol, price, ma50, ma200])

    return average_table