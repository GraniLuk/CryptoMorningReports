import logging
import asyncio
from datetime import date, datetime
import azure.functions as func
import os
from dotenv import load_dotenv
from technical_analysis.priceRangeReport import fetch_range_price
from technical_analysis.RSIReport import create_rsi_table
from technical_analysis.movingAveragesReport import calculate_indicators
from technical_analysis.macd_report import calculate_macd
from stepn.stepn_report import fetch_stepn_report
from infra.telegram_logging_handler import app_logger
from infra.sql_connection import connect_to_sql
from source_repository import fetch_symbols
from launchpool.launchpool_report import check_gempool_articles
from news.news_agent import get_detailed_crypto_analysis, highlight_articles
from news.rss_parser import get_news
from sharedCode.telegram import send_telegram_message
from technical_analysis.volume_report import fetch_volume_report

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

        # Check if there is new launchpool
        launchpool_report = check_gempool_articles()
        
        # Fetch volume report
        volume_table = fetch_volume_report(symbols, conn)

        # Print tables
        logger.info(rsi_table)
        logger.info(ma_average_table)
        logger.info(ema_average_table)
        logger.info(range_table)
        logger.info(stepn_table)
        logger.info(macd_table)
        logger.info(launchpool_report)

        # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Format message with pre tags
        message_part1 = f"Crypto Report: {today_date}\n"
        message_part1 += f"RSI Report: <pre>{rsi_table}</pre>\n\n"
        message_part1 += f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
        message_part1 += f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
        message_part2 = f"MACD Report: <pre>{macd_table}</pre>\n\n"
        message_part2 += f"24h Range Report:\n<pre>{range_table}</pre>"
        stepn_report = f"StepN Report: <pre>{stepn_table}</pre>"
        volume_report = f"Volume Report: <pre>{volume_table}</pre>"

        fetched_news = get_news()
        news_report = get_detailed_crypto_analysis(os.environ["PERPLEXITY_API_KEY"], message_part1 + message_part2, fetched_news)        
        highlight_articles_message = highlight_articles(os.environ["PERPLEXITY_API_KEY"], symbols, fetched_news)

        # Run the async function with HTML parse mode for both messages
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message_part1,
            parse_mode="HTML"
        ))
        
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message_part2,
            parse_mode="HTML"
        ))

        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            stepn_report,
            parse_mode="HTML"
        ))
        
        asyncio.run(send_telegram_message(
            telegram_enabled,
            telegram_token,
            telegram_chat_id,
            volume_report,
            parse_mode="HTML"
        ))

        if (launchpool_report):
            message_part3 = f"New Launchpool Report: <pre>{launchpool_report}</pre>"
            asyncio.run(send_telegram_message(
                telegram_enabled, 
                telegram_token, 
                telegram_chat_id, 
                message_part3,
                parse_mode="HTML"
            ))

        if (news_report.startswith("Failed")):
            app_logger.error('Failed to get news analysis: %s', news_report)
        else:
            asyncio.run(send_telegram_message(
                telegram_enabled,
                telegram_token,
                telegram_chat_id,
                news_report,
                parse_mode="HTML"
            ))
        
        if (highlight_articles_message.startswith("Failed")):
            app_logger.error('Failed to get news analysis: %s', highlight_articles_message)
        else:
            asyncio.run(send_telegram_message(
                telegram_enabled,
                telegram_token,
                telegram_chat_id,
                highlight_articles_message,
                parse_mode="HTML"
            ))
    except Exception as e:
        logger.error('Function failed with error: %s', str(e))
        raise
    finally:
        conn.close()

def process_past_reports(target_date: date = None):
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
        #rsi_table = create_rsi_table(symbols, conn)

        # Create second table for 50d and 200d averages
        ma_average_table, ema_average_table = calculate_indicators(symbols, conn, target_date)

        # Create second table for 24h ranges
        #range_table = fetch_range_price(symbols, conn)

        # Create table for stepN report
        #stepn_table = fetch_stepn_report(conn)

        # Add MACD table calculation
        macd_table = calculate_macd(symbols, conn, target_date)

        # Print tables
        #logger.info(rsi_table)
        logger.info(ma_average_table)
        logger.info(ema_average_table)
        #logger.info(range_table)
        #logger.info(stepn_table)
        logger.info(macd_table)


        # Format message with pre tags
        message_part1 = f"Crypto Report: {target_date}\n"
        #message_part1 += f"RSI Report: <pre>{rsi_table}</pre>\n\n"
        message_part1 += f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
        message_part1 += f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
        
        message_part2 = f"MACD Report: <pre>{macd_table}</pre>\n\n"
        #message_part2 += f"24h Range Report:\n<pre>{range_table}</pre>"
        #message_part2 += f"StepN Report: <pre>{stepn_table}</pre>"

        # Run the async function with HTML parse mode for both messages
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message_part1,
            parse_mode=None
        ))
        
        asyncio.run(send_telegram_message(
            telegram_enabled, 
            telegram_token, 
            telegram_chat_id, 
            message_part2,
            parse_mode="HTML"
        ))
    except Exception as e:
        logger.error('Function failed with error: %s', str(e))
        raise
    finally:
        conn.close()

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
