"""Fetch and save Order Book liquidity data and CVD for symbols."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING


# Add parent directory to path for imports when run standalone
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from datetime import UTC, datetime

from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from shared_code.binance import fetch_binance_cvd, fetch_binance_order_book
from source_repository import SourceID, Symbol
from technical_analysis.repositories.cvd_repository import CVDRepository
from technical_analysis.repositories.order_book_repository import OrderBookRepository


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


# Constants for volume formatting thresholds
VOLUME_BILLION = 1_000_000_000
VOLUME_MILLION = 1_000_000
VOLUME_THOUSAND = 1_000

# Constants for bid/ask ratio interpretation
RATIO_BUY_PRESSURE = 1.2
RATIO_SELL_PRESSURE = 0.8

# Minimum wall size to report in AI context (USD)
MIN_SIGNIFICANT_WALL = 100_000

# CVD thresholds for interpretation (relative to 24h volume)
CVD_STRONG_THRESHOLD = 0.1  # 10% of total volume = strong signal
CVD_STRONG_PCT = 10  # 10% = strong buying/selling
CVD_MODERATE_PCT = 5  # 5% = moderate buying/selling


def _format_volume(value: float) -> str:
    """Format volume value with appropriate suffix (K, M, B).

    Args:
        value: Volume value in USD

    Returns:
        Formatted string with suffix

    """
    if value >= VOLUME_BILLION:
        return f"${value / VOLUME_BILLION:.1f}B"
    if value >= VOLUME_MILLION:
        return f"${value / VOLUME_MILLION:.1f}M"
    if value >= VOLUME_THOUSAND:
        return f"${value / VOLUME_THOUSAND:.0f}K"
    return f"${value:.0f}"


def _get_ratio_indicator(ratio: float) -> str:
    """Get emoji indicator based on bid/ask ratio.

    Args:
        ratio: Bid/Ask volume ratio

    Returns:
        Emoji string: 🟢 (buy pressure), 🔴 (sell pressure), ⚪ (neutral)

    """
    if ratio > RATIO_BUY_PRESSURE:
        return "🟢"  # Strong buying pressure
    if ratio < RATIO_SELL_PRESSURE:
        return "🔴"  # Strong selling pressure
    return "⚪"  # Neutral


def fetch_order_book_report(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> PrettyTable:
    """Fetch Order Book depth for all symbols and save to database.

    Args:
        symbols: List of Symbol objects to fetch data for
        conn: Database connection

    Returns:
        PrettyTable with order book liquidity data

    """
    repo = OrderBookRepository(conn)

    table = PrettyTable()
    table.field_names = [
        "Symbol",
        "Best Bid",
        "Best Ask",
        "Spread%",
        "Bid Vol 2%",
        "Ask Vol 2%",
        "B/A Ratio",
        "Bid Wall",
        "Ask Wall",
    ]
    table.align["Symbol"] = "l"
    table.align["Best Bid"] = "r"
    table.align["Best Ask"] = "r"
    table.align["Spread%"] = "r"
    table.align["Bid Vol 2%"] = "r"
    table.align["Ask Vol 2%"] = "r"
    table.align["B/A Ratio"] = "r"
    table.align["Bid Wall"] = "r"
    table.align["Ask Wall"] = "r"

    indicator_date = datetime.now(UTC)
    successful = 0
    failed = 0

    for symbol in symbols:
        # Only fetch for Binance symbols (order book API)
        if symbol.source_id != SourceID.BINANCE:
            continue

        try:
            metrics = fetch_binance_order_book(symbol, limit=100)

            if metrics is None:
                app_logger.warning(f"No order book data available for {symbol.symbol_name}")
                failed += 1
                continue

            # Save to database
            repo.save_order_book_metrics(
                symbol.symbol_id,
                metrics,
                indicator_date,
            )

            # Get ratio indicator
            indicator = _get_ratio_indicator(metrics.bid_ask_ratio)

            # Add to table
            table.add_row(
                [
                    symbol.symbol_name,
                    f"{metrics.best_bid:,.2f}",
                    f"{metrics.best_ask:,.2f}",
                    f"{metrics.spread_pct:.3f}%",
                    _format_volume(metrics.bid_volume_2pct),
                    _format_volume(metrics.ask_volume_2pct),
                    f"{metrics.bid_ask_ratio:.2f} {indicator}",
                    _format_volume(metrics.largest_bid_wall),
                    _format_volume(metrics.largest_ask_wall),
                ],
            )

            successful += 1

        except (KeyError, ValueError, TypeError, AttributeError) as e:
            app_logger.error(f"Error processing order book for {symbol.symbol_name}: {e!s}")
            failed += 1

    app_logger.info(f"Order book data fetch complete: {successful} successful, {failed} failed")

    return table


def _get_cvd_indicator(cvd: float, total_volume: float) -> str:
    """Get emoji indicator based on CVD relative to volume.

    Args:
        cvd: Cumulative Volume Delta value
        total_volume: Total buy + sell volume for reference

    Returns:
        Emoji string: 🟢 (bullish), 🔴 (bearish), ⚪ (neutral)

    """
    if total_volume == 0:
        return "⚪"

    cvd_ratio = abs(cvd) / total_volume

    if cvd_ratio > CVD_STRONG_THRESHOLD:
        return "🟢" if cvd > 0 else "🔴"
    return "⚪"


def fetch_cvd_report(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> PrettyTable:
    """Fetch Cumulative Volume Delta (order flow) for all symbols.

    Args:
        symbols: List of Symbol objects to fetch data for
        conn: Database connection

    Returns:
        PrettyTable with CVD order flow data

    """
    repo = CVDRepository(conn)

    table = PrettyTable()
    table.field_names = [
        "Symbol",
        "CVD 1h",
        "CVD 4h",
        "CVD 24h",
        "Buy Vol",
        "Sell Vol",
        "Trades/h",
        "Lg Buys",
        "Lg Sells",
    ]
    table.align["Symbol"] = "l"
    table.align["CVD 1h"] = "r"
    table.align["CVD 4h"] = "r"
    table.align["CVD 24h"] = "r"
    table.align["Buy Vol"] = "r"
    table.align["Sell Vol"] = "r"
    table.align["Trades/h"] = "r"
    table.align["Lg Buys"] = "r"
    table.align["Lg Sells"] = "r"

    indicator_date = datetime.now(UTC)
    successful = 0
    failed = 0

    for symbol in symbols:
        # Only fetch for Binance symbols
        if symbol.source_id != SourceID.BINANCE:
            continue

        try:
            metrics = fetch_binance_cvd(symbol, hours=24)

            if metrics is None:
                app_logger.warning(f"No CVD data available for {symbol.symbol_name}")
                failed += 1
                continue

            # Save to database
            repo.save_cvd_metrics(
                symbol.symbol_id,
                metrics,
                indicator_date,
            )

            # Get indicator
            total_vol = metrics.buy_volume_24h + metrics.sell_volume_24h
            indicator = _get_cvd_indicator(metrics.cvd_24h, total_vol)

            # Add to table
            table.add_row(
                [
                    symbol.symbol_name,
                    f"{metrics.cvd_1h:+,.0f}",
                    f"{metrics.cvd_4h:+,.0f}",
                    f"{metrics.cvd_24h:+,.0f} {indicator}",
                    _format_volume(metrics.buy_volume_24h),
                    _format_volume(metrics.sell_volume_24h),
                    f"{metrics.trade_count_1h:,}",
                    str(metrics.large_buy_count),
                    str(metrics.large_sell_count),
                ],
            )

            successful += 1

        except (KeyError, ValueError, TypeError, AttributeError) as e:
            app_logger.error(f"Error processing CVD for {symbol.symbol_name}: {e!s}")
            failed += 1

    app_logger.info(f"CVD data fetch complete: {successful} successful, {failed} failed")

    return table


def _to_float(value: object) -> float:
    """Safely convert a value to float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return 0.0


def build_order_book_ai_context(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> str:
    """Build order book section for AI analysis context.

    Args:
        symbols: List of Symbol objects
        conn: Database connection

    Returns:
        Formatted string for AI analysis context

    """
    repo = OrderBookRepository(conn)
    lines = ["Order Book Liquidity Analysis:"]

    for symbol in symbols:
        if symbol.source_id != SourceID.BINANCE:
            continue

        try:
            metrics = repo.get_latest_order_book_metrics(symbol.symbol_id)

            if metrics is None:
                continue

            ratio = _to_float(metrics.get("bid_ask_ratio", 0))
            spread = _to_float(metrics.get("spread_pct", 0))
            bid_wall = _to_float(metrics.get("largest_bid_wall", 0))
            bid_wall_price = _to_float(metrics.get("largest_bid_wall_price", 0))
            ask_wall = _to_float(metrics.get("largest_ask_wall", 0))
            ask_wall_price = _to_float(metrics.get("largest_ask_wall_price", 0))

            # Determine pressure direction
            if ratio > RATIO_BUY_PRESSURE:
                pressure = "buy pressure"
            elif ratio < RATIO_SELL_PRESSURE:
                pressure = "sell pressure"
            else:
                pressure = "neutral"

            line = f"{symbol.symbol_name}: B/A Ratio {ratio:.2f} ({pressure}), spread {spread:.3f}%"

            # Add wall info if significant
            if bid_wall > MIN_SIGNIFICANT_WALL:
                line += f", bid wall at ${bid_wall_price:,.0f} ({_format_volume(bid_wall)})"
            if ask_wall > MIN_SIGNIFICANT_WALL:
                line += f", ask wall at ${ask_wall_price:,.0f} ({_format_volume(ask_wall)})"

            lines.append(line)

        except (KeyError, ValueError, TypeError) as e:
            app_logger.warning(f"Error building AI context for {symbol.symbol_name}: {e!s}")

    # Add interpretation guidance
    lines.append("")
    lines.append("Interpretation:")
    lines.append("- Bid/Ask Ratio > 1.2 = Strong buying pressure (bullish short-term)")
    lines.append("- Bid/Ask Ratio < 0.8 = Strong selling pressure (bearish short-term)")
    lines.append("- Liquidity walls indicate potential support (bid) or resistance (ask) levels")
    lines.append("- Wider spreads indicate lower liquidity and higher volatility risk")

    return "\n".join(lines)


def build_cvd_ai_context(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> str:
    """Build CVD (Cumulative Volume Delta) section for AI analysis context.

    Args:
        symbols: List of Symbol objects
        conn: Database connection

    Returns:
        Formatted string for AI analysis context

    """
    repo = CVDRepository(conn)
    lines = ["Order Flow Analysis (Cumulative Volume Delta):"]

    for symbol in symbols:
        if symbol.source_id != SourceID.BINANCE:
            continue

        try:
            metrics = repo.get_latest_cvd_metrics(symbol.symbol_id)

            if metrics is None:
                continue

            cvd_1h = _to_float(metrics.get("cvd_1h", 0))
            cvd_24h = _to_float(metrics.get("cvd_24h", 0))
            buy_vol = _to_float(metrics.get("buy_volume_24h", 0))
            sell_vol = _to_float(metrics.get("sell_volume_24h", 0))
            large_buys = int(_to_float(metrics.get("large_buy_count", 0)))
            large_sells = int(_to_float(metrics.get("large_sell_count", 0)))

            # Determine flow direction
            total_vol = buy_vol + sell_vol
            if total_vol > 0:
                cvd_pct = (cvd_24h / total_vol) * 100
                if cvd_pct > CVD_STRONG_PCT:
                    flow = "strong buying"
                elif cvd_pct > CVD_MODERATE_PCT:
                    flow = "moderate buying"
                elif cvd_pct < -CVD_STRONG_PCT:
                    flow = "strong selling"
                elif cvd_pct < -CVD_MODERATE_PCT:
                    flow = "moderate selling"
                else:
                    flow = "balanced"
            else:
                flow = "no data"
                cvd_pct = 0

            line = (
                f"{symbol.symbol_name}: CVD 24h {_format_volume(cvd_24h)} ({flow}), "
                f"1h trend {'+' if cvd_1h > 0 else ''}{_format_volume(cvd_1h)}"
            )

            # Add large trade imbalance if significant
            if large_buys > large_sells * 1.5:
                line += f", {large_buys} large buys vs {large_sells} sells (bullish whales)"
            elif large_sells > large_buys * 1.5:
                line += f", {large_sells} large sells vs {large_buys} buys (bearish whales)"

            lines.append(line)

        except (KeyError, ValueError, TypeError) as e:
            app_logger.warning(f"Error building CVD context for {symbol.symbol_name}: {e!s}")

    # Add interpretation guidance
    lines.append("")
    lines.append("CVD Interpretation:")
    lines.append("- Positive CVD = Net buying pressure (takers buying from makers)")
    lines.append("- Negative CVD = Net selling pressure (takers selling to makers)")
    lines.append("- Rising CVD + Rising Price = Trend confirmation (strong)")
    lines.append("- Rising CVD + Falling Price = Potential reversal (accumulation)")
    lines.append("- Falling CVD + Rising Price = Potential reversal (distribution)")
    lines.append("- Large trade imbalance shows institutional activity direction")

    return "\n".join(lines)


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    print("=== Order Book Report ===")
    table = fetch_order_book_report(symbols, conn)
    print(table)

    print("\n=== CVD Report ===")
    cvd_table = fetch_cvd_report(symbols, conn)
    print(cvd_table)

    print("\n--- Order Book AI Context ---")
    ai_context = build_order_book_ai_context(symbols, conn)
    print(ai_context)

    print("\n--- CVD AI Context ---")
    cvd_context = build_cvd_ai_context(symbols, conn)
    print(cvd_context)
