"""ETF (Exchange-Traded Fund) data repository for database operations."""

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from infra.telegram_logging_handler import app_logger


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


class ETFRepository:
    """Repository for ETF inflows/outflows data."""

    def __init__(self, conn: "pyodbc.Connection | SQLiteConnectionWrapper"):
        """Initialize the ETF repository with a database connection."""
        self.conn = conn
        self.is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    def save_etf_flow(
        self,
        ticker: str,
        coin: str,
        issuer: str | None,
        price: float | None,
        aum: float | None,
        flows: float | None,
        flows_change: float | None,
        volume: float | None,
        fetch_date: str,
    ) -> None:
        """Save ETF flow data to database.

        Args:
            ticker: ETF ticker symbol (e.g., 'IBIT', 'FBTC')
            coin: Coin type ('BTC' or 'ETH')
            issuer: ETF issuer (e.g., 'BlackRock', 'Fidelity')
            price: Current ETF price per share
            aum: Assets under management in USD
            flows: Daily net inflows/outflows in USD
            flows_change: Change in flows from previous period
            volume: Trading volume in USD
            fetch_date: Date when data was fetched (YYYY-MM-DD format)
        """
        cursor = self.conn.cursor()

        try:
            if self.is_sqlite:
                # SQLite: Use INSERT OR REPLACE for upsert
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ETFFlows
                    (Ticker, Coin, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticker,
                        coin,
                        issuer,
                        price,
                        aum,
                        flows,
                        flows_change,
                        volume,
                        fetch_date,
                    ),
                )
            else:
                # Azure SQL: Use MERGE for upsert
                cursor.execute(
                    """
                    MERGE INTO ETFFlows AS target
                    USING (SELECT ? AS Ticker, ? AS FetchDate) AS source
                    ON target.Ticker = source.Ticker AND target.FetchDate = source.FetchDate
                    WHEN MATCHED THEN
                        UPDATE SET Coin = ?, Issuer = ?, Price = ?, AUM = ?,
                                 Flows = ?, FlowsChange = ?, Volume = ?
                    WHEN NOT MATCHED THEN
                        INSERT (
                            Ticker, Coin, Issuer, Price, AUM, Flows,
                            FlowsChange, Volume, FetchDate
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        ticker,
                        fetch_date,
                        coin,
                        issuer,
                        price,
                        aum,
                        flows,
                        flows_change,
                        volume,
                        ticker,
                        coin,
                        issuer,
                        price,
                        aum,
                        flows,
                        flows_change,
                        volume,
                        fetch_date,
                    ),
                )

            self.conn.commit()
            app_logger.info(
                f"Saved ETF flow for {ticker} ({coin}): ${flows:,.0f} flows on {fetch_date}",
            )

        except Exception as e:
            app_logger.error(f"Error saving ETF flow for {ticker}: {e!s}")
            self.conn.rollback()
            raise

    def get_available_etf_coins(self) -> list[str]:
        """Get list of all coins that have ETF flow data.

        Returns:
            List of coin symbols (e.g., ['BTC', 'ETH', 'SOL'])
        """
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT DISTINCT Coin
                FROM ETFFlows
                ORDER BY Coin
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            coins = [row[0] for row in rows if row[0]]
            app_logger.info(f"Found {len(coins)} coins with ETF data: {coins}")
            return coins

        except Exception as e:
            app_logger.error(f"Error fetching available ETF coins: {e!s}")
            return []

    def get_latest_etf_flows(self, coin: str) -> list[dict[str, str | float | None]] | None:
        """Get the most recent ETF flows for a specific coin.

        IMPORTANT: Only returns data from TODAY. If no data exists for today,
        returns None instead of falling back to old data.

        Args:
            coin: Coin type ('BTC' or 'ETH')

        Returns:
            List of ETF flow dictionaries for today, or None if no data found for today
        """
        cursor = self.conn.cursor()

        try:
            # Get today's date
            today = datetime.now(UTC).date().isoformat()

            # Query for TODAY's data only (not the most recent date in DB)
            flows_query = """
                SELECT Ticker, Issuer, Price, AUM, Flows, FlowsChange, Volume, FetchDate
                FROM ETFFlows
                WHERE Coin = ? AND FetchDate = ?
                ORDER BY Flows DESC
            """

            cursor.execute(flows_query, (coin, today))
            rows = cursor.fetchall()

            if not rows:
                app_logger.info(f"No ETF data found for {coin} on {today}")
                return None

            results = [
                {
                    "ticker": row[0],
                    "issuer": row[1],
                    "price": row[2],
                    "aum": row[3],
                    "flows": row[4],
                    "flows_change": row[5],
                    "volume": row[6],
                    "fetch_date": row[7],
                }
                for row in rows
            ]

            app_logger.info(f"Retrieved {len(results)} ETF flows for {coin} on {today}")

        except Exception as e:
            app_logger.error(f"Error fetching latest ETF flows for {coin}: {e!s}")
            raise
        else:
            return results

    def get_weekly_etf_flows(
        self,
        coin: str,
        days: int = 7,
    ) -> dict[str, float | int] | None:
        """Get aggregated ETF flows for a coin over the specified number of days.

        Args:
            coin: Coin type ('BTC' or 'ETH')
            days: Number of days to aggregate (default: 7)

        Returns:
            Dictionary with aggregated flow data or None if no data
        """
        cursor = self.conn.cursor()

        try:
            if self.is_sqlite:
                # SQLite: Use date() function for date arithmetic
                query = """
                    SELECT
                        SUM(Flows) as total_flows,
                        AVG(Flows) as avg_daily_flows,
                        COUNT(*) as days_count,
                        MIN(FetchDate) as start_date,
                        MAX(FetchDate) as end_date
                    FROM ETFFlows
                    WHERE Coin = ?
                      AND FetchDate >= date('now', '-' || ? || ' days')
                """
            else:
                # Azure SQL: Use DATEADD function
                query = """
                    SELECT
                        SUM(Flows) as total_flows,
                        AVG(CAST(Flows AS FLOAT)) as avg_daily_flows,
                        COUNT(*) as days_count,
                        MIN(FetchDate) as start_date,
                        MAX(FetchDate) as end_date
                    FROM ETFFlows
                    WHERE Coin = ?
                      AND FetchDate >= DATEADD(DAY, -?, CAST(GETDATE() AS DATE))
                """

            cursor.execute(query, (coin, days))
            row = cursor.fetchone()

            if not row or row[0] is None:
                app_logger.info(f"No ETF flow data found for {coin} in last {days} days")
                return None

            result = {
                "total_flows": row[0],
                "avg_daily_flows": row[1],
                "days_count": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "coin": coin,
            }

            app_logger.info(
                f"Aggregated ETF flows for {coin}: "
                f"${result['total_flows']:,.0f} over {result['days_count']} days",
            )

        except Exception as e:
            app_logger.error(f"Error fetching weekly ETF flows for {coin}: {e!s}")
            raise
        else:
            return result

    def get_etf_flows_by_issuer(
        self,
        coin: str,
        fetch_date: str | None = None,
    ) -> list[dict[str, str | float | None]] | None:
        """Get ETF flows grouped by issuer for a specific coin and date.

        Args:
            coin: Coin type ('BTC' or 'ETH')
            fetch_date: Specific date (YYYY-MM-DD) or None for latest

        Returns:
            List of issuer-grouped ETF flow data or None if no data
        """
        cursor = self.conn.cursor()

        try:
            if fetch_date is None:
                # Get the most recent date for this coin
                date_query = """
                    SELECT FetchDate
                    FROM ETFFlows
                    WHERE Coin = ?
                    ORDER BY FetchDate DESC
                    LIMIT 1
                """

                if not self.is_sqlite:
                    date_query = """
                        SELECT TOP 1 FetchDate
                        FROM ETFFlows
                        WHERE Coin = ?
                        ORDER BY FetchDate DESC
                    """

                cursor.execute(date_query, (coin,))
                date_row = cursor.fetchone()
                if not date_row:
                    return None
                fetch_date = date_row[0]

            # Group by issuer and sum flows
            query = """
                SELECT
                    Issuer,
                    SUM(Flows) as total_flows,
                    COUNT(*) as etf_count,
                    AVG(Price) as avg_price,
                    SUM(AUM) as total_aum
                FROM ETFFlows
                WHERE Coin = ? AND FetchDate = ?
                  AND Issuer IS NOT NULL
                GROUP BY Issuer
                ORDER BY total_flows DESC
            """

            cursor.execute(query, (coin, fetch_date))
            rows = cursor.fetchall()

            if not rows:
                return None

            results = [
                {
                    "issuer": row[0],
                    "total_flows": row[1],
                    "etf_count": row[2],
                    "avg_price": row[3],
                    "total_aum": row[4],
                    "fetch_date": fetch_date,
                }
                for row in rows
            ]

            app_logger.info(
                f"Retrieved ETF flows by issuer for {coin} on {fetch_date}: {len(results)} issuers",
            )

        except Exception as e:
            app_logger.error(f"Error fetching ETF flows by issuer for {coin}: {e!s}")
            raise
        else:
            return results
