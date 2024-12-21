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

app = func.FunctionApp()

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

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

# Get debug status from environment variable
is_debug = os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT') == 'Development'

@app.timer_trigger(
    schedule="0 5,12 * * *", 
    arg_name="myTimer", 
    run_on_startup=True,  # Only run on startup in debug/development
    use_monitor=False
) 
def BitcoinChecker(myTimer: func.TimerRequest) -> None:
    logging.info('BitcoinChecker function started at %s', datetime.now().isoformat())
    
    try:
        # Load configuration
        logging.info('Loading configuration...')
        telegram_enabled = os.environ["TELEGRAM_ENABLED"].lower() == "true"
        telegram_token = os.environ["TELEGRAM_TOKEN"]
        telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
        logging.info('Configuration loaded. Telegram enabled: %s', telegram_enabled)

        # List of symbols
        symbols = ['BTC-USD', 'ETH-USD', 'XRP-USD', 'ATOM-USD', 'DOT-USD', 'HBAR-USD', 'KCS-USD', 'FLOW-USD', 'MATIC-USD', 'AKT-USD',
                   'NEXO-USD', 'DYM-USD', 'OSMO-USD']
        logging.info('Processing %d symbols...', len(symbols))

        rsi_values = []

        for symbol in symbols:
            try:
                logging.info('Processing symbol: %s', symbol)
                ticker = yf.Ticker(symbol)
                df = ticker.history(interval="1d", period="max")
                logging.info('Retrieved %d data points for %s', len(df), symbol)
                
                df['RSI'] = calculate_rsi(df['Close'])
                logging.info('%s: Price=%f, RSI=%f', symbol, df['Close'].iloc[-1], df['RSI'].iloc[-1])
                
                # Get today's price and RSI
                today_price = round(df['Close'].iloc[-1], 3)
                today_rsi = round(df['RSI'].iloc[-1], 2)
                
                # Get 24h high/low prices
                day_high = round(df['High'].iloc[-1], 3)
                day_low = round(df['Low'].iloc[-1], 3)
                
                # Store the results
                rsi_values.append((symbol, today_price, day_high, day_low, today_rsi))
            except Exception as e:
                logging.error('Error processing symbol %s: %s', symbol, str(e))

        # Sort by RSI value in descending order
        rsi_values.sort(key=lambda x: x[4], reverse=True)

        def clean_symbol(symbol):
            return symbol.replace('-USD', '')

        # Create first table for prices and RSI
        table1 = ['| Symbol | Current Price | RSI  |']
        table1.append('|--------|---------------|------|')

        for row in rsi_values:
            symbol = clean_symbol(row[0])
            price = row[1]
            rsi = row[4]
            
            if rsi > 80:
                row_md = f'| {symbol} | {price} | **{rsi}** |'
            else:
                row_md = f'| {symbol} | {price} | {rsi} |'
                
            table1.append(row_md)

        table1 = '\n'.join(table1)

        # Create second table for 24h ranges
        table2 = PrettyTable()
        table2.field_names = ["Symbol", "24h Low", "24h High", "Range %"]
        
        # Store rows with range calculation
        range_rows = []
        for row in rsi_values:
            symbol, _, high, low, _ = row
            price_range = ((high - low) / low) * 100
            range_rows.append((clean_symbol(symbol), low, high, price_range))
        
        # Sort by price range descending
        range_rows.sort(key=lambda x: x[3], reverse=True)
        
        # Add sorted rows to table
        for row in range_rows:
            table2.add_row([row[0], row[1], row[2], f"{row[3]:.2f}%"])

        # Print tables
        logging.info(table1)
        logging.info(table2)

        # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Format message with Markdown
        message = f"RSI Report: {today_date}\n"
        message += f"{table1}\n\n"
        message += f"24h Range Report:\n```\n{table2}\n```"

        # Run the async function with Markdown parse mode
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message,
            parse_mode="Markdown"
        ))
    except Exception as e:
        logging.error('Function failed with error: %s', str(e))
        raise
