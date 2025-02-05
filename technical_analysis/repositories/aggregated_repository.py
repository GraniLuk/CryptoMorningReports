import pyodbc
from infra.telegram_logging_handler import app_logger


def get_aggregated_data(conn):
    """
    Fetch data from SymbolDataView
    Returns: List of dictionaries containing aggregated symbol data
    """
    try:
            cursor = conn.cursor()
            
            query = """
                SELECT TOP (1000) [SymbolName]
                    ,[RSIIndicatorDate]
                    ,[RSIClosePrice]
                    ,[RSI]
                    ,[MACurrentPrice]
                    ,[MA50]
                    ,[MA200]
                    ,[EMA50]
                    ,[EMA200]
                    ,[LowPrice]
                    ,[HighPrice]
                    ,[RangePercent]
                FROM [dbo].[SymbolDataView]
            """
            
            cursor.execute(query)
            
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
                
            cursor.close()
            app_logger.info("Successfully fetched symbol data")
            
            return results
            
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching symbol data: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching symbol data: {str(e)}")
        raise