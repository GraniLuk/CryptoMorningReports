"""RSI data repository for cryptocurrency markets."""

import os
from datetime import date, datetime, timedelta

import pyodbc

from infra.telegram_logging_handler import app_logger


def save_rsi_results(conn, daily_candle_id: int, rsi: float) -> None:
    """Save RSI results to the database.

    Args:
        conn: Database connection
        daily_candle_id (int): DailyCandle ID from DailyCandles table
        rsi (float): Calculated RSI value

    """
    try:
        if conn:
            cursor = conn.cursor()

            # Check if we're using SQLite or SQL Server
            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            if is_sqlite:
                # SQLite uses INSERT OR REPLACE
                query = """
                    INSERT OR REPLACE INTO RSI (DailyCandleID, RSI)
                    VALUES (?, ?)
                """
            else:
                # SQL Server uses MERGE
                query = """
                    MERGE INTO RSI AS target
                    USING (SELECT ? AS DailyCandleID, ? AS RSI)
                        AS source (DailyCandleID, RSI)
                    ON target.DailyCandleID = source.DailyCandleID
                    WHEN MATCHED THEN
                        UPDATE SET RSI = source.RSI
                    WHEN NOT MATCHED THEN
                        INSERT (DailyCandleID, RSI)
                        VALUES (source.DailyCandleID, source.RSI);
                """

            cursor.execute(query, (daily_candle_id, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved RSI results to database for daily_candle_id {daily_candle_id}",
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving RSI results: {e!s}")
        raise


def save_rsi_by_timeframe(conn, candle_id: int, rsi: float, timeframe: str = "daily") -> None:
    """Save RSI results to the database for different timeframes.

    Args:
        conn: Database connection
        candle_id (int): Candle ID from the respective candles table
        rsi (float): Calculated RSI value
        timeframe (str): Timeframe type ("daily", "hourly", "fifteen_min")

    """
    # Map timeframe to the correct table
    table_map = {
        "daily": "RSI",
        "hourly": "HourlyRSI",
        "fifteen_min": "FifteenMinRSI",
    }

    # Map timeframe to the correct ID column name
    id_column_map = {
        "daily": "DailyCandleID",
        "hourly": "HourlyCandleID",
        "fifteen_min": "FifteenMinCandleID",
    }

    table_name = table_map.get(timeframe.lower())
    id_column = id_column_map.get(timeframe.lower())

    if not table_name or not id_column:
        msg = f"Invalid timeframe: {timeframe}"
        raise ValueError(msg)

    try:
        if conn:
            cursor = conn.cursor()

            # Check if we're using SQLite or SQL Server
            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            if is_sqlite:
                # SQLite uses INSERT OR REPLACE
                query = f"""
                    INSERT OR REPLACE INTO {table_name} ({id_column}, RSI)
                    VALUES (?, ?)
                """  # noqa: S608
            else:
                # SQL Server uses MERGE
                query = f"""
                    MERGE INTO {table_name} AS target
                    USING (SELECT ? AS {id_column}, ? AS RSI)
                        AS source ({id_column}, RSI)
                    ON target.{id_column} = source.{id_column}
                    WHEN MATCHED THEN
                        UPDATE SET RSI = source.RSI
                    WHEN NOT MATCHED THEN
                        INSERT ({id_column}, RSI)
                        VALUES (source.{id_column}, source.RSI);
                """  # noqa: S608
            cursor.execute(query, (candle_id, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved {timeframe} RSI results to database for candle_id {candle_id}",
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving {timeframe} RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving {timeframe} RSI results: {e!s}")
        raise


def get_candles_with_rsi(conn, symbol_id: int, from_date, timeframe: str = "daily") -> list | None:
    """Fetch candle data with RSI for a specific symbol.

    only returning records on or after the specified date.

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID to filter the data
        from_date: The start date to filter the candles (inclusive)
        timeframe (str): Timeframe type ("daily", "hourly", "fifteen_min")

    Returns:
        list: List of dictionaries containing the candle and RSI data

    """
    try:
        if conn:
            cursor = conn.cursor()

            # Map timeframe to the correct tables
            table_map = {
                "daily": ("DailyCandles", "RSI", "DailyCandleID"),
                "hourly": ("HourlyCandles", "HourlyRSI", "HourlyCandleID"),
                "fifteen_min": (
                    "FifteenMinCandles",
                    "FifteenMinRSI",
                    "FifteenMinCandleID",
                ),
            }

            candle_table, rsi_table, id_column = table_map.get(
                timeframe.lower(), table_map["daily"],
            )

            # Convert date/datetime to ISO string for SQL comparison
            # SQLite stores EndDate as text, so we need string comparison
            if isinstance(from_date, date | datetime):
                from_date_str = from_date.isoformat()
            else:
                from_date_str = str(from_date)

            query = f"""
                SELECT
                    dc.ID,
                    dc.SymbolId,
                    dc.EndDate as date,
                    r.RSI,
                    dc.[Close],
                    dc.[Open],
                    dc.High,
                    dc.Low
                FROM {candle_table} dc
                LEFT JOIN {rsi_table} r ON dc.ID = r.{id_column}
                WHERE dc.SymbolId = ? AND dc.EndDate >= ?
                ORDER BY dc.EndDate DESC
            """  # noqa: S608
            cursor.execute(query, (symbol_id, from_date_str))

            # Fetch column names
            columns = [column[0] for column in cursor.description]

            # Fetch all rows and convert to list of dictionaries
            results = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

            cursor.close()
            app_logger.info(
                f"Successfully fetched {timeframe} candle data with RSI for "
                f"symbol_id {symbol_id} starting from {from_date}",
            )
            return results

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching {timeframe} candle data with RSI: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching {timeframe} candle data with RSI: {e!s}")
        raise


def _get_timeframe_config(timeframe: str) -> tuple[str, str, str, int, int]:
    """Get timeframe configuration for database queries."""
    table_map = {
        "daily": ("DailyCandles", "RSI", "DailyCandleID", 1, 7),
        "hourly": ("HourlyCandles", "HourlyRSI", "HourlyCandleID", 1, 24),
        "fifteen_min": (
            "FifteenMinCandles",
            "FifteenMinRSI",
            "FifteenMinCandleID",
            4,
            4 * 24,
        ),
    }
    return table_map.get(timeframe.lower(), table_map["daily"])


def _get_interval_settings(
    timeframe: str, previous_interval: int, week_interval: int,
) -> tuple[str, int, int]:
    """Get interval keyword and adjusted intervals."""
    interval_keyword = (
        "day"
        if timeframe.lower() == "daily"
        else "hour"
        if timeframe.lower() == "hourly"
        else "minute"
    )

    # Adjust multiplier for fifteen_min (as we need to multiply by 15)
    if timeframe.lower() == "fifteen_min":
        previous_interval *= 15
        week_interval *= 15

    return interval_keyword, previous_interval, week_interval


def _build_query(
    *,
    is_sqlite: bool,
    candle_table: str,
    rsi_table: str,
    id_column: str,
    interval_keyword: str,
    previous_interval: int,
    week_interval: int,
) -> str:
    """Build the appropriate query for SQLite or SQL Server."""
    if is_sqlite:
        # SQLite syntax: datetime(date, '-X days/hours/minutes')
        if interval_keyword == "day":
            date_func_prev = f"datetime(?, '-{previous_interval} days')"
            date_func_week = f"datetime(?, '-{week_interval} days')"
        elif interval_keyword == "hour":
            date_func_prev = f"datetime(?, '-{previous_interval} hours')"
            date_func_week = f"datetime(?, '-{week_interval} hours')"
        else:  # minute
            date_func_prev = f"datetime(?, '-{previous_interval} minutes')"
            date_func_week = f"datetime(?, '-{week_interval} minutes')"

        query = f"""
            SELECT
                dc.EndDate as IndicatorDate,
                r.RSI
            FROM {candle_table} dc
            LEFT JOIN {rsi_table} r ON dc.Id = r.{id_column}
            WHERE dc.SymbolID = ?
            AND dc.EndDate IN (
                {date_func_prev},  -- Previous interval
                {date_func_week}   -- Week equivalent
            )
            ORDER BY dc.EndDate DESC
        """  # noqa: S608
    else:
        # SQL Server syntax
        query = f"""
            SELECT
                dc.EndDate as IndicatorDate,
                r.RSI
            FROM {candle_table} dc
            LEFT JOIN {rsi_table} r ON dc.ID = r.{id_column}
            WHERE dc.SymbolID = ?
            AND dc.EndDate IN (
                DATEADD({interval_keyword}, -{previous_interval}, ?),  -- Previous interval
                DATEADD({interval_keyword}, -{week_interval}, ?)   -- Week equivalent
            )
            ORDER BY dc.EndDate DESC
        """  # noqa: S608
    return query


def _process_rsi_results(rows, current_date: date, timeframe: str) -> dict:
    """Process query results into RSI dictionary."""
    results = {}

    # Convert date to datetime for comparison if it's a date object
    if isinstance(current_date, datetime):
        compare_date = current_date
    elif hasattr(current_date, "to_pydatetime"):  # pandas Timestamp
        compare_date = current_date.to_pydatetime()  # type: ignore
    elif isinstance(current_date, date):  # date object (not datetime)
        compare_date = datetime.combine(current_date, datetime.min.time())
    else:
        # Fallback for any other type
        compare_date = datetime.combine(current_date, datetime.min.time())

    for row in rows:
        # Handle case where RSI might be None
        if row[1] is not None:
            interval_description = "yesterday" if timeframe.lower() == "daily" else "previous"
            week_description = "week_ago" if timeframe.lower() == "daily" else "period_ago"

            # Get the row date and ensure it's datetime for comparison
            row_date = row[0]
            if isinstance(row_date, str):
                row_date = datetime.fromisoformat(row_date.replace("Z", "+00:00"))
            elif hasattr(row_date, "to_pydatetime"):
                row_date = row_date.to_pydatetime()
            elif not isinstance(row_date, datetime):
                # Convert date to datetime for comparison
                row_date = datetime.combine(row_date, datetime.min.time())

            # Timeframe-specific date matching
            if timeframe.lower() == "daily":
                _match_daily_rsi(
                    row_date, compare_date, row[1], interval_description, week_description, results,
                )
            elif timeframe.lower() == "hourly":
                _match_hourly_rsi(
                    row_date, compare_date, row[1], interval_description, week_description, results,
                )
            elif timeframe.lower() == "fifteen_min":
                _match_fifteen_min_rsi(
                    row_date, compare_date, row[1], interval_description, week_description, results,
                )

    return results


def _match_daily_rsi(
    row_date: datetime,
    compare_date: datetime,
    rsi_value: float,
    interval_desc: str,
    week_desc: str,
    results: dict,
) -> None:
    """Match daily RSI values."""
    seconds_in_day = 86400
    if abs((row_date - (compare_date - timedelta(days=1))).total_seconds()) < seconds_in_day:
        results[interval_desc] = float(rsi_value)
    elif abs((row_date - (compare_date - timedelta(days=7))).total_seconds()) < seconds_in_day:
        results[week_desc] = float(rsi_value)


def _match_hourly_rsi(
    row_date: datetime,
    compare_date: datetime,
    rsi_value: float,
    interval_desc: str,
    week_desc: str,
    results: dict,
) -> None:
    """Match hourly RSI values."""
    seconds_in_hour = 3600
    if abs((row_date - (compare_date - timedelta(hours=1))).total_seconds()) < seconds_in_hour:
        results[interval_desc] = float(rsi_value)
    elif abs((row_date - (compare_date - timedelta(hours=24))).total_seconds()) < seconds_in_hour:
        results[week_desc] = float(rsi_value)


def _match_fifteen_min_rsi(
    row_date: datetime,
    compare_date: datetime,
    rsi_value: float,
    interval_desc: str,
    week_desc: str,
    results: dict,
) -> None:
    """Match fifteen minute RSI values."""
    seconds_in_15_minutes = 900
    if (
        abs((row_date - (compare_date - timedelta(minutes=15))).total_seconds())
        < seconds_in_15_minutes
    ):
        results[interval_desc] = float(rsi_value)
    elif (
        abs((row_date - (compare_date - timedelta(minutes=24 * 15))).total_seconds())
        < seconds_in_15_minutes
    ):
        results[week_desc] = float(rsi_value)


def get_historical_rsi(conn, symbol_id: int, current_date: date, timeframe: str = "daily") -> dict:
    """Fetch RSI values for current date, yesterday, and week ago for a symbol.

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID to fetch RSI for
        current_date: The current date to compare from
        timeframe (str): Timeframe type ("daily", "hourly", "fifteen_min")

    Returns:
        dict: Dictionary containing current, yesterday and week ago RSI values

    """
    results = {}  # Initialize empty results dictionary

    try:
        if conn:
            cursor = conn.cursor()

            # Get timeframe configuration
            candle_table, rsi_table, id_column, previous_interval, week_interval = (
                _get_timeframe_config(timeframe)
            )

            # Get interval settings
            interval_keyword, previous_interval, week_interval = _get_interval_settings(
                timeframe, previous_interval, week_interval,
            )

            # Check if we're using SQLite or SQL Server
            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            # Build the appropriate query
            query = _build_query(
                is_sqlite=is_sqlite,
                candle_table=candle_table,
                rsi_table=rsi_table,
                id_column=id_column,
                interval_keyword=interval_keyword,
                previous_interval=previous_interval,
                week_interval=week_interval,
            )

            # Execute query with appropriate parameters
            if is_sqlite:
                # Convert datetime/Timestamp to ISO format string
                date_param = (
                    current_date.isoformat()
                    if hasattr(current_date, "isoformat")
                    else str(current_date)
                )
                cursor.execute(query, (symbol_id, date_param, date_param))
            else:
                cursor.execute(query, (symbol_id, current_date, current_date))

            # Process results
            rows = cursor.fetchall()
            results = _process_rsi_results(rows, current_date, timeframe)

            cursor.close()

    except pyodbc.Error as e:
        app_logger.error(
            f"ODBC Error while fetching historical {timeframe} RSI for symbol {symbol_id}: {e}",
        )
        raise
    except Exception as e:
        app_logger.error(f"Error fetching historical {timeframe} RSI for symbol {symbol_id}: {e!s}")
        raise

    else:
        return results  # Return results dictionary (empty if conn is None or exception occurs)
