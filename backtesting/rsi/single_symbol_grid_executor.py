import itertools
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd

from backtesting.rsi.excel import save_to_excel
from backtesting.rsi.strategy import run_strategy_for_symbol_internal
from source_repository import fetch_symbols
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi


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

    # Calculate the date 4 years before today
    five_years_ago = datetime.now() - timedelta(days=5 * 365)

    # Assuming you have a valid connection and symbol_id
    candles_data = get_candles_with_rsi(conn, symbol.symbol_id, five_years_ago)

    for rsi_value, tp_value, sl_value, daysAfterToBuy in itertools.product(
        rsi_range, tp_values, sl_values, days_options
    ):
        print(
            f"\nRunning strategy for {symbol.symbol_name} with parameters: RSI = {rsi_value}, TP = {tp_value}, SL = {sl_value}, daysAfterToBuy = {daysAfterToBuy}"
        )
        results_df, ratio = run_strategy_for_symbol_internal(
            candles_data, symbol, rsi_value, tp_value, sl_value, daysAfterToBuy
        )

        if not results_df.empty:
            total_profit = results_df["profit"].sum()
            tp_hits = len(results_df[results_df["trade_outcome"] == "TP"])
            sl_hits = len(results_df[results_df["trade_outcome"] == "SL"])
        else:
            total_profit = 0.0
            tp_hits = 0
            sl_hits = 0

        results.append(
            {
                "rsi_value": rsi_value,
                "tp_value": tp_value,
                "sl_value": sl_value,
                "daysAfterToBuy": daysAfterToBuy,
                "total_profit": total_profit,
                "trades": len(results_df),
                "TP_ratio": ratio,
                "TP_hits": tp_hits,
                "SL_hits": sl_hits,
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
        filtered_symbols = [symbol for symbol in symbols if symbol.symbol_name == "XRP"]
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
