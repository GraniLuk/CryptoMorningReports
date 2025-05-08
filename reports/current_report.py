import os
from datetime import datetime, timedelta, timezone

from infra.telegram_logging_handler import app_logger
from news.news_agent import create_ai_client
from source_repository import fetch_symbol_by_name
from technical_analysis.daily_candle import fetch_daily_candles
from technical_analysis.fifteen_min_candle import fetch_fifteen_min_candles
from technical_analysis.hourly_candle import fetch_hourly_candles

# Define system prompts for the AI analysis
SYSTEM_PROMPT_SITUATION = """
You are an advanced crypto analyst specialized in deep technical analysis for specific cryptocurrencies.
Focus on providing detailed insights based solely on the provided price data across multiple timeframes.
Your analysis should include:
1. Support and resistance levels with specific price targets
2. Trend identification and potential reversal points
3. Volume analysis and its implications
4. Key technical indicators and what they suggest
5. Clear trading opportunities with entry, target, and stop-loss levels

Format your response using proper Markdown for readability, including sections with headers.
"""

USER_PROMPT_SITUATION = """
Analyze the current situation for {symbol_name} based on the following data:

DAILY CANDLES (LAST 7 DAYS):
{daily_candles}

HOURLY CANDLES (LAST 24 HOURS):
{hourly_candles}

15-MINUTE CANDLES (LAST 24 HOURS):
{fifteen_min_candles}

Provide a comprehensive technical analysis including:
1. Current trend direction across all timeframes
2. Key support and resistance levels with exact prices
3. Notable patterns forming in any timeframe
4. Volume analysis and what it suggests about momentum
5. Short-term price targets (24-48 hours)
6. Actionable trading strategy with entry, target and stop loss
7. Risk assessment for the suggested strategy

Include specific numbers and percentages in your analysis rather than general statements.
"""


def format_candle_data(candles):
    """Format candle data for AI prompt"""
    if not candles:
        return "No data available"

    formatted = "Date | Open | High | Low | Close | Volume\n"
    formatted += "---- | ---- | ---- | --- | ----- | ------\n"

    for candle in candles:
        date_str = candle.end_date.strftime("%Y-%m-%d %H:%M")
        formatted += f"{date_str} | {candle.open:.4f} | {candle.high:.4f} | {candle.low:.4f} | {candle.close:.4f} | {candle.volume:.2f}\n"

    return formatted


async def generate_crypto_situation_report(conn, symbol_name):
    """
    Generate a comprehensive situation report for a specific cryptocurrency

    Args:
        conn: Database connection
        symbol_name: Cryptocurrency symbol (e.g., "BTC", "ETH")

    Returns:
        Markdown formatted situation report
    """
    logger = app_logger
    logger.info(f"Generating situation report for {symbol_name}")

    # Get symbol from database
    symbol = fetch_symbol_by_name(conn, symbol_name)
    if not symbol:
        error_msg = f"Symbol {symbol_name} not found in the database"
        logger.error(error_msg)
        return error_msg

    symbols = [symbol]

    # Calculate date ranges using UTC time
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)

    # Fetch candles for different timeframes
    daily_candles = fetch_daily_candles(
        symbols, conn, start_date=seven_days_ago.date(), end_date=now.date()
    )
    hourly_candles = fetch_hourly_candles(
        symbols, conn, end_time=now, start_time=one_day_ago
    )
    fifteen_min_candles = fetch_fifteen_min_candles(
        symbols, conn, end_time=now, start_time=one_day_ago
    )

    # Check if we have data
    if not daily_candles or not hourly_candles or not fifteen_min_candles:
        warning_msg = (
            f"Warning: Incomplete data for {symbol_name}. Daily candles: {len(daily_candles)}, "
            f"Hourly candles: {len(hourly_candles)}, 15min candles: {len(fifteen_min_candles)}"
        )
        logger.warning(warning_msg)

    # Format candle data for the AI prompt
    daily_formatted = format_candle_data(daily_candles)
    hourly_formatted = format_candle_data(hourly_candles)
    fifteen_min_formatted = format_candle_data(fifteen_min_candles)

    # Determine which AI API to use
    ai_api_type = os.environ.get("AI_API_TYPE", "perplexity").lower()
    ai_api_key = ""

    if ai_api_type == "perplexity":
        ai_api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        logger.info("Using Perplexity API for analysis")
    elif ai_api_type == "gemini":
        ai_api_key = os.environ.get("GEMINI_API_KEY", "")
        logger.info("Using Gemini API for analysis")
    else:
        logger.warning(f"Unknown AI API type: {ai_api_type}, defaulting to Perplexity")
        ai_api_type = "perplexity"
        ai_api_key = os.environ.get("PERPLEXITY_API_KEY", "")

    if not ai_api_key:
        error_msg = f"Failed: No {ai_api_type.title()} API key found"
        logger.error(error_msg)
        return error_msg

    try:
        # Create AI client and generate analysis
        ai_client = create_ai_client(ai_api_type, ai_api_key)

        # Prepare prompt content
        formatted_prompt = USER_PROMPT_SITUATION.format(
            symbol_name=symbol_name,
            daily_candles=daily_formatted,
            hourly_candles=hourly_formatted,
            fifteen_min_candles=fifteen_min_formatted,
        )

        # For PerplexityClient
        if isinstance(ai_client, type) and ai_client.__name__ == "PerplexityClient":
            data = {
                "model": "sonar-pro",  # Use appropriate model
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_SITUATION,
                    },
                    {
                        "role": "user",
                        "content": formatted_prompt,
                    },
                ],
            }

            try:
                import requests

                response = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    json=data,
                    headers=ai_client.headers,
                )

                if response.status_code == 200:
                    analysis = response.json()["choices"][0]["message"]["content"]
                else:
                    error_msg = (
                        f"Failed: API error: {response.status_code} - {response.text}"
                    )
                    logger.error(error_msg)
                    return error_msg
            except Exception as e:
                error_msg = f"Failed to get crypto situation analysis: {str(e)}"
                logger.error(error_msg)
                return error_msg

        # For GeminiClient
        elif ai_api_type == "gemini":
            try:
                prompt = f"{SYSTEM_PROMPT_SITUATION}\n\n{formatted_prompt}"
                response = ai_client.model.generate_content(prompt)

                if response.candidates and len(response.candidates) > 0:
                    analysis = response.text
                else:
                    error_msg = "Failed: No valid response from Gemini API"
                    logger.error(error_msg)
                    return error_msg
            except Exception as e:
                error_msg = (
                    f"Failed to get crypto situation analysis from Gemini: {str(e)}"
                )
                logger.error(error_msg)
                return error_msg

        # Add header to the report
        report_title = f"# {symbol_name} Situation Report\n\n"
        report_date = f"*Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}*\n\n"

        full_report = report_title + report_date + analysis
        logger.info(f"Successfully generated situation report for {symbol_name}")

        return full_report

    except Exception as e:
        error_msg = f"Error generating situation report for {symbol_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    import asyncio

    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    async def main():
        load_dotenv()
        conn = connect_to_sql()
        # Example usage
        symbol_name = "Virtual"  # Replace with desired symbol
        report = await generate_crypto_situation_report(conn, symbol_name)
        print(report)

    # Run the async main function
    asyncio.run(main())
