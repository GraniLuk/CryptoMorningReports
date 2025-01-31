from typing import List
from sharedCode.priceChecker import fetch_close_prices
from technical_analysis.rsi_repository import save_rsi_results
import pandas as pd
from prettytable import PrettyTable
from infra.telegram_logging_handler import app_logger
from source_repository import Symbol

def calculate_rsi(series, window=14):
    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_rsi_using_EMA(series, period=14):
    # Calculate price changes
    delta = series.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate EMA of gains and losses
    avg_gain = calculate_ema(gain, period)
    avg_loss = calculate_ema(loss, period)
    
    # Calculate RS
    rs = avg_gain / avg_loss
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_rsi_using_RMA(series, periods=14):
    delta = series.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    alpha = 1.0 / periods
    
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def create_rsi_table(symbols: List[Symbol], conn) -> PrettyTable:
    all_values = pd.DataFrame()
    
    for symbol in symbols:
        try:
            df = fetch_close_prices(symbol.kucoin_name)
            if not df.empty:
                df['RSI'] = calculate_rsi_using_EMA(df['close'])
                df['symbol'] = symbol.symbol_name
                # Take only latest row
                latest_row = df.iloc[-1:]
                all_values = pd.concat([all_values, latest_row])
                
                # Save to database if connection is available
                if conn:
                    try:
                        save_rsi_results(
                            conn=conn,
                            symbol_id=symbol.symbol_id,
                            closed_price=float(latest_row['close'].iloc[-1]),
                            rsi=float(latest_row['RSI'].iloc[-1])
                        )
                    except Exception as e:
                        app_logger.error(f"Failed to save RSI results for {symbol.symbol_name}: {str(e)}")
                
                app_logger.info('%s: Price=%f, RSI=%f', symbol.symbol_name, 
                              latest_row['close'].iloc[-1], latest_row['RSI'].iloc[-1])
        except Exception as e:
            app_logger.error(f"Error processing {symbol.symbol_name}: {str(e)}")
    
    # Sort by RSI descending
    all_values = all_values.sort_values('RSI', ascending=False)
    
    # Create table
    rsi_table = PrettyTable()
    rsi_table.field_names = ["Symbol", "Current Price", "RSI"]
    
    for _, row in all_values.iterrows():
        symbol = row['symbol']
        price = float(row['close'])
        rsi = float(row['RSI'])
        rsi_table.add_row([
            symbol,
            f"${price:,.2f}",
            f"{rsi:.2f}"
        ])
    
    return rsi_table

if __name__ == "__main__":
    create_rsi_table()