from typing import List
from kucoin import Client as KucoinClient
from rsi_repository import save_rsi_results
from sharedCode.binance import fetch_close_prices_from_Binance
from sharedCode.coingecko import fetch_coingecko_price
import pandas as pd
from datetime import datetime, timedelta
from infra.configuration import get_kucoin_credentials
from prettytable import PrettyTable
import time
from infra.telegram_logging_handler import app_logger
from source_repository import SourceID, Symbol

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

def fetch_close_prices_from_Kucoin(symbol: str, limit: int = 14) -> pd.DataFrame:
    try:
        # Initialize Kucoin client
        kucoin_credentials = get_kucoin_credentials()
        api_key = kucoin_credentials['api_key']
        api_secret = kucoin_credentials['api_secret']
        api_passphrase = kucoin_credentials['api_passphrase']
        client = KucoinClient(api_key, api_secret, api_passphrase)
        
        # Calculate start time (limit days ago)
        end_time = int(time.time())
        start_time = int((datetime.now() - timedelta(days=limit)).timestamp())
        
        # Get kline data with start and end time
        klines = client.get_kline_data(symbol, '1day', start=start_time, end=end_time)
        
        # Kucoin returns data in format:
        # [timestamp, open, close, high, low, volume, turnover]
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
        
        # Convert timestamp strings to numeric first, then to datetime
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='s')
        #df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Convert string values to float
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        
        # Sort by timestamp ascending first
        df = df.sort_values('timestamp', ascending=True)
        
        # Set timestamp as index after sorting
        df.set_index('timestamp', inplace=True)
        
        return df
    
    except Exception as e:
        app_logger.error(f"Error fetching data from Kucoin: {str(e)}")
        return pd.DataFrame()

def create_rsi_table(symbols: List[Symbol], conn) -> PrettyTable:
    all_values = pd.DataFrame()
    
    for symbol in symbols:
        try:
            if (symbol.source_id == SourceID.KUCOIN):
                df = fetch_close_prices_from_Kucoin(symbol.kucoin_name)
            if (symbol.source_id == SourceID.BINANCE):
                df = fetch_close_prices_from_Binance(symbol.binance_name)
            if (symbol.source_id == SourceID.COINGECKO):
                df = fetch_coingecko_price(symbol.symbol_name)
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