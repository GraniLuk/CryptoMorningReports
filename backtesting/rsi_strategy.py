from decimal import Decimal

import pandas as pd

from source_repository import fetch_symbols
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi


def run_backtest(
    symbol_id: int,
    candles_data,
    rsi_value: int,
    tp_value: Decimal,
    sl_value: Decimal,
    daysAfterToBuy: int,
):
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
                f"Started position for symbol {symbol_id} on date {entry_date} with entry price {entry_price}"
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
                        f"Closed position ❤️ for symbol {symbol_id} at date {current_date} with price {current_high}"
                    )
                    break
                elif current_low <= sl_price:
                    outcome = "SL"
                    close_date = current_date
                    close_price = current_low
                    days_taken = (current_date - entry_date).days
                    print(
                        f"Closed position 💀 for symbol {symbol_id} at date {current_date} with price {current_low}"
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
                    }
                )

            active_trade = False

    # Analyze results
    results_df = pd.DataFrame(trades)
    if not results_df.empty:
        summary = results_df.groupby("trade_outcome").agg(
            count=("trade_outcome", "size"), avg_days=("days", "mean")
        )

        print(f"\nBacktest Results for symbol {symbol_id}:")
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
    else:
        print(
            f"\nNo trades were executed for symbol {symbol_id} during the backtest period."
        )

    # Save trades results to Excel for further analysis
    excel_filename = f"trades_results_symbol_{symbol_id}.xlsx"
    results_df.to_excel(excel_filename, index=False)
    print(f"\nTrades results for symbol {symbol_id} saved to '{excel_filename}'.")

    return results_df


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    load_dotenv()
    conn = connect_to_sql()

    symbol_ratios = {}
    symbols = fetch_symbols(conn)
    # Loop over symbols 1 to 16
    for symbol_id in [symbol.symbol_id for symbol in symbols]:
        candles_data = get_candles_with_rsi(conn, symbol_id)
        results_df = run_backtest(
            symbol_id, candles_data, 30, Decimal("1.1"), Decimal("0.9"), 1
        )
        if results_df.empty:
            ratio = 0.0
        else:
            total_trades = len(results_df)
            tp_trades = len(results_df[results_df["trade_outcome"] == "TP"])
            ratio = tp_trades / total_trades
        symbol_ratios[symbol_id] = ratio
        print(f"Symbol {symbol_id}: TP Ratio = {ratio:.2f}\n")

    # Compare results across symbols
    best_symbol = max(symbol_ratios, key=symbol_ratios.get)
    print("Summary of TP Ratios:")
    for symbol, ratio in symbol_ratios.items():
        print(f"Symbol {symbol}: {ratio:.2f}")

    print(
        f"\nBest performing symbol: {best_symbol} with a TP ratio of {symbol_ratios[best_symbol]:.2f}"
    )
