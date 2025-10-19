from datetime import date, datetime, timedelta
from typing import Dict, List

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.fifteen_min_candle_repository import (
    FifteenMinCandleRepository,
)
from technical_analysis.repositories.hourly_candle_repository import (
    HourlyCandleRepository,
)
from technical_analysis.repositories.rsi_repository import (
    get_candles_with_rsi,
    save_rsi_by_timeframe,
)
from technical_analysis.rsi import calculate_rsi_using_RMA


def get_rsi_for_symbol_timeframe(
    symbol: Symbol, conn, timeframe: str = "daily", lookback_days: int = 7
):
    """
    Gets RSI data for a symbol in the specified timeframe.
    If RSI values are missing in the database, it calculates them only for the requested period.

    Args:
        symbol: Symbol object
        conn: Database connection
        timeframe: The timeframe to fetch ('daily', 'hourly', 'fifteen_min')
        lookback_days: How many days to look back for data

    Returns:
        DataFrame: DataFrame with RSI data or None if no data
    """
    # Calculate appropriate start date based on the timeframe
    target_date = date.today()
    start_date = target_date - timedelta(days=lookback_days)

    # We need to pull data from an earlier start date to calculate RSI accurately
    # RSI typically uses 14 periods, so we add extra days/periods depending on timeframe
    rsi_periods = 14  # Standard RSI period

    # Calculate additional lookback based on timeframe (add more periods for higher frequency data)
    additional_lookback = {
        "daily": rsi_periods,
        "hourly": rsi_periods // 24 + 1,  # Minimum 1 day
        "fifteen_min": rsi_periods // (24 * 4) + 1,  # Minimum 1 day
    }

    calculation_start_date = start_date - timedelta(
        days=additional_lookback.get(timeframe, rsi_periods)
    )

    try:  # Get candle data with RSI values from the database, using the extended date range for calculation
        candles_with_rsi = get_candles_with_rsi(
            conn, symbol.symbol_id, calculation_start_date.isoformat(), timeframe
        )

        if not candles_with_rsi:
            app_logger.warning(
                f"No {timeframe} RSI data found for {symbol.symbol_name}, attempting to calculate RSI"
            )

            # Attempt to fetch candles directly and calculate RSI
            repository = _get_candle_repository(conn, timeframe)
            if not repository:
                app_logger.error(f"No repository available for timeframe: {timeframe}")
                return None  # Fetch candles for calculation (need more data for RSI calculation)
            extended_start_date = calculation_start_date - timedelta(
                days=30
            )  # Get more historical data for RSI calculation
            # Convert date to datetime for repository call
            extended_start_datetime = datetime.combine(
                extended_start_date, datetime.min.time()
            )
            candles = repository.get_candles(
                symbol, extended_start_datetime, datetime.now()
            )

            if not candles:
                app_logger.warning(
                    f"No {timeframe} candles found for {symbol.symbol_name}"
                )
                return None

            # Calculate and save RSI for missing data
            candles_with_rsi = _calculate_and_save_rsi(conn, symbol, candles, timeframe)

            if not candles_with_rsi:
                app_logger.error(
                    f"Failed to calculate RSI for {symbol.symbol_name} {timeframe}"
                )
                return None

        # Create DataFrame from candles
        df = pd.DataFrame(candles_with_rsi)
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
        df["symbol"] = symbol.symbol_name

        # Ensure the index is DatetimeIndex
        df.index = pd.to_datetime(df.index)
        # Explicitly cast to DatetimeIndex if it's not already, for type safety
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.DatetimeIndex(df.index)

        # Convert start_date (datetime.date) to pandas Timestamp
        # This is crucial for comparison with DatetimeIndex
        start_timestamp = pd.Timestamp(start_date)

        # Now, compare df.index with start_timestamp.
        # If df.index is timezone-aware, start_timestamp must also be made aware or comparison might fail/behave unexpectedly.
        # If df.index is naive, start_timestamp should also be naive.
        if df.index.tz is not None:
            # If start_timestamp is naive, localize it to df.index.tz
            if start_timestamp.tz is None:
                start_timestamp = start_timestamp.tz_localize(df.index.tz)
            # If start_timestamp is aware but different tz, convert it
            elif start_timestamp.tz != df.index.tz:
                start_timestamp = start_timestamp.tz_convert(df.index.tz)
        else:
            # If df.index is naive, ensure start_timestamp is also naive
            if start_timestamp.tz is not None:
                start_timestamp = start_timestamp.tz_localize(None)

        requested_df: pd.DataFrame = df[df.index >= start_timestamp]
        rsi_series: pd.Series = requested_df["RSI"]
        missing_rsi: bool = bool(rsi_series.isna().any())

        if missing_rsi:
            app_logger.info(
                f"Found missing {timeframe} RSI values for {symbol.symbol_name}, calculating them now..."
            )

            # Import calculation functions inline to avoid circular imports
            from technical_analysis.repositories.rsi_repository import (
                save_rsi_by_timeframe,
            )
            from technical_analysis.rsi import calculate_rsi_using_RMA

            # Calculate RSI for the entire dataframe (to ensure accurate values)
            df["calculated_RSI"] = calculate_rsi_using_RMA(df["Close"])

            # Find rows with missing RSI values in the requested date range
            missing_mask: pd.Series = requested_df["RSI"].isna()
            missing_rows: pd.DataFrame = requested_df[missing_mask]
            app_logger.info(
                f"Found {len(missing_rows)} rows with missing RSI in the requested date range"
            )
            # Update only the missing values in the database
            for idx, row in missing_rows.iterrows():
                # Type assertion to help type checker understand idx is a valid index
                assert isinstance(idx, (pd.Timestamp, str, int)), (
                    f"Unexpected index type: {type(idx)}"
                )

                candle_id = int(row["SymbolId"])
                try:
                    # Use loc instead of at for better type inference
                    calculated_value = df.loc[idx, "calculated_RSI"]
                    calculated_rsi = float(calculated_value)  # type: ignore[arg-type]

                    if not pd.isna(calculated_rsi):
                        # Save the calculated value to the database
                        save_rsi_by_timeframe(
                            conn, candle_id, calculated_rsi, timeframe
                        )

                        # Update the dataframe
                        df.loc[idx, "RSI"] = calculated_rsi

                        app_logger.info(
                            f"Saved {timeframe} RSI for {symbol.symbol_name} candle {candle_id}: RSI={calculated_rsi:.2f}"
                        )
                except Exception as e:
                    app_logger.error(
                        f"Failed to save {timeframe} RSI for candle {candle_id}: {str(e)}"
                    )

            # Remove the temporary calculation column
            df.drop("calculated_RSI", axis=1, inplace=True, errors="ignore")

            app_logger.info(
                f"Successfully updated missing {timeframe} RSI values for {symbol.symbol_name}"
            )

        # Return only the data for the requested date range using the aligned start_timestamp
        return df[df.index >= start_timestamp]

    except Exception as e:
        app_logger.error(
            f"Error getting {timeframe} RSI for {symbol.symbol_name}: {str(e)}"
        )
        return None


def create_multi_timeframe_rsi_table(
    symbol: Symbol, conn, timeframes: List[str] = ["daily", "hourly", "fifteen_min"]
):
    """
    Creates a multi-timeframe RSI table for a symbol

    Args:
        symbol: Symbol object
        conn: Database connection
        timeframes: List of timeframes to include

    Returns:
        PrettyTable: Formatted table with RSI values
    """
    # Map of lookback days appropriate for each timeframe
    lookback_map = {
        "daily": 30,  # Look back 30 days
        "hourly": 7,  # Look back 7 days for hourly
        "fifteen_min": 3,  # Look back 3 days for 15-min
    }

    # Collect data for each timeframe
    rsi_data = {}
    for timeframe in timeframes:
        lookback = lookback_map.get(timeframe, 7)
        df = get_rsi_for_symbol_timeframe(symbol, conn, timeframe, lookback)
        if df is not None and not df.empty:
            rsi_data[timeframe] = df

    if not rsi_data:
        app_logger.warning(f"No RSI data found for {symbol.symbol_name}")
        return None

    # Create a PrettyTable for output
    rsi_table = PrettyTable()

    # Define column titles based on available timeframes
    columns = ["Date"]
    if "daily" in rsi_data:
        columns.extend(["Daily Price", "Daily RSI"])
    if "hourly" in rsi_data:
        columns.extend(["Hourly Price", "Hourly RSI"])
    if "fifteen_min" in rsi_data:
        columns.extend(["15min Price", "15min RSI"])

    rsi_table.field_names = columns

    # For each timeframe, get the most recent data
    latest_data = {}
    for timeframe, df in rsi_data.items():
        if not df.empty:
            latest_row = df.iloc[-1]
            latest_data[timeframe] = {
                "date": latest_row.name,
                "price": float(latest_row["Close"]),
                "rsi": float(latest_row["RSI"])
                if pd.notna(latest_row["RSI"])
                else None,
            }  # Add the row to the table
    row_data = []

    # Use the most recent date from any timeframe
    # Convert all date objects to pandas Timestamp to ensure consistent comparison
    timestamps = [pd.Timestamp(data["date"]) for data in latest_data.values()]
    most_recent_date: pd.Timestamp = max(timestamps)

    # Ensure the timestamp is valid before calling strftime
    if pd.notna(most_recent_date):
        row_data.append(most_recent_date.strftime("%Y-%m-%d %H:%M"))
    else:
        row_data.append("N/A")

    # Add data for each timeframe
    if "daily" in latest_data:
        row_data.append(f"${latest_data['daily']['price']:,.2f}")
        row_data.append(
            f"{latest_data['daily']['rsi']:.2f}"
            if latest_data["daily"]["rsi"] is not None
            else "N/A"
        )

    if "hourly" in latest_data:
        row_data.append(f"${latest_data['hourly']['price']:,.2f}")
        row_data.append(
            f"{latest_data['hourly']['rsi']:.2f}"
            if latest_data["hourly"]["rsi"] is not None
            else "N/A"
        )

    if "fifteen_min" in latest_data:
        row_data.append(f"${latest_data['fifteen_min']['price']:,.2f}")
        row_data.append(
            f"{latest_data['fifteen_min']['rsi']:.2f}"
            if latest_data["fifteen_min"]["rsi"] is not None
            else "N/A"
        )

    # Check if all required RSI values are present
    if (
        latest_data["fifteen_min"]["rsi"] is not None
        and latest_data["hourly"]["rsi"] is not None
        and latest_data["daily"]["rsi"] is not None
    ):
        rsi_table.add_row(row_data)

    return rsi_table


def create_multi_timeframe_rsi_tables(
    symbols: List[Symbol],
    conn,
    timeframes: List[str] = ["daily", "hourly", "fifteen_min"],
) -> Dict[str, PrettyTable]:
    """
    Creates multi-timeframe RSI tables for multiple symbols

    Args:
        symbols: List of Symbol objects
        conn: Database connection
        timeframes: List of timeframes to include

    Returns:
        Dict[str, PrettyTable]: Dictionary mapping timeframes to formatted tables with RSI values
    """
    # Collect all RSI data
    all_symbols_data = {}
    for timeframe in timeframes:
        all_symbols_data[timeframe] = []

    for symbol in symbols:
        for timeframe in timeframes:
            df = get_rsi_for_symbol_timeframe(symbol, conn, timeframe)
            if df is not None and not df.empty:
                # Get just the latest row
                latest_row = df.iloc[-1].copy()
                latest_row["symbol"] = symbol.symbol_name
                latest_row["date"] = latest_row.name
                all_symbols_data[timeframe].append(latest_row)

    # Create tables for each timeframe
    tables = {}

    for timeframe in timeframes:
        if not all_symbols_data[timeframe]:
            app_logger.warning(f"No {timeframe} RSI data available")
            continue

        # Convert to DataFrame and sort by RSI
        df = pd.DataFrame(all_symbols_data[timeframe])
        if not df.empty:
            df = df.sort_values("RSI", ascending=False)

            # Create table for this timeframe
            table = PrettyTable()
            table.field_names = ["Symbol", "Price", f"{timeframe.capitalize()} RSI"]

            for _, row in df.iterrows():
                symbol = row["symbol"]
                price = float(row["Close"])
                rsi = float(row["RSI"]) if pd.notna(row["RSI"]) else None

                table.add_row(
                    [
                        symbol,
                        f"${price:,.2f}",
                        f"{rsi:.2f}" if rsi is not None else "N/A",
                    ]
                )

            tables[timeframe] = table

    return tables


def create_consolidated_rsi_table(symbols: List[Symbol], conn) -> PrettyTable:
    """
    Creates a consolidated RSI table showing RSI for daily, hourly, and 15-min timeframes

    Args:
        symbols: List of Symbol objects
        conn: Database connection

    Returns:
        PrettyTable: Consolidated table with RSI values across timeframes
    """
    # Get the most recent data for each symbol and timeframe
    data = []

    for symbol in symbols:
        symbol_data = {"symbol": symbol.symbol_name}

        # Get data for each timeframe
        daily_df = get_rsi_for_symbol_timeframe(symbol, conn, "daily", 1)
        hourly_df = get_rsi_for_symbol_timeframe(symbol, conn, "hourly", 1)
        fifteen_min_df = get_rsi_for_symbol_timeframe(symbol, conn, "fifteen_min", 1)

        # Extract latest values
        if daily_df is not None and not daily_df.empty:
            # Type annotation to help type checker
            daily_close: pd.Series = daily_df["Close"]
            daily_rsi: pd.Series = daily_df["RSI"]

            symbol_data["daily_price"] = f"{float(daily_close.iloc[-1]):.2f}"
            symbol_data["daily_rsi"] = (
                f"{float(daily_rsi.iloc[-1]):.2f}"
                if pd.notna(daily_rsi.iloc[-1])
                else "N/A"
            )

        if hourly_df is not None and not hourly_df.empty:
            # Type annotation to help type checker
            hourly_close: pd.Series = hourly_df["Close"]
            hourly_rsi: pd.Series = hourly_df["RSI"]

            symbol_data["hourly_price"] = f"{float(hourly_close.iloc[-1]):.2f}"
            symbol_data["hourly_rsi"] = (
                f"{float(hourly_rsi.iloc[-1])::.2f}"
                if pd.notna(hourly_rsi.iloc[-1])
                else "N/A"
            )

        if fifteen_min_df is not None and not fifteen_min_df.empty:
            # Type annotation to help type checker
            fifteen_close: pd.Series = fifteen_min_df["Close"]
            fifteen_rsi: pd.Series = fifteen_min_df["RSI"]

            symbol_data["fifteen_min_price"] = f"{float(fifteen_close.iloc[-1])::.2f}"
            symbol_data["fifteen_min_rsi"] = (
                f"{float(fifteen_rsi.iloc[-1]):.2f}"
                if pd.notna(fifteen_rsi.iloc[-1])
                else "N/A"
            )

        data.append(symbol_data)  # Create consolidated table
    table = PrettyTable()
    table.field_names = ["Symbol", "Daily RSI", "Hourly RSI", "15min RSI"]

    # Sort by daily RSI (descending)
    sorted_data = sorted(
        data,
        key=lambda x: (x.get("daily_rsi") is not None, x.get("daily_rsi", 0)),
        reverse=True,
    )

    for row in sorted_data:
        table.add_row(
            [
                row["symbol"],
                row.get("daily_rsi", "N/A"),
                row.get("hourly_rsi", "N/A"),
                row.get("fifteen_min_rsi", "N/A"),
            ]
        )

    return table


def _get_candle_repository(conn, timeframe: str):
    """
    Returns the appropriate candle repository based on timeframe.
    """
    timeframe_lower = timeframe.lower()
    if timeframe_lower == "daily":
        return DailyCandleRepository(conn)
    elif timeframe_lower == "hourly":
        return HourlyCandleRepository(conn)
    elif timeframe_lower == "fifteen_min":
        return FifteenMinCandleRepository(conn)
    else:
        app_logger.error(f"Unknown timeframe: {timeframe}")
        return None


def _calculate_and_save_rsi(conn, symbol: Symbol, candles: List, timeframe: str):
    """
    Calculate RSI for the given candles and save to database.
    Returns list of candles with RSI data in the format expected by the calling function.
    """
    if not candles:
        return None

    try:
        # Create DataFrame from candles
        df = pd.DataFrame(
            [
                {
                    "date": candle.end_date,
                    "close": candle.close,
                    "candle_id": candle.id,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "volume": candle.volume,
                }
                for candle in candles
            ]
        )

        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)

        # Calculate RSI using RMA method
        df["rsi"] = calculate_rsi_using_RMA(df["close"])
        # Save RSI values to database
        for index, row in df.iterrows():
            if not pd.isna(row["rsi"]):
                save_rsi_by_timeframe(
                    conn, int(row["candle_id"]), float(row["rsi"]), timeframe
                )

        # Return data in the format expected by the calling function
        # Reset index to make date a column again
        df.reset_index(inplace=True)

        # Filter out rows with NaN RSI values and return as list of dictionaries
        valid_data = df.dropna(subset=["rsi"])

        return [
            {
                "date": row["date"],
                "close": row["close"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "volume": row["volume"],
                "rsi": row["rsi"],
            }
            for _, row in valid_data.iterrows()
        ]

    except Exception as e:
        app_logger.error(
            f"Error calculating RSI for {symbol.symbol_name} {timeframe}: {str(e)}"
        )
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols
    from technical_analysis.fifteen_min_candle import calculate_fifteen_min_rsi
    from technical_analysis.hourly_candle import calculate_hourly_rsi
    from technical_analysis.rsi_calculator import update_daily_rsi_for_all_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    symbols = [
        symbol for symbol in symbols if symbol.symbol_name in ["VIRTUAL"]
    ]  # Filter for testing

    # Update RSI for all timeframes before generating reports
    update_daily_rsi_for_all_symbols(conn, symbols)
    calculate_hourly_rsi(symbols, conn)
    calculate_fifteen_min_rsi(symbols, conn)

    # Generate reports
    print("Individual Symbol Report:")
    symbol = next((s for s in symbols if s.symbol_name == "VIRTUAL"), symbols[0])
    table = create_multi_timeframe_rsi_table(symbol, conn)
    if table:
        print(table)
