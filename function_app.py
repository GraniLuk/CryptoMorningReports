import logging
import yfinance as yf
import pandas as pd
from prettytable import PrettyTable
from telegram import Bot
import asyncio
from datetime import datetime
import azure.functions as func
import requests
from azure.data.tables import TableServiceClient
import aiohttp
import os
from dotenv import load_dotenv
from collections import namedtuple
from utils import clean_symbol
from binance24 import fetch_range_price
from RSIReport import create_rsi_table

load_dotenv()

app = func.FunctionApp()

def process_bitcoin_checker():
    logging.info('BitcoinChecker function started at %s', datetime.now().isoformat())
    
    try:
        # Load configuration
        logging.info('Loading configuration...')
        telegram_enabled = os.environ["TELEGRAM_ENABLED"].lower() == "true"
        telegram_token = os.environ["TELEGRAM_TOKEN"]
        telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
        logging.info('Configuration loaded. Telegram enabled: %s', telegram_enabled)

        # List of symbols
        symbols = ['BTC-USD', 'ETH-USD', 'XRP-USD', 'ATOM-USD', 'DOT-USD', 'HBAR-USD', 'KCS-USD', 'FLOW-USD', 'POL-USD', 'AKT-USD',
                   'NEXO-USD', 'DYM-USD', 'OSMO-USD']
        logging.info('Processing %d symbols...', len(symbols))

        all_values = []

        CryptoData = namedtuple('CryptoData', ['symbol', 'current_price', 'rsi', 'ma50', 'ma200'])

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
                # Store the results
                all_values.append(CryptoData(
                    symbol=symbol,
                    ma50=today_MA50,
                    ma200=today_MA200
                ))
            except Exception as e:
                logging.error('Error processing symbol %s: %s', symbol, str(e))

        # Create first table for RSI and prices
        rsi_table = create_rsi_table(symbols)

        average_table = PrettyTable()
        average_table.field_names = ["Symbol", "Current Price", "MA50", "MA200"]
        
        for row in all_values:
            symbol = clean_symbol(row.symbol)
            price = row.current_price
            ma50 = row.ma50
            ma200 = row.ma200
            average_table.add_row([symbol, price ,ma50, ma200])

        # Create second table for 24h ranges
        range_table = fetch_range_price(symbols)
        # Print tables
        logging.info(rsi_table)
        logging.info(average_table)
        logging.info(range_table)

        # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Format message with pre tags
        message = f"Crypto Report: {today_date}\n"
        message += f"RSI Report: <pre>{rsi_table}</pre>\n\n"
        message += f"Average Report: <pre>{average_table}</pre>\n\n"
        message += f"24h Range Report:\n<pre>{range_table}</pre>"

        # Run the async function with HTML parse mode
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message,
            parse_mode="HTML"
        ))
    except Exception as e:
        logging.error('Function failed with error: %s', str(e))
        raise


# Update send_telegram_message function definition:
async def send_telegram_message(enabled, token, chat_id, message, parse_mode="HTML"):
    if not enabled:
        logging.info('Telegram notifications are disabled')
        return
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.text()
                logging.info('Telegram API response: %s', result)
    except Exception as e:
        logging.error('Failed to send Telegram message: %s', str(e))

@app.timer_trigger(
    schedule="0 5,12 * * *", 
    arg_name="myTimer", 
    use_monitor=False
) 
def BitcoinChecker(myTimer: func.TimerRequest) -> None:
    process_bitcoin_checker()

@app.route(route="manual-trigger")
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("manual_trigger function started")
    try:
        process_bitcoin_checker()
        logging.info("BitcoinChecker function completed successfully")
        return func.HttpResponse("Function executed successfully", status_code=200)
    except Exception as e:
        logging.error(f"Error in manual_trigger: {str(e)}")
        return func.HttpResponse(f"Function execution failed: {str(e)}", status_code=500)