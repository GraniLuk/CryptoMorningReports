"""
Optimized version of RSI calculation for multiple timeframes
"""

from datetime import date, timedelta

import pandas as pd

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import (
    get_candles_with_rsi,
    save_rsi_by_timeframe,
)
from technical_analysis.rsi import calculate_rsi_using_RMA


def get_optimized_rsi_for_symbol_timeframe(
    symbol: Symbol, conn, timeframe: str = "daily", lookback_days: int = 7
):
    """
    Gets RSI data for a symbol in the specified timeframe.
    If RSI values are missing in the database, it calculates them only for the requested period.
    Optimized version that doesn't recalculate all historical data.

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

    try:
        # Get candle data with RSI values from the database, using the extended date range for calculation
        candles_with_rsi = get_candles_with_rsi(
            conn, symbol.symbol_id, calculation_start_date, timeframe
        )

        if not candles_with_rsi:
            app_logger.warning(f"No {timeframe} RSI data found for {symbol.symbol_name}")
            return None

        # Create DataFrame from candles
        df = pd.DataFrame(candles_with_rsi)
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
        df["symbol"] = symbol.symbol_name

        # Check if any candles in the requested date range are missing RSI values
        requested_df: pd.DataFrame = df[df.index >= pd.Timestamp(start_date)]

        # Ensure RSI column exists and check for missing values
        if "RSI" not in requested_df.columns:
            requested_df["RSI"] = pd.NA

        # Extract RSI column as Series and check for missing values
        rsi_series: pd.Series = requested_df["RSI"]
        missing_rsi: bool = bool(rsi_series.isna().any())

        if missing_rsi:
            app_logger.info(
                f"Found missing {timeframe} RSI values for {symbol.symbol_name}, calculating them now..."
            )

            # Calculate RSI for the entire dataframe (to ensure accurate values)
            calculated_rsi = calculate_rsi_using_RMA(df["Close"])
            df["calculated_RSI"] = calculated_rsi

            # Find rows with missing RSI values in the requested date range
            rsi_mask: pd.Series = requested_df["RSI"].isna()
            missing_rows: pd.DataFrame = requested_df[rsi_mask]
            app_logger.info(
                f"Found {len(missing_rows)} rows with missing RSI in the requested date range"
            )

            # Update only the missing values in the database
            for idx, row in missing_rows.iterrows():
                # Type assertion to help type checker understand idx is a valid index
                assert isinstance(idx, pd.Timestamp | str | int), (
                    f"Unexpected index type: {type(idx)}"
                )

                candle_id = int(row["SymbolId"])

                # Get the calculated RSI value using loc for proper type inference
                calculated_value = df.loc[idx, "calculated_RSI"]

                if pd.notna(calculated_value):
                    # Type ignore: RSI values are always numeric, safe to convert to float
                    calculated_rsi_value = float(calculated_value)  # type: ignore[arg-type]

                    try:
                        # Save the calculated value to the database
                        save_rsi_by_timeframe(conn, candle_id, calculated_rsi_value, timeframe)

                        # Update the dataframe using loc
                        df.loc[idx, "RSI"] = calculated_rsi_value

                        app_logger.info(
                            f"Saved {timeframe} RSI for {symbol.symbol_name} candle {candle_id}: RSI={calculated_rsi_value:.2f}"
                        )
                    except Exception as e:
                        app_logger.error(
                            f"Failed to save {timeframe} RSI for candle {candle_id}: {e!s}"
                        )

            # Remove the temporary calculation column
            df.drop("calculated_RSI", axis=1, inplace=True, errors="ignore")

            app_logger.info(
                f"Successfully updated missing {timeframe} RSI values for {symbol.symbol_name}"
            )

        # Return only the data for the requested date range
        return df[df.index >= pd.Timestamp(start_date)]

    except Exception as e:
        app_logger.error(f"Error getting {timeframe} RSI for {symbol.symbol_name}: {e!s}")
        return None


# Function to test the optimized implementation
def test_optimized_rsi():
    """Test the optimized RSI calculation"""
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    # Load environment and connect to database
    load_dotenv()
    conn = connect_to_sql()

    if not conn:
        print("Failed to connect to database")
        return

    symbols = fetch_symbols(conn)

    if not symbols:
        print("No symbols found")
        return

    # Get the VIRTUAL symbol or first symbol
    symbol = next((s for s in symbols if s.symbol_name == "VIRTUAL"), symbols[0])
    print(f"Testing with symbol: {symbol.symbol_name}")

    # First let's get data with all RSI values present
    df_complete = get_optimized_rsi_for_symbol_timeframe(symbol, conn, "daily", 3)

    if df_complete is None or df_complete.empty:
        print("No RSI data available for testing")
        return

    print("\nDataFrame with optimized RSI calculation:")
    print(df_complete.head())

    # Check if all values have RSI - ensure df_complete is a DataFrame
    assert isinstance(df_complete, pd.DataFrame), "Expected a DataFrame"
    has_missing_rsi: bool = bool(df_complete["RSI"].isna().any())
    print(f"\nAre there any missing RSI values? {has_missing_rsi}")

    if not has_missing_rsi:
        print("\nSUCCESS: All RSI values are present and accounted for!")
    else:
        print("\nFAILED: There are missing RSI values")


if __name__ == "__main__":
    test_optimized_rsi()
