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
    df["signal"] = (df["RSI"] <= rsi_value) & (
        df["RSI"].shift(daysAfterToBuy) > rsi_value
    )

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

                if current_high >= tp_price:
                    outcome = "TP"
                    close_date = current_date
                    close_price = current_high
                    days_taken = (current_date - entry_date).days
                    print(
                        f"Closed position ❤️ for {symbol_name} at date {current_date} with price {current_high}"
                    )
                    break
                elif current_low <= sl_price:
                    outcome = "SL"
                    close_date = current_date
                    close_price = current_low
                    days_taken = (current_date - entry_date).days
                    print(
                        f"Closed position 💀 for {symbol_name} at date {current_date} with price {current_low}"
                    )
                    break

            if outcome:
                # Calculate profit for this trade based on a 1000$ investment.
                if outcome == "TP":
                    profit = investment_value * (tp_value - 1)
                elif outcome == "SL":
                    profit = investment_value * (
                        sl_value - 1
                    )  # will be negative if sl_value < 1
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

    # Save trades results to Excel for further analysis
    excel_filename = f"trades_results_{symbol_name}.xlsx"
    results_df.to_excel(excel_filename, index=False)
    print(f"\nTrades results for {symbol_name} saved to '{excel_filename}'.")

    return results_df


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
    # Calculate the date 4 years before today
    five_years_ago = datetime.now() - timedelta(days=5 * 365)

    # Assuming you have a valid connection and symbol_id
    candles_data = get_candles_with_rsi(conn, symbol.symbol_id, five_years_ago)
    results_df = run_backtest(
        symbol, candles_data, rsi_value, tp_value, sl_value, daysAfterToBuy
    )
    if results_df.empty:
        ratio = 0.0
    else:
        total_trades = len(results_df)
        tp_trades = len(results_df[results_df["trade_outcome"] == "TP"])
        ratio = tp_trades / total_trades
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
    Returns a dictionary with each symbol name and its TP ratio.
    """
    symbol_ratios = {}
    symbols = fetch_symbols(conn)
    # Loop over fetched symbols
    for symbol in symbols:
        _, ratio = run_strategy_for_symbol(
            conn, symbol, rsi_value, tp_value, sl_value, daysAfterToBuy
        )
        symbol_ratios[symbol.symbol_name] = ratio
        print(f"{symbol.symbol_name}: TP Ratio = {ratio:.2f}\n")
    return symbol_ratios


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    load_dotenv()
    conn = connect_to_sql()

    # # Option 1: Execute for all symbols
    # symbol_ratios = run_strategy_for_all_symbols(conn)
    # print("Summary of TP Ratios:")
    # for name, ratio in symbol_ratios.items():
    #     print(f"{name}: {ratio:.2f}")

    # best_symbol = max(symbol_ratios, key=symbol_ratios.get)
    # print(
    #     f"\nBest performing symbol: {best_symbol} with a TP ratio of {symbol_ratios[best_symbol]:.2f}"
    # )

    # Option 2: Execute for a single symbol (uncomment below to run for just one symbol)
    symbols = fetch_symbols(conn)
    if symbols:
        filtered_symbols = [symbol for symbol in symbols if symbol.symbol_name == "SOL"]
        _, ratio = run_strategy_for_symbol(conn, filtered_symbols[0])
        print(f"{filtered_symbols[0].symbol_name}: TP Ratio = {ratio:.2f}")
