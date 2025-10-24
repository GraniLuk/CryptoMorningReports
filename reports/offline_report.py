"""
Offline report generator - uses mock data when database is unavailable.
Perfect for testing AI analysis without database access.
"""

import logging
import os
from datetime import datetime, timezone

from infra.mock_data import (
    format_mock_aggregated_data,
    generate_mock_candles,
    get_mock_aggregated_data,
    get_mock_current_prices,
    get_mock_symbols,
)
from news.news_agent import get_detailed_crypto_analysis_with_news
from news.rss_parser import get_news


async def generate_offline_report():
    """
    Generate a crypto analysis report using mock data and real news.
    This allows testing the AI analysis pipeline without database access.
    """
    logging.info("Generating offline report with mock data...")

    # Get AI configuration
    ai_api_key = os.getenv("AI_API_KEY")
    ai_api_type = os.getenv("AI_API_TYPE", "gemini")

    if not ai_api_key:
        logging.error("AI_API_KEY not set in environment variables")
        return "Error: AI_API_KEY not configured"

    # Get real news (this doesn't need database)
    logging.info("Fetching real news from RSS feeds...")
    fetched_news = get_news()
    logging.info(f"Fetched {len(fetched_news)} news articles")

    # Generate mock symbols and prices
    symbols = get_mock_symbols()
    logging.info(f"Using {len(symbols)} mock symbols")

    # Generate mock current prices section
    mock_prices = get_mock_current_prices()
    current_prices_section = "Current Prices (spot / last 24h):\n<pre>"
    current_prices_section += "Symbol  | Last        | 24h Low     | 24h High    | Range% | FromLow% | FromHigh%\n"
    current_prices_section += "--------|-------------|-------------|-------------|--------|----------|-----------\n"

    for symbol_name, price_data in mock_prices.items():
        last = price_data["last"]
        low = price_data["low_24h"]
        high = price_data["high_24h"]
        range_pct = ((high - low) / low) * 100
        from_low = ((last - low) / low) * 100
        from_high = ((high - last) / high) * 100

        current_prices_section += f"{symbol_name:7} | {last:13.2f} | {low:13.2f} | {high:13.2f} | {range_pct:6.2f} | {from_low:8.2f} | {from_high:9.2f}\n"

    current_prices_section += "</pre>\n\n"

    # Generate mock aggregated data
    aggregated_formatted = format_mock_aggregated_data()
    aggregated_with_prices = (
        current_prices_section
        + "Aggregated Indicators:\n<pre>"
        + aggregated_formatted
        + "</pre>\n\n"
    )

    # Generate the AI analysis with real news and mock indicators
    logging.info("Generating AI analysis...")
    analysis = get_detailed_crypto_analysis_with_news(
        ai_api_key,
        aggregated_with_prices,
        fetched_news,
        ai_api_type,
        conn=None,  # No database connection
    )

    # Add a header indicating this is an offline report
    offline_header = "# Crypto Analysis Report (OFFLINE MODE - Using Mock Data)\n\n"
    offline_header += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
    offline_header += "⚠️ **Note:** This report uses mock technical indicator data combined with real news for testing purposes.\n\n"
    offline_header += "---\n\n"

    full_report = offline_header + analysis

    # Print to console
    print("\n" + "=" * 80)
    print("OFFLINE REPORT GENERATED")
    print("=" * 80)
    print(full_report)
    print("=" * 80)

    # Optionally save to file
    report_filename = (
        f"offline_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    )
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(full_report)

    logging.info(f"Report saved to {report_filename}")

    return full_report


async def generate_offline_situation_report(symbol: str):
    """
    Generate a situation report for a specific symbol using mock data.
    """
    logging.info(f"Generating offline situation report for {symbol}...")

    # Get mock symbols
    symbols = get_mock_symbols()
    target_symbol = next((s for s in symbols if s.symbol_name == symbol), None)

    if not target_symbol:
        return f"Symbol {symbol} not found in mock data. Available: {', '.join(s.symbol_name for s in symbols)}"

    # Generate mock candles
    hourly_candles = generate_mock_candles(target_symbol, hours=24)

    # Create a simple report
    report = f"# {symbol} Situation Report (OFFLINE MODE)\n\n"
    report += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
    report += "⚠️ **Note:** Using mock data for testing\n\n"
    report += f"## Recent Price Action (Last 24 Hours)\n\n"

    if hourly_candles:
        latest = hourly_candles[-1]
        report += f"- **Current Price:** ${latest.close:.2f}\n"
        report += f"- **24h High:** ${max(c.high for c in hourly_candles):.2f}\n"
        report += f"- **24h Low:** ${min(c.low for c in hourly_candles):.2f}\n"
        report += f"- **24h Volume:** {sum(c.volume for c in hourly_candles):.2f}\n\n"

        report += "### Last 5 Hourly Candles:\n\n"
        for candle in hourly_candles[-5:]:
            report += f"- {candle.end_date.strftime('%Y-%m-%d %H:%M')}: "
            report += f"O: ${candle.open:.2f}, H: ${candle.high:.2f}, L: ${candle.low:.2f}, C: ${candle.close:.2f}\n"

    print("\n" + "=" * 80)
    print(f"OFFLINE SITUATION REPORT - {symbol}")
    print("=" * 80)
    print(report)
    print("=" * 80)

    return report
