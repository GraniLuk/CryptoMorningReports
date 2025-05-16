from datetime import date, datetime, timedelta
from typing import Dict, List

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi


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
        "fifteen_min": rsi_periods // (24 * 4) + 1  # Minimum 1 day
    }
    
    calculation_start_date = start_date - timedelta(days=additional_lookback.get(timeframe, rsi_periods))

    try:
        # Get candle data with RSI values from the database, using the extended date range for calculation
        candles_with_rsi = get_candles_with_rsi(
            conn, symbol.symbol_id, calculation_start_date, timeframe
        )

        if not candles_with_rsi:
            app_logger.warning(
                f"No {timeframe} RSI data found for {symbol.symbol_name}"
            )
            return None

        # Create DataFrame from candles
        df = pd.DataFrame(candles_with_rsi)
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
        df["symbol"] = symbol.symbol_name

        # Check if any candles in the requested date range are missing RSI values
        requested_df = df[df.index >= pd.Timestamp(start_date)]
        missing_rsi = requested_df["RSI"].isna().any()
        
        if missing_rsi:
            app_logger.info(
                f"Found missing {timeframe} RSI values for {symbol.symbol_name}, calculating them now..."
            )
            
            # Import calculation functions inline to avoid circular imports
            from technical_analysis.rsi import calculate_rsi_using_RMA
            from technical_analysis.repositories.rsi_repository import save_rsi_by_timeframe
            
            # Calculate RSI for the entire dataframe (to ensure accurate values)
            df["calculated_RSI"] = calculate_rsi_using_RMA(df["Close"])
            
            # Find rows with missing RSI values in the requested date range
            missing_rows = requested_df[requested_df["RSI"].isna()]
            app_logger.info(f"Found {len(missing_rows)} rows with missing RSI in the requested date range")
              # Update only the missing values in the database
            for idx, row in missing_rows.iterrows():
                candle_id = int(row["SymbolId"])
                try:
                    calculated_rsi = float(df.at[idx, "calculated_RSI"])
                    
                    if not pd.isna(calculated_rsi):
                        # Save the calculated value to the database
                        save_rsi_by_timeframe(conn, candle_id, calculated_rsi, timeframe)
                        
                        # Update the dataframe
                        df.at[idx, "RSI"] = calculated_rsi
                        
                        app_logger.info(
                            f"Saved {timeframe} RSI for {symbol.symbol_name} candle {candle_id}: RSI={calculated_rsi:.2f}"
                        )
                except Exception as e:
                    app_logger.error(
                        f"Failed to save {timeframe} RSI for candle {candle_id}: {str(e)}"
                    )
            
            # Remove the temporary calculation column
            df.drop("calculated_RSI", axis=1, inplace=True, errors="ignore")
            
            app_logger.info(f"Successfully updated missing {timeframe} RSI values for {symbol.symbol_name}")
        
        # Return only the data for the requested date range
        return df[df.index >= pd.Timestamp(start_date)]

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
            }    # Add the row to the table
    row_data = []

    # Use the most recent date from any timeframe
    # Convert all date objects to pandas Timestamp to ensure consistent comparison
    most_recent_date = max([pd.Timestamp(data["date"]) for data in latest_data.values()])
    row_data.append(most_recent_date.strftime("%Y-%m-%d %H:%M"))

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
            symbol_data["daily_price"] = f"{float(daily_df['Close'].iloc[-1]):.2f}"
            symbol_data["daily_rsi"] = (
                f"{float(daily_df['RSI'].iloc[-1]):.2f}"
                if pd.notna(daily_df["RSI"].iloc[-1])
                else "N/A"
            )

        if hourly_df is not None and not hourly_df.empty:
            symbol_data["hourly_price"] = f"{float(hourly_df['Close'].iloc[-1]):.2f}"
            symbol_data["hourly_rsi"] = (
                f"{float(hourly_df['RSI'].iloc[-1]):.2f}"
                if pd.notna(hourly_df["RSI"].iloc[-1])
                else "N/A"
            )

        if fifteen_min_df is not None and not fifteen_min_df.empty:
            symbol_data["fifteen_min_price"] = f"{float(fifteen_min_df['Close'].iloc[-1]):.2f}"
            symbol_data["fifteen_min_rsi"] = (
                f"{float(fifteen_min_df['RSI'].iloc[-1]):.2f}"
                if pd.notna(fifteen_min_df["RSI"].iloc[-1])
                else "N/A"
            )

        data.append(symbol_data)    # Create consolidated table
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
                row.get('daily_rsi', 'N/A'),
                row.get('hourly_rsi', 'N/A'),
                row.get('fifteen_min_rsi', 'N/A')
            ]
        )

    return table


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
        symbol
        for symbol in symbols
        if symbol.symbol_name in ["VIRTUAL"]
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
