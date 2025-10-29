# Define system prompts for the AI analysis
SYSTEM_PROMPT_SITUATION = """
You are an advanced crypto analyst specialized in deep technical analysis for
specific cryptocurrencies.
Focus on providing detailed insights based solely on the provided price data
across multiple timeframes.
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
