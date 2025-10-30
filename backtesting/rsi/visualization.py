"""Visualization utilities for RSI backtesting results."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_trading_visualization(
    candles_data: pd.DataFrame,
    results_df: pd.DataFrame,
    symbol_name: str,
    rsi_value: int,
):
    """Create an interactive visualization of trading strategy with candlesticks, RSI, and signals.

    Args:
        candles_data: DataFrame with OHLC and RSI data
        results_df: DataFrame with trading results
        symbol_name: Name of the trading symbol

    """
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{symbol_name} Price", "RSI"),
        row_heights=[0.7, 0.3],
    )

    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=candles_data["date"],
            open=candles_data["Open"],
            high=candles_data["High"],
            low=candles_data["Low"],
            close=candles_data["Close"],
            name="OHLC",
        ),
        row=1,
        col=1,
    )

    # Add RSI
    fig.add_trace(
        go.Scatter(
            x=candles_data["date"],
            y=candles_data["RSI"],
            name="RSI",
            line={"color": "purple"},
        ),
        row=2,
        col=1,
    )

    # Add entry points
    if not results_df.empty:
        # Plot entry points
        fig.add_trace(
            go.Scatter(
                x=results_df["open_date"],
                y=results_df["open_price"],
                mode="markers",
                name="Entry Points",
                marker={"size": 10, "symbol": "triangle-up", "color": "blue"},
            ),
            row=1,
            col=1,
        )

        # Plot exit points colored by outcome
        for outcome in ["TP", "SL"]:
            mask = results_df["trade_outcome"] == outcome
            color = "green" if outcome == "TP" else "red"

            fig.add_trace(
                go.Scatter(
                    x=results_df[mask]["close_date"],
                    y=results_df[mask]["close_price"],
                    mode="markers",
                    name=f"{outcome} Exit",
                    marker={"size": 10, "symbol": "triangle-down", "color": color},
                ),
                row=1,
                col=1,
            )

    # Update layout
    fig.update_layout(
        title=f"{symbol_name} Trading Strategy Analysis",
        yaxis_title="Price",
        yaxis2_title="RSI",
        xaxis_rangeslider_visible=False,
        height=800,
    )

    # Add RSI lines
    fig.add_hline(y=rsi_value, line_width=1, line_dash="dash", line_color="green", row="2", col="1")
    # fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="red", row=2, col=1)

    return fig
