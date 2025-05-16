"""
Optimized version of RSI calculation for multiple timeframes
"""
import pandas as pd
from datetime import date, timedelta

from technical_analysis.rsi import calculate_rsi_using_RMA
from technical_analysis.repositories.rsi_repository import save_rsi_by_timeframe, get_candles_with_rsi
from infra.telegram_logging_handler import app_logger
from source_repository import Symbol

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
            
            # Calculate RSI for the entire dataframe (to ensure accurate values)
            calculated_rsi = calculate_rsi_using_RMA(df["Close"])
            df["calculated_RSI"] = calculated_rsi
            
            # Find rows with missing RSI values in the requested date range
            missing_rows = requested_df[requested_df["RSI"].isna()]
            app_logger.info(f"Found {len(missing_rows)} rows with missing RSI in the requested date range")
            
            # Update only the missing values in the database
            for index, row in missing_rows.iterrows():
                candle_id = int(row["SymbolId"])
                if not pd.isna(df.at[index, "calculated_RSI"]):
                    calculated_rsi_value = float(df.at[index, "calculated_RSI"])
                    
                    try:
                        # Save the calculated value to the database
                        save_rsi_by_timeframe(conn, candle_id, calculated_rsi_value, timeframe)
                        
                        # Update the dataframe
                        df.at[index, "RSI"] = calculated_rsi_value
                        
                        app_logger.info(
                            f"Saved {timeframe} RSI for {symbol.symbol_name} candle {candle_id}: RSI={calculated_rsi_value:.2f}"
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
    
    # Check if all values have RSI
    print(f"\nAre there any missing RSI values? {df_complete['RSI'].isna().any()}")
    
    if not df_complete['RSI'].isna().any():
        print("\nSUCCESS: All RSI values are present and accounted for!")
    else:
        print("\nFAILED: There are missing RSI values")

if __name__ == "__main__":
    test_optimized_rsi()
