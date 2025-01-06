from collections import namedtuple
import yfinance as yf
from prettytable import PrettyTable
from moving_averages_repository import save_moving_averages_results, fetch_yesterday_moving_averages
from telegram_logging_handler import app_logger
from sql_connection import Symbol
from typing import List

def create_average_table(symbols: List[Symbol], conn) -> PrettyTable:
    all_values = []
    CryptoData = namedtuple('CryptoData', ['symbol', 'current_price', 'ma50', 'ma200', 'ma50_status', 'ma200_status'])
    yesterdayValues = fetch_yesterday_moving_averages(conn)

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
            
            # Initialize status indicators with colored circles
            ma50_status = "🟢" if today_price > today_MA50 else "🔴"
            ma200_status = "🟢" if today_price > today_MA200 else "🔴"
            
            # Check for MA crossovers if we have yesterday's data
            if not yesterdayValues.empty:
                yesterday_data = yesterdayValues[yesterdayValues['SymbolName'] == symbol.symbol_name]
                if not yesterday_data.empty:
                    yesterday_price = yesterday_data['CurrentPrice'].iloc[0]
                    yesterday_ma50 = yesterday_data['MA50'].iloc[0]
                    yesterday_ma200 = yesterday_data['MA200'].iloc[0]
                    
                    # Update MA50 status with alert if crossed
                    if yesterday_price < yesterday_ma50 and today_price > today_MA50:
                        ma50_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above MA50")
                    elif yesterday_price > yesterday_ma50 and today_price < today_MA50:
                        ma50_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below MA50")
                    
                    # Update MA200 status with alert if crossed
                    if yesterday_price < yesterday_ma200 and today_price > today_MA200:
                        ma200_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above MA200")
                    elif yesterday_price > yesterday_ma200 and today_price < today_MA200:
                        ma200_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below MA200")
            
            # Store the results
            all_values.append(CryptoData(
                symbol=symbol.symbol_name,
                current_price=today_price,
                ma50=today_MA50,
                ma200=today_MA200,
                ma50_status=ma50_status,
                ma200_status=ma200_status
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
    average_table.field_names = ["Symbol", "Current", "MA50", "MA50 Status", "MA200", "MA200 Status"]

    for row in all_values:
        average_table.add_row([
            row.symbol,
            row.current_price,
            row.ma50,
            row.ma50_status,
            row.ma200,
            row.ma200_status
        ])

    return average_table