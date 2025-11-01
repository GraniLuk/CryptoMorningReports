"""MACD analysis and reporting for cryptocurrency markets."""

from collections import namedtuple
from datetime import UTC, date, datetime, timedelta

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from shared_code.number_format import format_to_6digits_without_trailing_zeros
from shared_code.price_checker import fetch_daily_candles
from source_repository import SourceID, Symbol
from technical_analysis.repositories.macd_repository import (
    fetch_yesterday_macd,
    save_macd_results,
)


def calculate_macd(symbols: list[Symbol], conn, target_date: date) -> PrettyTable:
    """Calculate MACD indicators for given symbols and return a formatted table."""
    macd_values = []
    MACDData = namedtuple(
        "MACDData", ["symbol", "current_price", "macd", "signal", "histogram", "status"]
    )

    # Fetch previous day's values
    yesterday_values = fetch_yesterday_macd(conn, target_date)

    for symbol in symbols:
        try:
            app_logger.info(
                "Processing MACD for symbol: %s for date %s",
                symbol.symbol_name,
                target_date,
            )

            # Get historical data - 60 days for MACD calculation
            start_date = target_date - timedelta(days=60)
            candles = fetch_daily_candles(symbol, start_date, target_date, conn)

            if not candles:
                continue

            # Create DataFrame from candles
            df = pd.DataFrame(
                [
                    {
                        "Date": candle.end_date,
                        "Close": candle.close,
                        "Open": candle.open,
                        "High": candle.high,
                        "Low": candle.low,
                        "Volume": candle.volume,
                    }
                    for candle in candles
                ]
            )

            # Normalize dates to timezone-naive datetime objects for consistent comparison
            if not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)

            df = df.set_index("Date")
            df = df.sort_index()

            if df.empty:
                continue

            # Calculate MACD
            exp1 = df["Close"].ewm(span=12, adjust=False).mean()
            exp2 = df["Close"].ewm(span=26, adjust=False).mean()
            df["MACD"] = exp1 - exp2
            df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
            df["Histogram"] = df["MACD"] - df["Signal"]

            current_price = df["Close"].iloc[-1]
            macd = df["MACD"].iloc[-1]
            signal = df["Signal"].iloc[-1]
            histogram = df["Histogram"].iloc[-1]

            # Determine status
            status = "🟢" if histogram > 0 else "🔴"
            # Check for crossovers
            if yesterday_values is not None and not yesterday_values.empty:
                yesterday_data = yesterday_values[
                    yesterday_values["SymbolName"] == symbol.symbol_name
                ]
                if not yesterday_data.empty:
                    # Extract series with explicit type annotation to help type checker
                    histogram_series: pd.Series = yesterday_data["Histogram"]
                    yesterday_histogram = histogram_series.iloc[0]

                    if yesterday_histogram < 0 and histogram > 0:
                        status = "🚨🟢"  # Bullish crossover
                        app_logger.info(f"{symbol.symbol_name} MACD bullish crossover")
                    elif yesterday_histogram > 0 and histogram < 0:
                        status = "🚨🔴"  # Bearish crossover
                        app_logger.info(f"{symbol.symbol_name} MACD bearish crossover")

            macd_values.append(
                MACDData(
                    symbol=symbol.symbol_name,
                    current_price=current_price,
                    macd=macd,
                    signal=signal,
                    histogram=histogram,
                    status=status,
                )
            )

            # Save to database
            if conn:
                try:
                    save_macd_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        current_price=current_price,
                        macd=macd,
                        signal=signal,
                        histogram=histogram,
                        indicator_date=target_date,
                    )
                except Exception as e:
                    app_logger.error(f"Failed to save MACD results for {symbol.symbol_name}: {e!s}")

        except Exception as e:
            app_logger.error("Error processing MACD for symbol %s: %s", symbol.symbol_name, str(e))

    # Create MACD table
    macd_table = PrettyTable()
    macd_table.field_names = ["Symbol", "Price", "MACD", "Hist"]

    # Fill table
    for row in macd_values:
        macd_table.add_row(
            [
                row.symbol,
                format_to_6digits_without_trailing_zeros(row.current_price),
                format_to_6digits_without_trailing_zeros(row.macd),
                f"{format_to_6digits_without_trailing_zeros(row.histogram)} {row.status}",
            ]
        )

    return macd_table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol

    load_dotenv()
    conn = connect_to_sql()
    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="BTC",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.BINANCE,
        coingecko_name="bitcoin",  # Added required field
    )

    symbols = [symbol]

    macd_report = calculate_macd(symbols, conn=conn, target_date=datetime.now(UTC).date())
