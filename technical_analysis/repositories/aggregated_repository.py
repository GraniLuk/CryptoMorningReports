import pyodbc

from infra.telegram_logging_handler import app_logger


def get_aggregated_data(conn):
    """
    Fetch data from SymbolDataView (SQL Server) or construct from tables (SQLite)
    Returns: List of dictionaries containing aggregated symbol data with all indicators
    """
    import os

    is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    if is_sqlite:
        # SQLite: Build aggregated data from individual tables
        try:
            cursor = conn.cursor()

            # Get the latest date for each indicator to determine what to show
            # We'll use the most recent IndicatorDate across all tables
            query = """
                SELECT 
                    s.SymbolName,
                    -- RSI data (get most recent RSI for each symbol)
                    rsi_data.RSIIndicatorDate,
                    rsi_data.RSIClosePrice,
                    rsi_data.RSI,
                    -- Moving Averages data
                    ma.CurrentPrice as MACurrentPrice,
                    ma.MA50,
                    ma.MA200,
                    ma.EMA50,
                    ma.EMA200,
                    ma.IndicatorDate as MAIndicatorDate,
                    -- MACD data
                    macd.MACD,
                    macd.Signal as MACDSignal,
                    macd.Histogram as MACDHistogram,
                    macd.IndicatorDate as MACDIndicatorDate,
                    -- Price Range data
                    pr.LowPrice,
                    pr.HighPrice,
                    pr.RangePercent,
                    pr.IndicatorDate as PriceRangeDate,
                    -- Volume data
                    vh.Volume,
                    vh.IndicatorDate as VolumeDate,
                    -- Market Cap data
                    mc.MarketCap,
                    mc.IndicatorDate as MarketCapDate
                FROM Symbols s
                -- Join with most recent RSI data for each symbol
                LEFT JOIN (
                    SELECT 
                        dc.SymbolID,
                        dc.Date as RSIIndicatorDate,
                        dc.Close as RSIClosePrice,
                        r.RSI,
                        ROW_NUMBER() OVER (PARTITION BY dc.SymbolID ORDER BY dc.Date DESC) as rn
                    FROM RSI r
                    JOIN DailyCandles dc ON r.DailyCandleID = dc.Id
                ) rsi_data ON s.SymbolID = rsi_data.SymbolID AND rsi_data.rn = 1
                -- Join with latest MovingAverages
                LEFT JOIN (
                    SELECT *, 
                           ROW_NUMBER() OVER (PARTITION BY SymbolID ORDER BY IndicatorDate DESC) as rn
                    FROM MovingAverages
                ) ma ON s.SymbolID = ma.SymbolID AND ma.rn = 1
                -- Join with latest MACD
                LEFT JOIN (
                    SELECT *, 
                           ROW_NUMBER() OVER (PARTITION BY SymbolID ORDER BY IndicatorDate DESC) as rn
                    FROM MACD
                ) macd ON s.SymbolID = macd.SymbolID AND macd.rn = 1
                -- Join with latest PriceRange
                LEFT JOIN (
                    SELECT *, 
                           ROW_NUMBER() OVER (PARTITION BY SymbolID ORDER BY IndicatorDate DESC) as rn
                    FROM PriceRange
                ) pr ON s.SymbolID = pr.SymbolID AND pr.rn = 1
                -- Join with latest VolumeHistory
                LEFT JOIN (
                    SELECT *, 
                           ROW_NUMBER() OVER (PARTITION BY SymbolID ORDER BY IndicatorDate DESC) as rn
                    FROM VolumeHistory
                ) vh ON s.SymbolID = vh.SymbolID AND vh.rn = 1
                -- Join with latest MarketCapHistory
                LEFT JOIN (
                    SELECT *, 
                           ROW_NUMBER() OVER (PARTITION BY SymbolID ORDER BY IndicatorDate DESC) as rn
                    FROM MarketCapHistory
                ) mc ON s.SymbolID = mc.SymbolID AND mc.rn = 1
                ORDER BY s.SymbolName
            """

            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            results = []

            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            cursor.close()
            app_logger.info(
                f"Successfully fetched aggregated data for {len(results)} symbols from SQLite"
            )

            return results

        except Exception as e:
            app_logger.error(f"Error fetching aggregated data from SQLite: {str(e)}")
            raise

    try:
        cursor = conn.cursor()

        query = """
                SELECT TOP (100) [SymbolName]
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
                order by RSIIndicatorDate desc
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
