"""Symbol detection for cryptocurrency mentions in news articles.

This module provides functionality to detect cryptocurrency symbols mentioned
in article text, with confidence scoring to avoid false positives.
"""

import re
from dataclasses import dataclass

from source_repository import Symbol


# Confidence thresholds and scoring constants
CONFIDENCE_THRESHOLD = 0.6
SYMBOL_LENGTH_LONG = 4  # Symbols with 4+ characters get higher confidence
SYMBOL_LENGTH_MEDIUM = 3  # 3-character symbols get medium confidence
CONFIDENCE_LONG_SYMBOL = 0.95
CONFIDENCE_MEDIUM_SYMBOL = 0.85
CONFIDENCE_SHORT_SYMBOL = 0.7
MAX_CONTEXT_BOOST = 0.15
CONTEXT_BOOST_PER_KEYWORD = 0.05
CONTEXT_WINDOW_SIZE = 100


@dataclass
class SymbolMatch:
    """Represents a detected symbol match with confidence score.

    Attributes:
        symbol_name: Short symbol name (e.g., 'BTC', 'ETH')
        full_name: Full cryptocurrency name (e.g., 'Bitcoin', 'Ethereum')
        confidence: Confidence score between 0.0 and 1.0
        match_type: Type of match ('symbol', 'full_name', 'variation')
        matched_text: The actual text that was matched
    """

    symbol_name: str
    full_name: str
    confidence: float
    match_type: str
    matched_text: str


def detect_symbols_in_text(text: str, symbols: list[Symbol]) -> list[str]:
    """Detect cryptocurrency symbols mentioned in text.

    Args:
        text: Article text to analyze (title + content)
        symbols: List of Symbol objects to search for

    Returns:
        List of unique symbol names (e.g., ['BTC', 'ETH', 'SOL'])
        sorted by confidence score (highest first)
    """
    if not text or not symbols:
        return []

    # Combine matches from all detection methods
    all_matches: list[SymbolMatch] = []

    for symbol in symbols:
        all_matches.extend(_detect_symbol_variations(text, symbol))

    # Filter by confidence threshold and deduplicate
    high_confidence_matches = [
        match for match in all_matches if match.confidence >= CONFIDENCE_THRESHOLD
    ]

    # Group by symbol_name and keep highest confidence
    symbol_scores: dict[str, float] = {}
    for match in high_confidence_matches:
        current_score = symbol_scores.get(match.symbol_name, 0.0)
        symbol_scores[match.symbol_name] = max(current_score, match.confidence)

    # Sort by confidence (highest first)
    sorted_symbols = sorted(symbol_scores.items(), key=lambda x: x[1], reverse=True)

    return [symbol_name for symbol_name, _ in sorted_symbols]


def _detect_symbol_variations(text: str, symbol: Symbol) -> list[SymbolMatch]:
    """Detect all variations of a symbol in text.

    Args:
        text: Text to search in
        symbol: Symbol object with names to search for

    Returns:
        List of SymbolMatch objects for all found variations
    """
    matches: list[SymbolMatch] = []
    text_lower = text.lower()

    # 1. Detect full name (e.g., "Bitcoin", "Ethereum")
    full_name_pattern = rf"\b{re.escape(symbol.full_name.lower())}\b"
    if re.search(full_name_pattern, text_lower):
        matches.append(
            SymbolMatch(
                symbol_name=symbol.symbol_name,
                full_name=symbol.full_name,
                confidence=1.0,  # Full name is highest confidence
                match_type="full_name",
                matched_text=symbol.full_name,
            ),
        )

    # 2. Detect symbol name (e.g., "BTC", "ETH")
    # Apply confidence scoring based on symbol length to avoid false positives
    symbol_pattern = rf"\b{re.escape(symbol.symbol_name)}\b"
    if re.search(symbol_pattern, text, re.IGNORECASE):
        # Longer symbols get higher confidence (less likely to be false positive)
        symbol_length = len(symbol.symbol_name)
        if symbol_length >= SYMBOL_LENGTH_LONG:
            confidence = CONFIDENCE_LONG_SYMBOL
        elif symbol_length == SYMBOL_LENGTH_MEDIUM:
            confidence = CONFIDENCE_MEDIUM_SYMBOL
        else:  # 2 characters or less
            confidence = CONFIDENCE_SHORT_SYMBOL

        # Boost confidence if appears near crypto-related words
        context_boost = _calculate_context_boost(text_lower, symbol.symbol_name.lower())
        confidence = min(1.0, confidence + context_boost)

        matches.append(
            SymbolMatch(
                symbol_name=symbol.symbol_name,
                full_name=symbol.full_name,
                confidence=confidence,
                match_type="symbol",
                matched_text=symbol.symbol_name,
            ),
        )

    # 3. Detect common variations (e.g., "Bitcoin's", "Ethereum's")
    variation_patterns = [
        rf"\b{re.escape(symbol.full_name.lower())}'s\b",
        rf"\b{re.escape(symbol.full_name.lower())}-based\b",
        rf"\b{re.escape(symbol.symbol_name.lower())}/usd\b",
        rf"\b{re.escape(symbol.symbol_name.lower())}/usdt\b",
    ]

    for pattern in variation_patterns:
        if re.search(pattern, text_lower):
            matches.append(
                SymbolMatch(
                    symbol_name=symbol.symbol_name,
                    full_name=symbol.full_name,
                    confidence=0.9,
                    match_type="variation",
                    matched_text=pattern,
                ),
            )
            break  # Only count once per symbol

    return matches


def _calculate_context_boost(text: str, symbol_name: str) -> float:
    """Calculate confidence boost based on crypto-related context.

    Args:
        text: Full text (lowercase)
        symbol_name: Symbol name to search around (lowercase)

    Returns:
        Confidence boost value (0.0 to 0.15)
    """
    # Find the position of the symbol
    symbol_pos = text.find(symbol_name)
    if symbol_pos == -1:
        return 0.0

    # Extract context window (100 characters before and after)
    context_start = max(0, symbol_pos - 100)
    context_end = min(len(text), symbol_pos + len(symbol_name) + 100)
    context = text[context_start:context_end]

    # Crypto-related keywords that boost confidence
    crypto_keywords = [
        "crypto",
        "cryptocurrency",
        "blockchain",
        "token",
        "coin",
        "defi",
        "exchange",
        "trading",
        "price",
        "market",
        "wallet",
        "mining",
        "staking",
    ]

    # Count keyword matches in context
    keyword_matches = sum(1 for keyword in crypto_keywords if keyword in context)

    # Convert to boost value (max 0.15)
    return min(0.15, keyword_matches * 0.05)


def get_symbol_names_from_symbols(symbols: list[Symbol]) -> list[str]:
    """Extract symbol names from Symbol objects.

    Args:
        symbols: List of Symbol objects

    Returns:
        List of symbol names (e.g., ['BTC', 'ETH', 'SOL'])
    """
    return [symbol.symbol_name for symbol in symbols]
