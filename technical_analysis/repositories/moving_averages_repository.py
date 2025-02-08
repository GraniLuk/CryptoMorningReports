import pandas as pd
import pyodbc
from infra.telegram_logging_handler import app_logger
from datetime import date, timedelta


def save_moving_averages_results(
    conn,
    symbol_id: int,
    current_price: float,
    ma50: float,
    ma200: float,
    ema50: float = None,
    ema200: float = None,
    indicator_date: date = None,
) -> None:
    """
    Saves moving averages results to the database

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        current_price (float): Current price
        ma50 (float): 50-day moving average
        ma200 (float): 200-day moving average
        ema50 (float): 50-day exponential moving average
        ema200 (float): 200-day exponential moving average
        indicator_date (date): Date of the moving averages
    """
    try:
        if conn:
            indicator_date = indicator_date or date.today()
            cursor = conn.cursor()
            query = """
                MERGE INTO MovingAverages AS target
                USING (SELECT ? AS SymbolID, ? AS IndicatorDate, 
                             ? AS CurrentPrice, ? AS MA50, ? AS MA200, ? AS EMA50, ? AS EMA200) 
                    AS source (SymbolID, IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200)
                ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                WHEN MATCHED THEN
                    UPDATE SET CurrentPrice = source.CurrentPrice,
                             MA50 = source.MA50,
                             MA200 = source.MA200,
                             EMA50 = source.EMA50,
                             EMA200 = source.EMA200
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200)
                    VALUES (source.SymbolID, source.IndicatorDate, source.CurrentPrice, 
                           source.MA50, source.MA200, source.EMA50, source.EMA200);
            """
            cursor.execute(
                query,
                (symbol_id, indicator_date, current_price, ma50, ma200, ema50, ema200),
            )
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved moving averages results to database for symbol_id {symbol_id}"
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving moving averages results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving moving averages results: {str(e)}")
        raise


def fetch_yesterday_moving_averages(conn, target_date: date = None) -> pd.DataFrame:
    """
    Fetches all moving averages records from yesterday

    Args:
        conn: Database connection
        target_date (date): Date of the moving averages

    Returns:
        pd.DataFrame: DataFrame containing yesterday's moving averages data with columns:
            SymbolID, IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200
    """
    try:
        if conn:
            target_date = target_date or date.today()
            yesterday = target_date - timedelta(days=1)

            query = """
                SELECT ma.SymbolID, s.SymbolName, ma.IndicatorDate, ma.CurrentPrice, 
                       ma.MA50, ma.MA200, ma.EMA50, ma.EMA200
                FROM MovingAverages ma
                JOIN Symbols s ON ma.SymbolID = s.SymbolID
                WHERE ma.IndicatorDate = ?
            """

            df = pd.read_sql(query, conn, params=[yesterday])
            app_logger.info(
                f"Successfully fetched {len(df)} moving averages records for {yesterday}"
            )
            return df

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching yesterday's moving averages: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching yesterday's moving averages: {str(e)}")
        raise
