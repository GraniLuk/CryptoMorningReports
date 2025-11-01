"""SOPR (Spent Output Profit Ratio) analysis and data fetching."""

from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import requests
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from technical_analysis.repositories.sopr_repository import save_sopr_results


# Configuration
API_BASE = "https://bitcoin-data.com/"


def fetch_sopr_metrics(conn) -> PrettyTable | None:
    """Retrieve yesterday's SOPR variants from BGeometrics API and saves to database.

    Args:
        conn: Database connection

    Returns:
        PrettyTable: containing formatted table for display

    """
    metrics = {}
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        # Fetch base SOPR
        response = requests.get(f"{API_BASE}/v1/sopr", params={"day": yesterday}, timeout=10)

        # Check for rate limiting or other HTTP errors
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            app_logger.warning(
                "SOPR API rate limit exceeded (5 requests/hour for free tier). "
                "Skipping SOPR metrics this run.",
            )
            return None
        if response.status_code != HTTPStatus.OK:
            app_logger.error(f"SOPR API returned status {response.status_code}: {response.text}")
            return None

        metrics["SOPR"] = response.json()[0]

        # Fetch STH-SOPR
        response = requests.get(f"{API_BASE}/v1/sth-sopr", params={"day": yesterday}, timeout=10)
        if response.status_code != HTTPStatus.OK:
            app_logger.warning(f"STH-SOPR API error (status {response.status_code}), skipping")
            return None
        metrics["STH-SOPR"] = response.json()[0]

        # Fetch LTH-SOPR
        response = requests.get(f"{API_BASE}/v1/lth-sopr", params={"day": yesterday}, timeout=10)
        if response.status_code != HTTPStatus.OK:
            app_logger.warning(f"LTH-SOPR API error (status {response.status_code}), skipping")
            return None
        metrics["LTH-SOPR"] = response.json()[0]

    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        app_logger.error(f"Error fetching SOPR metrics: {e!s}")
        return None
    else:
        # Create pretty table for display
        table = PrettyTable()
        table.field_names = ["Indicator", "Value"]
        table.align["Indicator"] = "l"  # Left align indicator names
        table.align["Value"] = "r"  # Right align values

        for metric, data in metrics.items():
            value = float(data.get("sopr") or data.get("sthSopr") or data.get("lthSopr"))
            table.add_row([metric, f"{value:.4f}"])

        # Save results to database
        if conn:
            save_sopr_results(conn, metrics)
            app_logger.info("SOPR metrics fetched and saved successfully")

        return table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    load_dotenv()
    conn = connect_to_sql()
    table = fetch_sopr_metrics(conn)
    if table:
        pass
    else:
        pass
