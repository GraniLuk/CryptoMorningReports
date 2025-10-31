"""RSI grid search backtesting executor for all cryptocurrency symbols."""

import pandas as pd

from backtesting.rsi.excel import save_to_excel
from backtesting.rsi.single_symbol_grid_executor import run_grid_search_for_symbol
from source_repository import fetch_symbols


def run_grid_search_for_all_symbols(conn):
    """Execute the grid search for all symbols.

    Returns a combined list of dictionaries containing symbol name, parameters, and total profit.
    """
    all_results = []
    symbols = fetch_symbols(conn)
    if not symbols:
        return all_results

    for symbol in symbols:
        grid_results = run_grid_search_for_symbol(conn, symbol)
        for res in grid_results:
            res["symbol_name"] = symbol.symbol_name
        all_results.extend(grid_results)

    if all_results:
        grid_df = pd.DataFrame(all_results)
        save_to_excel(grid_df, "all_symbols_grid_search_results")

    return all_results


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    load_dotenv()
    conn = connect_to_sql()

    # Run grid search for all symbols
    combined_results = run_grid_search_for_all_symbols(conn)

    if combined_results:
        # Create a DataFrame for easier analysis
        grid_df = pd.DataFrame(combined_results)

        # Find the best overall strategy across all symbols
        best = grid_df.loc[grid_df["total_profit"].idxmax()]
    else:
        pass
