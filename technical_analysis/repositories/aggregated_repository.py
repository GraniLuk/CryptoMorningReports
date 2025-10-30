"""Aggregated data repository for cryptocurrency market indicators."""

import os

import pyodbc

from infra.telegram_logging_handler import app_logger


def get_aggregated_data(conn):
    """Fetch data from SymbolDataView (SQL Server) or construct from tables (SQLite)
    Returns: List of dictionaries containing aggregated symbol data with all indicators.
    """
    is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    if is_sqlite:
        # SQLite: Build aggregated data from individual tables
        try:
            cursor = conn.cursor()

            # Get the latest date for each indicator to determine what to show
            # We'll use the most recent IndicatorDate across all tables
            query = """
                WITH AllIndicatorDates AS (
    SELECT DISTINCT
        SymbolID,
        DATE(IndicatorDate) as IndicatorDate
    FROM (
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM MovingAverages
        UNION
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM MACD
        UNION
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM PriceRange
        UNION
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM VolumeHistory
        UNION
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM MarketCapHistory
        UNION
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM OpenInterest
        UNION
        SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate FROM FundingRate
        UNION
        SELECT dc.SymbolID, DATE(dc.Date) as IndicatorDate
        FROM DailyCandles dc
    ) AS all_dates
),
Last7Dates AS (
    SELECT
        SymbolID,
        IndicatorDate,
        ROW_NUMBER() OVER (PARTITION BY SymbolID ORDER BY IndicatorDate DESC) as rn
    FROM AllIndicatorDates
    WHERE IndicatorDate <= DATE('now')
),
LatestMA AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM MovingAverages
),
LatestMACD AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, MACD, Signal, Histogram,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM MACD
),
LatestPriceRange AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, LowPrice, HighPrice, RangePercent,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM PriceRange
),
LatestVolume AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, Volume,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM VolumeHistory
),
LatestMarketCap AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, MarketCap,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM MarketCapHistory
),
LatestOpenInterest AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, OpenInterest, OpenInterestValue,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM OpenInterest
),
LatestFundingRate AS (
    SELECT SymbolID, DATE(IndicatorDate) as IndicatorDate, FundingRate, FundingTime,
           ROW_NUMBER() OVER (
               PARTITION BY SymbolID, DATE(IndicatorDate) ORDER BY IndicatorDate DESC
           ) as rn
    FROM FundingRate
),
LatestDailyCandles AS (
    SELECT dc.SymbolID, DATE(dc.Date) as IndicatorDate, dc.Close, dc.Id as CandleId,
           ROW_NUMBER() OVER (
               PARTITION BY dc.SymbolID, DATE(dc.Date) ORDER BY dc.Date DESC
           ) as rn
    FROM DailyCandles dc
)
SELECT
    s.SymbolName,
    d.IndicatorDate,
    dc.Close as RSIClosePrice,
    rsi.RSI,
    ma.CurrentPrice as MACurrentPrice,
    ma.MA50,
    ma.MA200,
    ma.EMA50,
    ma.EMA200,
    macd.MACD,
    macd.Signal as MACDSignal,
    macd.Histogram as MACDHistogram,
    pr.LowPrice,
    pr.HighPrice,
    pr.RangePercent,
    vh.Volume,
    mc.MarketCap,
    oi.OpenInterest,
    oi.OpenInterestValue,
    fr.FundingRate,
    fr.FundingTime
FROM Symbols s
INNER JOIN Last7Dates d ON s.SymbolID = d.SymbolID AND d.rn <= 7
LEFT JOIN LatestDailyCandles dc
ON s.SymbolID = dc.SymbolID AND dc.IndicatorDate = d.IndicatorDate AND dc.rn = 1
LEFT JOIN RSI rsi ON dc.CandleId = rsi.DailyCandleID
LEFT JOIN LatestMA ma
ON s.SymbolID = ma.SymbolID AND ma.IndicatorDate = d.IndicatorDate AND ma.rn = 1
LEFT JOIN LatestMACD macd
ON s.SymbolID = macd.SymbolID AND macd.IndicatorDate = d.IndicatorDate AND macd.rn = 1
LEFT JOIN LatestPriceRange pr
ON s.SymbolID = pr.SymbolID AND pr.IndicatorDate = d.IndicatorDate AND pr.rn = 1
LEFT JOIN LatestVolume vh
ON s.SymbolID = vh.SymbolID AND vh.IndicatorDate = d.IndicatorDate AND vh.rn = 1
LEFT JOIN LatestMarketCap mc
ON s.SymbolID = mc.SymbolID AND mc.IndicatorDate = d.IndicatorDate AND mc.rn = 1
LEFT JOIN LatestOpenInterest oi
ON s.SymbolID = oi.SymbolID AND oi.IndicatorDate = d.IndicatorDate AND oi.rn = 1
LEFT JOIN LatestFundingRate fr
ON s.SymbolID = fr.SymbolID AND fr.IndicatorDate = d.IndicatorDate AND fr.rn = 1
ORDER BY s.SymbolName, d.IndicatorDate DESC

            """

            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            results = []

            for row in cursor.fetchall():
                results.append(dict(zip(columns, row, strict=False)))

            cursor.close()
            app_logger.info(
                f"Successfully fetched aggregated data for {len(results)} symbols from SQLite"
            )

            return results

        except Exception as e:
            app_logger.error(f"Error fetching aggregated data from SQLite: {e!s}")
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
                    ,[OpenInterest]
                    ,[OpenInterestValue]
                    ,[FundingRate]
                FROM [dbo].[SymbolDataView]
                order by RSIIndicatorDate desc
            """

        cursor.execute(query)

        columns = [column[0] for column in cursor.description]
        results = []

        for row in cursor.fetchall():
            results.append(dict(zip(columns, row, strict=False)))

        cursor.close()
        app_logger.info("Successfully fetched symbol data")

        return results

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching symbol data: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching symbol data: {e!s}")
        raise
