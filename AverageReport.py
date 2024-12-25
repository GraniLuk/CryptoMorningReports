from collections import namedtuple
import logging
import yfinance as yf
from utils import clean_symbol
from prettytable import PrettyTable

def create_average_table(symbols=["BTCUSDT"]):
    all_values = []
    CryptoData = namedtuple('CryptoData', ['symbol', 'current_price', 'ma50', 'ma200'])

    for symbol in symbols:
        try:
            logging.info('Processing symbol: %s', symbol)
            ticker = yf.Ticker(symbol)
            df = ticker.history(interval="1d", period="max")
            logging.info('Retrieved %d data points for %s', len(df), symbol)
            df['MA50'] = df['Close'].rolling(window=50).mean()
            today_MA50 = round(df['MA50'].iloc[-1],3)
            df['MA200'] = df['Close'].rolling(window=200).mean()
            today_MA200 = round(df['MA200'].iloc[-1],3)
            today_price = round(df['Close'].iloc[-1], 3)
            # Store the results
            all_values.append(CryptoData(
                symbol=symbol,
                current_price=today_price,
                ma50=today_MA50,
                ma200=today_MA200
            ))
        except Exception as e:
            logging.error('Error processing symbol %s: %s', symbol, str(e))

    
    average_table = PrettyTable()
    average_table.field_names = ["Symbol", "Current Price", "MA50", "MA200"]

    for row in all_values:
        symbol = clean_symbol(row.symbol)
        price = row.current_price
        ma50 = row.ma50
        ma200 = row.ma200
        average_table.add_row([symbol, price ,ma50, ma200])

    return average_table