import logging
import asyncio
from datetime import datetime
import azure.functions as func
import aiohttp
import os
from dotenv import load_dotenv
from priceRangeReport import fetch_range_price
from RSIReport import create_rsi_table
from movingAveragesReport import calculate_indicators
from stepn_report import fetch_stepn_report
from telegram_logging_handler import app_logger
from sql_connection import connect_to_sql, fetch_symbols, Symbol
from macd_report import calculate_macd

# Load environment variables from .env file
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
        logger = app_logger
        logger.info('Configuration loaded. Telegram enabled: %s', telegram_enabled)
        conn = connect_to_sql()
        # List of symbols
        symbols = fetch_symbols(conn)
        logger.info('Processing %d symbols...', len(symbols))
        
        # Create first table for RSI and prices
        rsi_table = create_rsi_table(symbols, conn)

        # Create second table for 50d and 200d averages
        ma_average_table, ema_average_table = calculate_indicators(symbols, conn)

        # Create second table for 24h ranges
        range_table = fetch_range_price(symbols, conn)

        # Create table for stepN report
        stepn_table = fetch_stepn_report(conn)

        # Add MACD table calculation
        macd_table = calculate_macd(symbols, conn)

        # Print tables
        logger.info(rsi_table)
        logger.info(ma_average_table)
        logger.info(ema_average_table)
        logger.info(range_table)
        logger.info(stepn_table)
        logger.info(macd_table)

        # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Format message with pre tags
        message = f"Crypto Report: {today_date}\n"
        message += f"RSI Report: <pre>{rsi_table}</pre>\n\n"
        message += f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
        message += f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
        message += f"MACD Report: <pre>{macd_table}</pre>\n\n"
        message += f"24h Range Report:\n<pre>{range_table}</pre>"
        message += f"StepN Report: <pre>{stepn_table}</pre>"

        # Run the async function with HTML parse mode
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message,
            parse_mode="HTML"
        ))
    except Exception as e:
        logger.error('Function failed with error: %s', str(e))
        raise
    finally:
        conn.close()


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
    schedule="0 5 * * *", 
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