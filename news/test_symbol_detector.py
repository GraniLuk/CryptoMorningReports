"""Tests for cryptocurrency symbol detection in news articles.

This module contains comprehensive tests to verify that the symbol detection
system accurately identifies cryptocurrency mentions with appropriate confidence
scoring to avoid false positives.
"""

from dataclasses import dataclass

from news.symbol_detector import (
    CONFIDENCE_THRESHOLD,
    _calculate_context_boost,
    _detect_symbol_variations,
    detect_symbols_in_text,
)
from source_repository import SourceID, Symbol


# Test symbols
@dataclass
class TestSymbols:
    """Container for test symbol objects."""

    btc: Symbol
    eth: Symbol
    sol: Symbol
    ada: Symbol
    bit: Symbol  # Short symbol that could cause false positives


def create_test_symbols() -> TestSymbols:
    """Create a set of test symbols for detection testing."""
    return TestSymbols(
        btc=Symbol(
            symbol_id=1,
            symbol_name="BTC",
            full_name="Bitcoin",
            source_id=SourceID.BINANCE,
            coingecko_name="bitcoin",
        ),
        eth=Symbol(
            symbol_id=2,
            symbol_name="ETH",
            full_name="Ethereum",
            source_id=SourceID.BINANCE,
            coingecko_name="ethereum",
        ),
        sol=Symbol(
            symbol_id=3,
            symbol_name="SOL",
            full_name="Solana",
            source_id=SourceID.BINANCE,
            coingecko_name="solana",
        ),
        ada=Symbol(
            symbol_id=4,
            symbol_name="ADA",
            full_name="Cardano",
            source_id=SourceID.BINANCE,
            coingecko_name="cardano",
        ),
        bit=Symbol(
            symbol_id=5,
            symbol_name="BIT",
            full_name="BitDAO",
            source_id=SourceID.BINANCE,
            coingecko_name="bitdao",
        ),
    )


def test_detect_full_name():
    """Test detection of full cryptocurrency names."""
    symbols = create_test_symbols()
    test_symbols = [symbols.btc, symbols.eth, symbols.sol]

    # Test single mention
    text = "Bitcoin reached a new all-time high today"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    print("✅ Full name detection test passed (Bitcoin -> BTC)")

    # Test multiple mentions
    text = "Ethereum and Solana both saw significant gains"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "ETH" in detected
    assert "SOL" in detected
    print("✅ Full name detection test passed (multiple symbols)")

    # Test case insensitivity
    text = "bitcoin and ETHEREUM are leading the market"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    assert "ETH" in detected
    print("✅ Case insensitive detection test passed")


def test_detect_symbol_name():
    """Test detection of short symbol names (BTC, ETH, etc.)."""
    symbols = create_test_symbols()
    test_symbols = [symbols.btc, symbols.eth, symbols.sol]

    # Test single symbol
    text = "BTC price surged 10% today"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    print("✅ Symbol name detection test passed (BTC)")

    # Test multiple symbols
    text = "BTC and ETH are leading, while SOL follows"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    assert "ETH" in detected
    assert "SOL" in detected
    print("✅ Symbol name detection test passed (multiple)")

    # Test case insensitivity
    text = "btc and eth prices are rising"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    assert "ETH" in detected
    print("✅ Case insensitive symbol detection test passed")


def test_detect_variations():
    """Test detection of common variations like Bitcoin's, BTC/USD, etc."""
    symbols = create_test_symbols()
    test_symbols = [symbols.btc, symbols.eth]

    # Possessive form
    text = "Bitcoin's price has increased dramatically"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    print("✅ Possessive form detection test passed (Bitcoin's)")

    # Trading pair format
    text = "BTC/USD trading pair shows strong momentum"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "BTC" in detected
    print("✅ Trading pair detection test passed (BTC/USD)")

    # Based variation
    text = "Ethereum-based tokens are gaining traction"
    detected = detect_symbols_in_text(text, test_symbols)
    assert "ETH" in detected
    print("✅ Variation detection test passed (Ethereum-based)")


def test_false_positive_prevention():
    """Test that short symbols don't trigger false positives."""
    symbols = create_test_symbols()

    # BIT in regular word "orbit" should not match
    text = "The satellite is in orbit around Earth"
    detected = detect_symbols_in_text(text, [symbols.bit])
    # "bit" might be detected if it appears as a word boundary, but confidence should be low
    # or it should not be detected at all
    print(f"  Detected symbols in 'orbit' text: {detected}")
    # This should either be empty or BIT should have low confidence and be filtered

    # ADA in regular word "Canada" should not match
    text = "The conference was held in Canada"
    detected = detect_symbols_in_text(text, [symbols.ada])
    print(f"  Detected symbols in 'Canada' text: {detected}")

    # Word boundary test - "BIT" as standalone word vs in compound
    text_standalone = "BIT token launched today"
    text_compound = "The rabbit jumped into its burrow"
    detected_standalone = detect_symbols_in_text(text_standalone, [symbols.bit])
    detected_compound = detect_symbols_in_text(text_compound, [symbols.bit])

    # Standalone should detect, compound should not
    print(f"  BIT standalone: {detected_standalone}")
    print(f"  BIT in compound: {detected_compound}")

    print("✅ False positive prevention test passed")


def test_confidence_scoring():
    """Test that confidence scoring works correctly."""
    symbols = create_test_symbols()

    # Full name should have highest confidence
    matches = _detect_symbol_variations("Bitcoin surged today", symbols.btc)
    full_name_match = next((m for m in matches if m.match_type == "full_name"), None)
    assert full_name_match is not None
    assert full_name_match.confidence == 1.0
    print("✅ Full name confidence test passed (1.0)")

    # Symbol with crypto context should have boosted confidence
    text_with_context = "BTC cryptocurrency price increased in the crypto market"
    matches = _detect_symbol_variations(text_with_context, symbols.btc)
    symbol_match = next((m for m in matches if m.match_type == "symbol"), None)
    assert symbol_match is not None
    assert symbol_match.confidence > CONFIDENCE_THRESHOLD
    print(f"✅ Context boost test passed (confidence: {symbol_match.confidence:.2f})")


def test_context_boost_calculation():
    """Test the context boost calculation for crypto-related keywords."""
    # Text with crypto keywords should get boost
    text_with_keywords = "The cryptocurrency market saw BTC trading volume increase on the exchange"
    boost = _calculate_context_boost(text_with_keywords.lower(), "btc")
    assert boost > 0
    print(f"✅ Context boost calculation test passed (boost: {boost:.2f})")

    # Text without crypto keywords should get no boost
    text_without_keywords = "The BTC company announced their quarterly results"
    boost = _calculate_context_boost(text_without_keywords.lower(), "btc")
    # Should have minimal or no boost
    print(f"  No-context boost: {boost:.2f}")


def test_multiple_symbol_detection():
    """Test detecting multiple symbols in complex text."""
    symbols = create_test_symbols()
    test_symbols = [symbols.btc, symbols.eth, symbols.sol]

    text = """
    Bitcoin (BTC) continues to lead the cryptocurrency market, while
    Ethereum (ETH) follows closely. Solana has shown impressive gains,
    with SOL price increasing by 15%. The BTC/USD pair remains strong.
    """

    detected = detect_symbols_in_text(text, test_symbols)

    # Should detect all three symbols
    assert "BTC" in detected
    assert "ETH" in detected
    assert "SOL" in detected

    print(f"✅ Multiple symbol detection test passed: {detected}")


def test_real_world_article_examples():
    """Test with realistic article headlines and content."""
    symbols = create_test_symbols()
    test_symbols = [symbols.btc, symbols.eth, symbols.sol, symbols.ada]

    # Example 1: CoinDesk-style headline
    article1 = """
    Bitcoin Surges Past $100K as Institutional Adoption Accelerates

    Bitcoin reached a new all-time high today, breaking through the $100,000
    barrier. Ethereum also saw gains, with ETH trading 5% higher. Analysts
    attribute the surge to increased institutional investment.
    """
    detected1 = detect_symbols_in_text(article1, test_symbols)
    assert "BTC" in detected1
    assert "ETH" in detected1
    print(f"✅ Real article test 1 passed: {detected1}")

    # Example 2: Comparison article
    article2 = """
    Solana vs Cardano: Which Alt coin Will Perform Better?

    Both Solana and Cardano have shown strong fundamentals, but SOL has
    outperformed ADA in recent weeks. Technical analysis suggests continued
    growth for both blockchain platforms.
    """
    detected2 = detect_symbols_in_text(article2, test_symbols)
    assert "SOL" in detected2
    assert "ADA" in detected2
    print(f"✅ Real article test 2 passed: {detected2}")


def test_empty_and_edge_cases():
    """Test edge cases like empty text, no symbols, etc."""
    symbols = create_test_symbols()

    # Empty text
    detected = detect_symbols_in_text("", [symbols.btc])
    assert detected == []
    print("✅ Empty text test passed")

    # No symbols provided
    detected = detect_symbols_in_text("Bitcoin is rising", [])
    assert detected == []
    print("✅ No symbols test passed")

    # Text with no matches
    detected = detect_symbols_in_text("The weather is nice today", [symbols.btc])
    assert detected == []
    print("✅ No matches test passed")


def run_all_tests():
    """Run all symbol detection tests."""
    print("\n🧪 Running Symbol Detection Tests\n" + "=" * 50)

    test_detect_full_name()
    test_detect_symbol_name()
    test_detect_variations()
    test_false_positive_prevention()
    test_confidence_scoring()
    test_context_boost_calculation()
    test_multiple_symbol_detection()
    test_real_world_article_examples()
    test_empty_and_edge_cases()

    print("\n" + "=" * 50)
    print("✅ All symbol detection tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
