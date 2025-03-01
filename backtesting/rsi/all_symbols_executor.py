from decimal import Decimal

import pandas as pd

from backtesting.rsi.excel import save_to_excel
from backtesting.rsi.strategy import run_strategy_for_symbol_internal
from source_repository import fetch_symbols


def run_strategy_for_all_symbols(
    conn,
    rsi_value: int = 30,
    tp_value: Decimal = Decimal("1.1"),
    sl_value: Decimal = Decimal("0.9"),
    daysAfterToBuy: int = 1,
):
    """
    Executes the strategy for all symbols.
    Returns a dictionary with each symbol name and its TP ratio, and a combined DataFrame of all trades.
    """
    symbol_ratios = {}
    all_trades_df = pd.DataFrame()  # Create empty DataFrame to store all results
    symbols = fetch_symbols(conn)

    # Loop over fetched symbols
    for symbol in symbols:
        results_df, ratio = run_strategy_for_symbol_internal(
            conn, symbol, rsi_value, tp_value, sl_value, daysAfterToBuy
        )
        symbol_ratios[symbol.symbol_name] = ratio
        print(f"{symbol.symbol_name}: TP Ratio = {ratio:.2f}\n")

        # Append results to combined DataFrame
        if not results_df.empty:
            all_trades_df = pd.concat([all_trades_df, results_df], ignore_index=True)

    if not all_trades_df.empty:
        save_to_excel(all_trades_df, "all_symbols_strategy_results")

    return symbol_ratios, all_trades_df
