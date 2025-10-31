"""Market capitalization analysis and reporting for cryptocurrency markets."""

from http import HTTPStatus

import requests
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.repositories.marketcap_repository import save_marketcap_results


def fetch_marketcap_report(symbols: list[Symbol], conn) -> PrettyTable:
    """Fetch and generate a market capitalization report for cryptocurrency symbols."""
    results = []
    missing_symbols = []

    # Get all market caps in one API call
    symbol_ids = ",".join([s.coingecko_name.lower() for s in symbols])
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": symbol_ids,
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == HTTPStatus.OK:
            data = response.json()

            # Create lookup dictionary
            market_caps = {coin["id"]: coin["market_cap"] for coin in data}

            for crypto in symbols:
                market_cap = market_caps.get(crypto.coingecko_name.lower(), 0)

                if market_cap > 0:
                    results.append(
                        {
                            "symbol": crypto.symbol_name,
                            "symbol_id": crypto.symbol_id,
                            "name": crypto.full_name,
                            "market_cap": market_cap,
                        }
                    )
                else:
                    missing_symbols.append(crypto.symbol_name)
    except Exception as e:
        app_logger.error(f"Error fetching market caps: {e}")

    # Sort results by market cap descending
    sorted_results = sorted(results, key=lambda x: x["market_cap"], reverse=True)

    # Create and format PrettyTable
    table = PrettyTable()
    table.field_names = ["Symbol", "Market Cap (USD)"]
    table.align["Symbol"] = "l"
    table.align["Market Cap (USD)"] = "r"

    for result in sorted_results:
        market_cap = f"${result['market_cap']:,.2f}"
        table.add_row([result["symbol"], market_cap])

    # Save results (assuming similar structure as volume_repository)
    save_marketcap_results(conn, sorted_results)

    return table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    table = fetch_marketcap_report(symbols, conn)
