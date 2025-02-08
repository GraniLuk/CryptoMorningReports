import pyodbc
from infra.telegram_logging_handler import app_logger


def save_rsi_results(conn, symbol_id: int, closed_price: float, rsi: float) -> None:
    """
    Saves RSI results to the database

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        closed_price (float): Current closing price
        rsi (float): Calculated RSI value
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO RSI AS target
                USING (SELECT ? AS SymbolID, CAST(GETDATE() AS DATE) AS IndicatorDate, ? AS ClosedPrice, ? AS RSI) 
                    AS source (SymbolID, IndicatorDate, ClosedPrice, RSI)
                ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                WHEN MATCHED THEN
                    UPDATE SET ClosedPrice = source.ClosedPrice, RSI = source.RSI
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, IndicatorDate, ClosedPrice, RSI)
                    VALUES (source.SymbolID, source.IndicatorDate, source.ClosedPrice, source.RSI);
            """
            cursor.execute(query, (symbol_id, closed_price, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved RSI results to database for symbol_id {symbol_id}"
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving RSI results: {str(e)}")
        raise
