from collections import namedtuple
from datetime import date, timedelta
from typing import List

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_daily_candles
from source_repository import SourceID, Symbol
from technical_analysis.repositories.macd_repository import (
    fetch_yesterday_macd,
    save_macd_results,
)


def calculate_macd(
    symbols: List[Symbol], conn, target_date: date = None
) -> PrettyTable:
    """
    Calculates MACD indicators for given symbols and returns a formatted table
    """
    target_date = target_date or date.today()

    macd_values = []
    MACDData = namedtuple(
        "MACDData", ["symbol", "current_price", "macd", "signal", "histogram", "status"]
    )

    # Fetch previous day's values
    yesterdayValues = fetch_yesterday_macd(conn, target_date)

    for symbol in symbols:
        try:
            app_logger.info(
                "Processing MACD for symbol: %s for date %s",
                symbol.symbol_name,
                target_date,
            )

            # Get historical data - 60 days for MACD calculation
            start_date = target_date - timedelta(days=60)
            candles = fetch_daily_candles([symbol], conn, start_date, target_date)

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
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

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
            if not yesterdayValues.empty:
                yesterday_data = yesterdayValues[
                    yesterdayValues["SymbolName"] == symbol.symbol_name
                ]
                if not yesterday_data.empty:
                    yesterday_histogram = yesterday_data["Histogram"].iloc[0]

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
                    app_logger.error(
                        f"Failed to save MACD results for {symbol.symbol_name}: {str(e)}"
                    )

        except Exception as e:
            app_logger.error(
                "Error processing MACD for symbol %s: %s", symbol.symbol_name, str(e)
            )

    # Create MACD table
    macd_table = PrettyTable()
    macd_table.field_names = ["Symbol", "Price", "MACD", "Hist"]

    def format_number(num):
        return f"{num:.6f}".rstrip("0").rstrip(".")

    # Fill table
    for row in macd_values:
        macd_table.add_row(
            [
                row.symbol,
                format_number(row.current_price),
                format_number(row.macd),
                f"{format_number(row.histogram)} {row.status}",
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
    )

    macd_report = calculate_macd(symbol, conn=conn)
    print(macd_report)
