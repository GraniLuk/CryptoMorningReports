"""RSI-based trading strategy implementation for backtesting."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd

from source_repository import Symbol


if TYPE_CHECKING:
    pass


def run_backtest(  # noqa: PLR0915
    symbol: Symbol,
    candles_data: list[dict],
    rsi_value: int,
    tp_value: Decimal,
    sl_value: Decimal,
    days_after_to_buy: int,
    position_type: str = "LONG",  # New parameter
) -> pd.DataFrame:
    """Run RSI-based backtest on candle data with specified parameters."""
    if position_type not in ["LONG", "SHORT"]:
        msg = "position_type must be either 'LONG' or 'SHORT'"
        raise ValueError(msg)

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
        if not active_trade and df.loc[i, "signal"] and (i + days_after_to_buy < len(df)):
            active_trade = True
            entry_date = datetime.strptime(
                str(df.loc[i + days_after_to_buy, "date"]),
                "%Y-%m-%d",
            ).replace(tzinfo=UTC)
            entry_price = Decimal(str(df.loc[i + days_after_to_buy, "Open"]))

            tp_price = entry_price * tp_value
            sl_price = entry_price * sl_value

            outcome = None
            days_taken = 0
            close_date = None
            close_price = None
            profit = 0  # Initialize profit

            for j in range(i + days_after_to_buy, len(df)):
                current_high = Decimal(str(df.loc[j, "High"]))
                current_low = Decimal(str(df.loc[j, "Low"]))
                current_date = datetime.strptime(str(df.loc[j, "date"]), "%Y-%m-%d").replace(
                    tzinfo=UTC,
                )
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
                elif current_low <= tp_price:
                    outcome = "TP"
                    close_price = tp_price
                    profit = investment_value * (Decimal("1") - (Decimal("2") - tp_value))
                elif current_high >= sl_price:
                    outcome = "SL"
                    close_price = sl_price
                    profit = -investment_value * ((Decimal("2") - sl_value) - Decimal("1"))

                if outcome:
                    days_taken = (current_date - entry_date).days
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
                    },
                )

    # Analyze results
    results_df = pd.DataFrame(trades)
    if not results_df.empty:
        # Add symbol name column to results
        results_df["symbol_name"] = symbol_name

        results_df["profit"].sum()
        results_df.groupby("trade_outcome").agg(
            count=("trade_outcome", "size"),
            avg_days=("days", "mean"),
        )

    else:
        pass

    return results_df


def run_strategy_for_symbol_internal(
    candles_data: list[dict],
    symbol: Symbol,
    rsi_value: int = 30,
    tp_value: Decimal = Decimal("1.1"),
    sl_value: Decimal = Decimal("0.9"),
    days_after_to_buy: int = 1,
    position_type: str = "LONG",
) -> tuple[pd.DataFrame, float]:
    """Execute the strategy for a single symbol.

    Returns the results DataFrame and the TP ratio.
    """
    # Run backtest
    results_df = run_backtest(
        symbol,
        candles_data,
        rsi_value,
        tp_value,
        sl_value,
        days_after_to_buy,
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
