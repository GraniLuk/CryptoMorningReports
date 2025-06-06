import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from infra.telegram_logging_handler import app_logger
from news.news_agent import create_ai_client
from source_repository import fetch_symbol_by_name
from technical_analysis.daily_candle import fetch_daily_candles
from technical_analysis.fifteen_min_candle import (
    fetch_fifteen_minutes_candles_for_all_symbols,
)
from technical_analysis.hourly_candle import fetch_hourly_candles_for_all_symbols
from technical_analysis.reports.current_data_table import (
    get_current_data_for_ai_prompt,
    get_current_data_summary_table,
)
from technical_analysis.reports.rsi_multi_timeframe import get_rsi_for_symbol_timeframe
from technical_analysis.repositories.moving_averages_repository import (
    fetch_moving_averages_for_symbol,
)

# Define system prompts for the AI analysis
SYSTEM_PROMPT_SITUATION = """
You are an expert cryptocurrency technical analyst performing in-depth market analysis. Drawing strictly from the provided price and volume data across multiple timeframes, deliver a comprehensive technical assessment with no fundamental analysis, news, or external factors.

Analysis Requirements:
1. Price Action Analysis
   - Identify major trend direction and structure
   - Specify key support/resistance levels with exact price values
   - Highlight significant chart patterns and their completion targets
   - Flag potential trend reversal points with price triggers

2. Volume Profile Assessment
   - Evaluate volume distribution at key price levels
   - Note volume divergences from price action
   - Identify high-volume nodes and areas of interest

3. Technical Indicator Analysis
   - RSI, MACD, and Moving Averages interpretation
   - Indicator divergences and crossovers
   - Time-sensitive momentum signals

4. Trading Opportunities
   - Specify exact entry price levels
   - Define multiple take-profit targets with rationale
   - Set precise stop-loss levels
   - Calculate risk-reward ratios

Present your analysis in clear Markdown formatting with:
- Main section headers (##)
- Subsection headers (###)
- Bullet points for key findings
- Tables for price levels
- Bold text for critical alerts
- Price values to 2 decimal places
"""

USER_PROMPT_SITUATION = """
Conduct a multi-timeframe technical analysis for {symbol_name} using the provided market data:

CURRENT MARKET SNAPSHOT:
{current_data_snapshot}

Input Data:
- DAILY CANDLES (LAST 7 DAYS): {daily_candles}

- HOURLY CANDLES (LAST 24 HOURS): {hourly_candles}

- 15-MINUTE CANDLES (LAST 24 HOURS): {fifteen_min_candles}

- RSI DATA (MULTIPLE TIMEFRAMES):
  Daily RSI: {daily_rsi}
  Hourly RSI: {hourly_rsi}
  15-min RSI: {fifteen_min_rsi}

- MOVING AVERAGES DATA (LAST 7 DAYS):
  {moving_averages}

Required Analysis Components:

1. Trend Analysis
   - Primary trend direction (Daily)
   - Intermediate trend (Hourly)
   - Short-term trend (15-min)
   - Identify any trend divergences between timeframes

2. Price Levels
   - Major support levels (list exact prices)
   - Major resistance levels (list exact prices)
   - Current price relative to key Moving Averages (20, 50, 200)

3. Technical Patterns
   - Chart patterns (specify completion '%' and target prices)
   - Candlestick formations
   - Momentum indicators (RSI, MACD, Stochastic)
   - Volume profile analysis with specific levels

4. Trading Recommendation
   - Entry price range: [specify exact prices]
   - Stop loss price: [specify exact price]
   - Take profit targets: [list multiple prices]
   - Risk-to-reward ratio calculation
   - Maximum drawdown potential (%)

5. Risk Assessment
   - Market volatility metrics (ATR, standard deviation)
   - Proximity to major economic events
   - Trading volume vs. average volume (%)
   - Institutional order flow analysis

Format all price targets, levels, and percentages with exact numerical values.
Include probability estimates for each predicted price movement.
Specify timeframes for all predictions (in hours/days).
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


def format_rsi_data(rsi_df):
    """Format RSI data for AI prompt"""
    if rsi_df is None or rsi_df.empty:
        return "No RSI data available"

    formatted = "Date | Close Price | RSI Value\n"
    formatted += "---- | ----------- | ---------\n"

    for idx, row in rsi_df.iterrows():
        date_str = idx.strftime("%Y-%m-%d %H:%M")
        close_price = row.get("Close", "N/A")
        rsi_value = row.get("RSI", "N/A")

        if pd.notna(close_price) and pd.notna(rsi_value):
            formatted += f"{date_str} | {close_price:.4f} | {rsi_value:.2f}\n"
        else:
            formatted += f"{date_str} | {close_price if pd.notna(close_price) else 'N/A'} | {rsi_value if pd.notna(rsi_value) else 'N/A'}\n"

    return formatted


def format_moving_averages_data(ma_df):
    """Format moving averages data for AI prompt"""
    if ma_df is None or ma_df.empty:
        return "No moving averages data available"

    formatted = "Date | Price | MA50 | MA200 | EMA50 | EMA200\n"
    formatted += "---- | ----- | ---- | ----- | ----- | ------\n"

    for _, row in ma_df.iterrows():
        date_str = row.get("IndicatorDate", "").strftime("%Y-%m-%d")
        price = row.get("CurrentPrice", "N/A")
        ma50 = row.get("MA50", "N/A")
        ma200 = row.get("MA200", "N/A")
        ema50 = row.get("EMA50", "N/A")
        ema200 = row.get("EMA200", "N/A")

        if all(pd.notna(x) for x in [price, ma50, ma200, ema50, ema200]):
            formatted += f"{date_str} | {price:.4f} | {ma50:.4f} | {ma200:.4f} | {ema50:.4f} | {ema200:.4f}\n"
        else:
            values = [
                price if pd.notna(price) else "N/A",
                ma50 if pd.notna(ma50) else "N/A",
                ma200 if pd.notna(ma200) else "N/A",
                ema50 if pd.notna(ema50) else "N/A",
                ema200 if pd.notna(ema200) else "N/A",
            ]
            formatted += f"{date_str} | {values[0]} | {values[1]} | {values[2]} | {values[3]} | {values[4]}\n"

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
    half_year_ago = now - timedelta(days=180)
    one_day_ago = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    # Fetch candles for different timeframes
    daily_candles = fetch_daily_candles(
        symbols, conn, start_date=half_year_ago.date(), end_date=now.date()
    )
    hourly_candles = fetch_hourly_candles_for_all_symbols(
        symbols, end_time=now, start_time=two_days_ago, conn=conn
    )
    fifteen_min_candles = fetch_fifteen_minutes_candles_for_all_symbols(
        symbols, end_time=now, start_time=one_day_ago, conn=conn
    )

    # Fetch RSI data for different timeframes
    daily_rsi = get_rsi_for_symbol_timeframe(symbol, conn, "daily", lookback_days=180)
    hourly_rsi = get_rsi_for_symbol_timeframe(symbol, conn, "hourly", lookback_days=2)
    fifteen_min_rsi = get_rsi_for_symbol_timeframe(
        symbol, conn, "fifteen_min", lookback_days=1
    )

    # Fetch moving averages data for the symbol
    moving_averages = fetch_moving_averages_for_symbol(
        conn, symbol.symbol_id, lookback_days=7
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

    # Format RSI data for the AI prompt
    daily_rsi_formatted = format_rsi_data(daily_rsi)
    hourly_rsi_formatted = format_rsi_data(hourly_rsi)
    fifteen_min_rsi_formatted = format_rsi_data(
        fifteen_min_rsi
    )  # Format moving averages data for the AI prompt
    moving_averages_formatted = format_moving_averages_data(moving_averages)

    # Generate current data snapshot for AI prompt and final report
    current_data_snapshot = get_current_data_for_ai_prompt(symbol, conn)
    current_data_table = get_current_data_summary_table(symbol, conn)

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
        ai_client = create_ai_client(ai_api_type, ai_api_key)  # Prepare prompt content
        formatted_prompt = USER_PROMPT_SITUATION.format(
            symbol_name=symbol_name,
            current_data_snapshot=current_data_snapshot,
            daily_candles=daily_formatted,
            hourly_candles=hourly_formatted,
            fifteen_min_candles=fifteen_min_formatted,
            daily_rsi=daily_rsi_formatted,
            hourly_rsi=hourly_rsi_formatted,
            fifteen_min_rsi=fifteen_min_rsi_formatted,
            moving_averages=moving_averages_formatted,
        )

        # Initialize analysis to handle potential cases where no condition matches
        analysis = ""

        # For PerplexityClient - checking for an instance instead of a class type
        if ai_api_type == "perplexity" or (
            hasattr(ai_client, "__class__")
            and ai_client.__class__.__name__ == "PerplexityClient"
        ):
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

                # Ensure we have headers for the Perplexity client
                headers = getattr(ai_client, "headers", {})

                response = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    json=data,
                    headers=headers,
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
                return error_msg  # For GeminiClient
        elif ai_api_type == "gemini":
            try:  # Import GeminiClient to check the client type
                from news.news_agent import GeminiClient

                # Check if it's a GeminiClient
                if isinstance(ai_client, GeminiClient):
                    prompt = f"{SYSTEM_PROMPT_SITUATION}\n\n{formatted_prompt}"
                    # Now we know it's a GeminiClient with a model attribute
                    response = ai_client.model.generate_content(prompt)

                    if response.candidates and len(response.candidates) > 0:
                        analysis = response.text
                    else:
                        error_msg = "Failed: No valid response from Gemini API"
                        logger.error(error_msg)
                        return error_msg
                else:
                    error_msg = "Failed: Invalid Gemini client configuration"
                    logger.error(error_msg)
                    return error_msg
            except Exception as e:
                error_msg = (
                    f"Failed to get crypto situation analysis from Gemini: {str(e)}"
                )
                logger.error(error_msg)
                return error_msg
        else:
            error_msg = f"Failed: Unsupported AI client type: {ai_api_type}"
            logger.error(error_msg)
            return error_msg

        # Check if we got a valid analysis
        if not analysis:
            error_msg = "Failed: No analysis was generated"
            logger.error(error_msg)
            return error_msg  # Add header to the report
        report_title = f"# {symbol_name} Situation Report\n\n"
        report_date = f"*Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}*\n\n"

        full_report = report_title + report_date + current_data_table + analysis
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
