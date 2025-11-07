"""ETF inflows and outflows report generation."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from prettytable import PrettyTable

from etf.etf_fetcher import fetch_defillama_etf_data, parse_etf_data
from etf.etf_repository import ETFRepository
from infra.telegram_logging_handler import app_logger


# Currency formatting constants
BILLION_THRESHOLD = 1_000_000_000
MILLION_THRESHOLD = 1_000_000
THOUSAND_THRESHOLD = 1_000


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


def update_etf_data(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper",
) -> bool:
    """Fetch ETF data from API and save to database (or use cached data if available).

    This method handles the entire ETF data lifecycle:
    1. Check if today's data already exists in the database
    2. If not, fetch from DefiLlama API
    3. Parse and save to database
    4. Return success status

    Args:
        conn: Database connection

    Returns:
        True if data is available (cached or fetched), False otherwise
    """
    try:
        repo = ETFRepository(conn)
        today = datetime.now(UTC).date().isoformat()

        # Check if we already have data for today
        existing_btc = repo.get_latest_etf_flows("BTC")
        existing_eth = repo.get_latest_etf_flows("ETH")

        if (existing_btc and existing_eth and
            existing_btc[0].get("fetch_date") == today):
            app_logger.info("✓ ETF data already cached for today, skipping API fetch")
            return True

        # Fetch fresh data from API
        app_logger.info("📊 Fetching latest ETF data from DefiLlama API...")
        raw_etf_data = fetch_defillama_etf_data()

        if not raw_etf_data:
            app_logger.warning("⚠️ No ETF data returned from API")
            return False

        # Parse and organize ETF data
        organized_data = parse_etf_data(raw_etf_data)
        if not organized_data:
            app_logger.warning("⚠️ Failed to parse ETF data from API")
            return False

        # Save to database
        total_saved = 0
        for coin in ["BTC", "ETH"]:
            if coin in organized_data:
                etf_list = organized_data[coin]
                app_logger.info(f"Processing {len(etf_list)} {coin} ETFs")

                for etf in etf_list:
                    try:
                        repo.save_etf_flow(
                            ticker=etf["ticker"],
                            coin=coin,
                            issuer=etf["issuer"],
                            price=etf["price"],
                            aum=etf["aum"],
                            flows=etf["flows"],
                            flows_change=etf["flows_change"],
                            volume=etf["volume"],
                            fetch_date=etf["fetch_date"],
                        )
                        total_saved += 1
                    except Exception as e:  # noqa: BLE001
                        app_logger.error(f"Failed to save {coin} ETF {etf['ticker']}: {e!s}")
                        continue

        conn.commit()
        app_logger.info(f"✓ ETF data update complete: {total_saved} records saved")

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error updating ETF data: {e!s}")
        return False
    else:
        return total_saved > 0


def fetch_etf_summary_report(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> PrettyTable:
    """Fetch and generate a simplified ETF summary report for BTC and ETH.

    Args:
        conn: Database connection (can be None for testing)

    Returns:
        PrettyTable with aggregated ETF flow data for BTC and ETH
    """
    etf_table = PrettyTable()

    # Set table headers - simplified view with only totals
    etf_table.field_names = [
        "Asset",
        "Daily Flows",
        "7-Day Total",
    ]

    if conn is None:
        # Return empty table for testing when no connection
        app_logger.warning("No database connection provided for ETF summary report")
        etf_table.add_row(["No data", "N/A", "N/A"])
        return etf_table

    try:
        repo = ETFRepository(conn)

        # Process both BTC and ETH
        for coin in ["BTC", "ETH"]:
            # Get latest daily flows
            latest_flows = repo.get_latest_etf_flows(coin)

            # Get 7-day aggregated flows
            weekly_flows = repo.get_weekly_etf_flows(coin, days=7)

            if not latest_flows:
                # Show zero flows if no data
                etf_table.add_row([
                    coin,
                    "$0",
                    "$0",
                ])
                continue

            # Calculate total daily flows
            total_daily_flows = sum(
                float(etf.get("flows", 0) or 0)
                for etf in latest_flows
                if etf.get("flows") is not None
            )

            # Get weekly total
            total_weekly_flows = weekly_flows.get("total_flows", 0) if weekly_flows else 0

            # Format values
            daily_flows_str = _format_currency(total_daily_flows)
            weekly_total_str = _format_currency(total_weekly_flows)

            etf_table.add_row([
                coin,
                daily_flows_str,
                weekly_total_str,
            ])

        app_logger.info("Generated ETF summary report for BTC and ETH")

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error generating ETF summary report: {e!s}")
        # Return error table
        etf_table.add_row(["Error", str(e)[:20], "N/A"])
        return etf_table
    else:
        return etf_table


def fetch_etf_report(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    coin: str = "BTC",
) -> PrettyTable:
    """Fetch and generate an ETF inflows/outflows report for a specific coin.

    Args:
        conn: Database connection (can be None for testing)
        coin: Coin type to report on ('BTC' or 'ETH', default: 'BTC')

    Returns:
        PrettyTable with ETF flow data formatted for display
    """
    if coin.upper() not in ["BTC", "ETH"]:
        msg = f"Invalid coin: {coin}. Must be 'BTC' or 'ETH'"
        raise ValueError(msg)

    coin = coin.upper()
    etf_table = PrettyTable()

    # Set table headers
    etf_table.field_names = [
        "Ticker",
        "Issuer",
        "Price",
        "Daily Flows",
        "7-Day Total",
        "AUM ($B)",
    ]

    if conn is None:
        # Return empty table for testing when no connection
        app_logger.warning("No database connection provided for ETF report")
        etf_table.add_row(["No data", "N/A", "N/A", "N/A", "N/A", "N/A"])
        return etf_table

    try:
        repo = ETFRepository(conn)

        # Get latest daily flows
        latest_flows = repo.get_latest_etf_flows(coin)

        # Get 7-day aggregated flows
        weekly_flows = repo.get_weekly_etf_flows(coin, days=7)

        if not latest_flows:
            app_logger.info(f"No ETF flow data available for {coin}")
            etf_table.add_row(["No data", "N/A", "N/A", "N/A", "N/A", "N/A"])
            return etf_table

        # Add individual ETF rows
        total_daily_flows = 0
        total_weekly_flows = 0

        for etf in latest_flows:
            ticker = etf["ticker"]
            issuer = str(etf["issuer"] or "Unknown")
            price = etf["price"]
            daily_flows = float(etf["flows"] or 0)

            # Get 7-day total for this specific ETF (simplified - using weekly average)
            weekly_total = 0
            days_count = weekly_flows.get("days_count", 0) if isinstance(weekly_flows, dict) else 0
            if days_count > 0:
                # Estimate weekly total based on daily flow and available days
                weekly_total = daily_flows * min(7, days_count)

            aum = float(etf["aum"]) if etf["aum"] is not None else None

            # Format values for display
            price_str = f"${price:,.2f}" if price else "N/A"
            daily_flows_str = _format_currency(daily_flows)
            weekly_total_str = _format_currency(weekly_total)
            aum_str = _format_large_number(aum) if aum else "N/A"

            etf_table.add_row([
                ticker,
                issuer[:12],  # Truncate long issuer names
                price_str,
                daily_flows_str,
                weekly_total_str,
                aum_str,
            ])

            total_daily_flows += daily_flows or 0
            total_weekly_flows += weekly_total

        # Add summary row
        etf_table.add_row([
            "=" * 10,
            "=" * 12,
            "=" * 8,
            "=" * 12,
            "=" * 12,
            "=" * 10,
        ])

        total_daily_str = _format_currency(total_daily_flows)
        total_weekly_str = _format_currency(total_weekly_flows)

        # Add directional indicator
        if total_daily_flows > 0:
            direction_indicator = "↑ INFLOW"
        elif total_daily_flows < 0:
            direction_indicator = "↓ OUTFLOW"
        else:
            direction_indicator = "→ NEUTRAL"

        etf_table.add_row([
            f"TOTAL {coin}",
            f"{direction_indicator}",
            "",
            total_daily_str,
            total_weekly_str,
            "",
        ])

        app_logger.info(
            f"Generated ETF report for {coin}: "
            f"{len(latest_flows)} ETFs, "
            f"total daily flows: {total_daily_str}",
        )

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error generating ETF report for {coin}: {e!s}")
        # Return error table
        etf_table.add_row(["Error", str(e)[:20], "N/A", "N/A", "N/A", "N/A"])
        return etf_table
    else:
        return etf_table


def _format_currency(amount: float) -> str:
    """Format currency amount with appropriate units and colors.

    Args:
        amount: Amount in USD

    Returns:
        Formatted currency string
    """
    if amount == 0:
        return "$0"

    abs_amount = abs(amount)

    # Format based on size
    if abs_amount >= BILLION_THRESHOLD:
        formatted = f"${abs_amount / BILLION_THRESHOLD:.1f}B"
    elif abs_amount >= MILLION_THRESHOLD:
        formatted = f"${abs_amount / MILLION_THRESHOLD:.0f}M"
    elif abs_amount >= THOUSAND_THRESHOLD:
        formatted = f"${abs_amount / THOUSAND_THRESHOLD:.0f}K"
    else:
        formatted = f"${abs_amount:,.0f}"

    # Add directional indicator
    if amount > 0:
        return f"↑ {formatted}"  # Green for inflows
    if amount < 0:
        return f"↓ {formatted}"  # Red for outflows
    return formatted


def _format_large_number(amount: float) -> str:
    """Format large numbers in billions.

    Args:
        amount: Amount in USD

    Returns:
        Formatted string in billions
    """
    if amount >= BILLION_THRESHOLD:
        return f"${amount / BILLION_THRESHOLD:.1f}B"
    if amount >= MILLION_THRESHOLD:
        return f"${amount / MILLION_THRESHOLD:.0f}M"
    return f"${amount:,.0f}"


def get_etf_flow_summary(coin: str, daily_flows: float, weekly_flows: float) -> str:
    """Generate a human-readable summary of ETF flows.

    Args:
        coin: Coin type ('BTC' or 'ETH')
        daily_flows: Total daily flows in USD
        weekly_flows: Total weekly flows in USD

    Returns:
        Summary string for AI analysis or reports
    """
    if daily_flows > 0:
        sentiment = "bullish"
        direction = "inflows"
    elif daily_flows < 0:
        sentiment = "bearish"
        direction = "outflows"
    else:
        sentiment = "neutral"
        direction = "balanced"

    daily_str = _format_currency(daily_flows).replace("↑ ", "").replace("↓ ", "")
    weekly_str = _format_currency(weekly_flows).replace("↑ ", "").replace("↓ ", "")

    institution_type = (
        "accumulation" if daily_flows > 0 else
        "distribution" if daily_flows < 0 else
        "stability"
    )
    return (
        f"{coin} ETF flows show {sentiment} sentiment with {direction} of "
        f"{daily_str} today and {weekly_str} over the past week, indicating "
        f"institutional {institution_type}."
    )


