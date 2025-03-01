import itertools
from decimal import Decimal

import pandas as pd

from backtesting.rsi.excel import save_to_excel
from backtesting.rsi.rsi_strategy import run_strategy_for_symbol_internal
from source_repository import fetch_symbols


def run_grid_search_for_symbol(conn, symbol):
    """
    Execute the strategy for a single symbol over a range of parameter combinations.
    Returns a list of dictionaries containing the parameters and the corresponding total profit.
    """
    results = []

    rsi_range = range(20, 41)  # 20 to 40 inclusive
    tp_values = [Decimal(val) for val in ["1.05", "1.1", "1.15", "1.2"]]
    sl_values = [Decimal(val) for val in ["1.05", "1.1", "1.15", "1.2"]]
    days_options = [0, 1]

    for rsi_value, tp_value, sl_value, daysAfterToBuy in itertools.product(
        rsi_range, tp_values, sl_values, days_options
    ):
        print(
            f"\nRunning strategy for {symbol.symbol_name} with parameters: RSI = {rsi_value}, TP = {tp_value}, SL = {sl_value}, daysAfterToBuy = {daysAfterToBuy}"
        )
        results_df, _ = run_strategy_for_symbol_internal(
            conn, symbol, rsi_value, tp_value, sl_value, daysAfterToBuy
        )

        if not results_df.empty:
            total_profit = results_df["profit"].sum()
        else:
            total_profit = 0.0

        results.append(
            {
                "rsi_value": rsi_value,
                "tp_value": tp_value,
                "sl_value": sl_value,
                "daysAfterToBuy": daysAfterToBuy,
                "total_profit": total_profit,
            }
        )

    grid_df = pd.DataFrame(results)
    if not grid_df.empty:
        save_to_excel(grid_df, "grid_search_results", symbol.symbol_name)

    return results


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    load_dotenv()
    conn = connect_to_sql()
    # Option 3: Run grid search for a single symbol
    # For grid search, choose a symbol. For example, filter by symbol name "SOL"
    symbols = fetch_symbols(conn)
    if symbols:
        filtered_symbols = [symbol for symbol in symbols if symbol.symbol_name == "SOL"]
        symbol_to_test = filtered_symbols[0] if filtered_symbols else symbols[0]

        # Run grid search for the selected symbol
        grid_results = run_grid_search_for_symbol(conn, symbol_to_test)

        # Convert grid results into a DataFrame to ease the analysis and print the best parameter set based on total profit.
        grid_df = pd.DataFrame(grid_results)
        print("\nGrid Search Summary (sorted by total profit):")
        print(grid_df.sort_values("total_profit", ascending=False))

        # Best performing parameter combination (if any trades took place)
        best = grid_df.loc[grid_df["total_profit"].idxmax()]
        print(
            f"\nBest performing parameters for {symbol_to_test.symbol_name}:\n"
            f"RSI: {best['rsi_value']}, TP: {best['tp_value']}, SL: {best['sl_value']}, daysAfterToBuy: {best['daysAfterToBuy']}, "
            f"Total Profit: {best['total_profit']}"
        )
    else:
        print("No symbols found for grid search.")
