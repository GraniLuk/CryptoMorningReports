from decimal import Decimal

import pandas as pd

from source_repository import Symbol


def run_backtest(
    symbol: Symbol,
    candles_data,
    rsi_value: int,
    tp_value: Decimal,
    sl_value: Decimal,
    daysAfterToBuy: int,
    position_type: str = "LONG",  # New parameter
):
    if position_type not in ["LONG", "SHORT"]:
        raise ValueError("position_type must be either 'LONG' or 'SHORT'")

    symbol_id = symbol.symbol_id
    symbol_name = symbol.symbol_name
    investment_value = 1000

    # Fetch data from database
    df = pd.DataFrame(candles_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Generate trading signals based on position type
    if position_type == "LONG":
        # Signal for long: RSI crosses above threshold
        df["signal"] = (df["RSI"] >= rsi_value) & (df["RSI"].shift(1) < rsi_value)
    else:
        # Signal for short: RSI crosses below threshold
        df["signal"] = (df["RSI"] <= rsi_value) & (df["RSI"].shift(1) > rsi_value)

    trades = []
    active_trade = False

    for i in range(len(df)):
        if not active_trade and df.loc[i, "signal"] and (i + daysAfterToBuy < len(df)):
            active_trade = True
            entry_date = df.loc[i + daysAfterToBuy, "date"]
            entry_price = df.loc[i + daysAfterToBuy, "Open"]
            print(
                f"Started {position_type} position for {symbol_name} on date {entry_date} with entry price {entry_price}"
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

                if position_type == "LONG":
                    if current_high >= tp_price:
                        outcome = "TP"
                        close_price = tp_price
                        profit = investment_value * (tp_value - Decimal("1"))
                    elif current_low <= sl_price:
                        outcome = "SL"
                        close_price = sl_price
                        profit = -investment_value * (Decimal("1") - sl_value)
                else:  # SHORT position
                    if current_low <= tp_price:
                        outcome = "TP"
                        close_price = tp_price
                        profit = investment_value * (
                            Decimal("1") - (Decimal("2") - tp_value)
                        )
                    elif current_high >= sl_price:
                        outcome = "SL"
                        close_price = sl_price
                        profit = -investment_value * (
                            (Decimal("2") - sl_value) - Decimal("1")
                        )

                if outcome:
                    days_taken = (current_date - entry_date).days
                    emoji = "❤️" if outcome == "TP" else "💀"
                    profit_str = "profit" if profit > 0 else "loss"
                    print(
                        f"Closed {position_type} position {emoji} for {symbol_name} at date {current_date} "
                        f"with price {close_price} and {profit_str} of {abs(profit):.2f}"
                    )
                    active_trade = False  # Reset flag when trade is closed
                    break

            if outcome:
                trades.append(
                    {
                        "symbolId": symbol_id,
                        "position_type": position_type,
                        "open_date": entry_date,
                        "open_price": entry_price,
                        "close_date": close_date,
                        "close_price": close_price,
                        "trade_outcome": outcome,
                        "days": days_taken,
                        "profit": profit,
                    }
                )

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


def run_strategy_for_symbol_internal(
    candles_data,
    symbol,
    rsi_value: int = 30,
    tp_value: Decimal = Decimal("1.1"),
    sl_value: Decimal = Decimal("0.9"),
    daysAfterToBuy: int = 1,
    position_type: str = "LONG",
):
    """
    Internal function that executes the strategy for a single symbol.
    Returns the results DataFrame and the TP ratio.
    """
    # Run backtest
    results_df = run_backtest(
        symbol,
        candles_data,
        rsi_value,
        tp_value,
        sl_value,
        daysAfterToBuy,
        position_type,
    )

    # Calculate TP ratio if there are trades
    if not results_df.empty:
        tp_count = len(results_df[results_df["trade_outcome"] == "TP"])
        total_trades = len(results_df)
        ratio = tp_count / total_trades if total_trades > 0 else 0
    else:
        ratio = 0

    return results_df, ratio
