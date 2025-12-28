"""SOPR (Spent Output Profit Ratio) analysis and data fetching."""

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import requests
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from technical_analysis.repositories.sopr_repository import save_sopr_results


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


# Configuration
API_BASE = "https://bitcoin-data.com/"


def _fetch_sopr_data(endpoint: str, date_str: str) -> dict | None:
    """Fetch SOPR data from a specific endpoint."""
    try:
        response = requests.get(f"{API_BASE}/v1/{endpoint}", params={"day": date_str}, timeout=10)
        if response.status_code != HTTPStatus.OK:
            app_logger.warning(f"{endpoint.upper()} API error (status {response.status_code})")
            return None
        data = response.json()
        if not data or len(data) == 0:
            app_logger.warning(f"{endpoint.upper()} API returned empty data for {date_str}")
            return None
        return data[0]
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        app_logger.error(f"Error fetching {endpoint}: {e!s}")
        return None


def fetch_sopr_metrics(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
) -> PrettyTable | None:
    """Retrieve yesterday's SOPR variants from BGeometrics API and saves to database.

    Args:
        conn: Database connection

    Returns:
        PrettyTable: containing formatted table for display

    """
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Check rate limit first
    response = requests.get(f"{API_BASE}/v1/sopr", params={"day": yesterday}, timeout=10)
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        app_logger.warning(
            "SOPR API rate limit exceeded (5 requests/hour for free tier). "
            "Skipping SOPR metrics this run.",
        )
        return None

    # Fetch all metrics
    metrics = {}
    endpoints = ["sopr", "sth-sopr", "lth-sopr"]
    names = ["SOPR", "STH-SOPR", "LTH-SOPR"]

    for endpoint, name in zip(endpoints, names, strict=True):
        data = _fetch_sopr_data(endpoint, yesterday)
        if data is None:
            return None  # Early return on any failure
        metrics[name] = data

    # Create and return table
    table = PrettyTable()
    table.field_names = ["Indicator", "Value"]
    table.align["Indicator"] = "l"  # Left align indicator names
    table.align["Value"] = "r"  # Right align values

    for metric, data in metrics.items():
        value = data.get("sopr") or data.get("sthSopr") or data.get("lthSopr")
        if value is None:
            app_logger.warning(f"No value found for {metric}, skipping")
            continue
        value = float(value)
        table.add_row([metric, f"{value:.4f}"])

    # Save results to database
    if conn:
        # Filter out metrics with no valid values
        filtered_metrics = {
            name: data
            for name, data in metrics.items()
            if (data.get("sopr") or data.get("sthSopr") or data.get("lthSopr")) is not None
        }
        if filtered_metrics:
            save_sopr_results(conn, filtered_metrics)
            app_logger.info("SOPR metrics fetched and saved successfully")
        else:
            app_logger.warning("No valid SOPR metrics to save")

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
