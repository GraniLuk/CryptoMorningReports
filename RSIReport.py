import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from datetime import datetime, timedelta
from utils import clean_symbol, convert_to_binance_symbol
from prettytable import PrettyTable

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_close_prices(symbol: str, lookback_days: int = 14) -> pd.DataFrame:
    client = Client()
    
    try:
        start_time = datetime.now() - timedelta(days=lookback_days)
        
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=Client.KLINE_INTERVAL_1DAY,
            start_str=start_time.strftime('%d %b %Y'),
            limit=lookback_days
        )
        
        # Create DataFrame with numeric types
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 
            'volume', 'close_time', 'quote_volume', 
            'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Convert price columns to float
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except BinanceAPIException as e:
        print(f"Error fetching data for {symbol}: {e.message}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Unexpected error for {symbol}: {str(e)}")
        return pd.DataFrame()

def create_rsi_table(symbols=["BTCUSDT"]):
    all_values = pd.DataFrame()
    
    for symbol in symbols:
        try:
            symbol = convert_to_binance_symbol(symbol)
            df = fetch_close_prices(symbol)
            if not df.empty:
                df['RSI'] = calculate_rsi(df['close'])
                df['symbol'] = symbol
                # Take only latest row
                latest_row = df.iloc[-1:]
                all_values = pd.concat([all_values, latest_row])
                logging.info('%s: Price=%f, RSI=%f', symbol, latest_row['close'].iloc[-1], latest_row['RSI'].iloc[-1])
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
    
    # Sort by RSI descending
    all_values = all_values.sort_values('RSI', ascending=False)
    
    # Create table
    rsi_table = PrettyTable()
    rsi_table.field_names = ["Symbol", "Current Price", "RSI"]
    
    for _, row in all_values.iterrows():
        symbol = clean_symbol(row['symbol'])
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