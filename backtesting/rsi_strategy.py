import itertools
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd

from source_repository import Symbol, fetch_symbols
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi


def run_backtest(
    symbol: Symbol,  # Expecting a Symbol instance with attributes symbol_id and symbol_name
    candles_data,
    rsi_value: int,
    tp_value: Decimal,
    sl_value: Decimal,
    daysAfterToBuy: int,
):
    symbol_id = symbol.symbol_id  # use only for data retrieval
    symbol_name = symbol.symbol_name
    investment_value = 1000

    # Fetch data from database
    df = pd.DataFrame(candles_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Generate trading signals
    df["signal"] = (df["RSI"] <= rsi_value) & (df["RSI"].shift(1) > rsi_value)

    trades = []
    active_trade = False

    for i in range(len(df)):
        if not active_trade and df.loc[i, "signal"] and (i + daysAfterToBuy < len(df)):
            active_trade = True
            entry_date = df.loc[i + daysAfterToBuy, "date"]
            entry_price = df.loc[i + daysAfterToBuy, "Open"]
            print(
                f"Started position for {symbol_name} on date {entry_date} with entry price {entry_price}"
            )
            tp_price = entry_price * tp_value
            sl_price = entry_price * sl_value

            outcome = None
            days_taken = 0
            close_date = None
            close_price = None

            for j in range(i + daysAfterToBuy, len(df)):
                current_high = df.loc[j, "High"]
                current_low = df.loc[j, "Low"]
                current_date = df.loc[j, "date"]
                close_date = current_date

                if current_high >= tp_price:
                    outcome = "TP"
                    close_price = entry_price * tp_value
                    days_taken = (current_date - entry_date).days
                    profit = investment_value * tp_value - investment_value
                    print(
                        f"Closed position ❤️ for {symbol_name} at date {current_date} with price {current_high} and profit of {profit:.2f}"
                    )
                    break
                elif current_low <= sl_price:
                    outcome = "SL"
                    close_price = entry_price * sl_value
                    days_taken = (current_date - entry_date).days
                    profit = -(investment_value * sl_value - investment_value)
                    print(
                        f"Closed position 💀 for {symbol_name} at date {current_date} with price {current_low} and loss of {profit:.2f}"
                    )
                    break

            if outcome:
                trades.append(
                    {
                        "symbolId": symbol_id,
                        "open_date": entry_date,
                        "open_price": entry_price,
                        "close_date": close_date,
                        "close_price": close_price,
                        "trade_outcome": outcome,
                        "days": days_taken,
                        "profit": profit,
                    }
                )

            active_trade = False

    # Analyze results
    results_df = pd.DataFrame(trades)
    if not results_df.empty:
        # Add symbol name column to results
        results_df["symbol_name"] = symbol_name

        total_profit = results_df["profit"].sum()
        summary = results_df.groupby("trade_outcome").agg(
            count=("trade_outcome", "size"), avg_days=("days", "mean")
        )

        print(f"\nBacktest Results for {symbol_name}:")
        print(f"Total trades: {len(results_df)}")
        print(
            f"Take Profit hits: {summary.loc['TP', 'count']}"
            if "TP" in summary.index
            else "Take Profit hits: 0"
        )
        print(
            f"Stop Loss hits: {summary.loc['SL', 'count']}"
            if "SL" in summary.index
            else "Stop Loss hits: 0"
        )
        print(
            f"Average days to TP: {summary.loc['TP', 'avg_days']:.1f}"
            if "TP" in summary.index
            else ""
        )
        print(
            f"Average days to SL: {summary.loc['SL', 'avg_days']:.1f}"
            if "SL" in summary.index
            else ""
        )
        print(f"Total profit for {symbol_name}: ${total_profit:.2f}")
    else:
        print(
            f"\nNo trades were executed for {symbol_name} during the backtest period."
        )

    return results_df


def save_to_excel(df, prefix, symbol_name=None):
    """Helper function to save DataFrame to Excel with consistent naming"""
    current_date = datetime.now().strftime("%Y%m%d")
    if symbol_name:
        filename = f"{prefix}_{symbol_name}_{current_date}.xlsx"
    else:
        filename = f"{prefix}_{current_date}.xlsx"
    df.to_excel(filename, index=False)
    print(f"\nResults saved to '{filename}'")


def run_strategy_for_symbol_internal(
    conn,
    symbol,
    rsi_value: int = 30,
    tp_value: Decimal = Decimal("1.1"),
    sl_value: Decimal = Decimal("0.9"),
    daysAfterToBuy: int = 1,
):
    """
    Internal function that executes the strategy for a single symbol.
    Returns the results DataFrame and the TP ratio.
    """
    # Calculate the date 4 years before today
    five_years_ago = datetime.now() - timedelta(days=5 * 365)

    # Assuming you have a valid connection and symbol_id
    candles_data = get_candles_with_rsi(conn, symbol.symbol_id, five_years_ago)

    # Run backtest
    results_df = run_backtest(
        symbol, candles_data, rsi_value, tp_value, sl_value, daysAfterToBuy
    )

    # Calculate TP ratio if there are trades
    if not results_df.empty:
        tp_count = len(results_df[results_df["trade_outcome"] == "TP"])
        total_trades = len(results_df)
        ratio = tp_count / total_trades if total_trades > 0 else 0
    else:
        ratio = 0

    return results_df, ratio


def run_strategy_for_symbol(
    conn,
    symbol,
    rsi_value: int = 30,
    tp_value: Decimal = Decimal("1.1"),
    sl_value: Decimal = Decimal("0.9"),
    daysAfterToBuy: int = 1,
):
    """
    Executes the strategy for a single symbol.
    Returns the results DataFrame and the TP ratio.
    """
    results_df, ratio = run_strategy_for_symbol_internal(
        conn, symbol, rsi_value, tp_value, sl_value, daysAfterToBuy
    )

    # if not results_df.empty:
    #     save_to_excel(results_df, "strategy_results", symbol.symbol_name)

    return results_df, ratio


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
        results_df, ratio = run_strategy_for_symbol(
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
        results_df, _ = run_strategy_for_symbol(
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
                "total_trades": len(results_df),
            }
        )

    grid_df = pd.DataFrame(results)
    if not grid_df.empty:
        save_to_excel(grid_df, "grid_search_results", symbol.symbol_name)

    return results


def run_grid_search_for_all_symbols(conn):
    """
    Execute the grid search for all symbols.
    Returns a combined list of dictionaries containing symbol name, parameters, and total profit.
    """
    all_results = []
    symbols = fetch_symbols(conn)
    if not symbols:
        print("No symbols found for grid search.")
        return all_results

    for symbol in symbols:
        print(f"\nRunning grid search for symbol {symbol.symbol_name}...")
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
        print("\nCombined Grid Search Summary (sorted by total profit):")
        print(grid_df.sort_values("total_profit", ascending=False))

        # Find the best overall strategy across all symbols
        best = grid_df.loc[grid_df["total_profit"].idxmax()]
        print(
            f"\nBest overall strategy:\n"
            f"Symbol: {best['symbol_name']}\n"
            f"RSI: {best['rsi_value']}, TP: {best['tp_value']}, SL: {best['sl_value']}, daysAfterToBuy: {best['daysAfterToBuy']}\n"
            f"Total Profit: {best['total_profit']}"
        )
    else:
        print("No grid search results found.")
