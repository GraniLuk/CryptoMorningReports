"""Repository for managing Cumulative Volume Delta (CVD) data in the database."""

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from infra.telegram_logging_handler import app_logger


if TYPE_CHECKING:
    from shared_code.binance import CVDHourlySnapshot, CVDMetrics


class CVDRepository:
    """Repository for Cumulative Volume Delta order flow metrics."""

    def __init__(self, conn):
        """Initialize the CVD repository with a database connection."""
        self.conn = conn
        self.is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    def save_cvd_metrics(
        self,
        symbol_id: int,
        metrics: "CVDMetrics",
        indicator_date: datetime,
    ):
        """Save CVD metrics to database.

        Args:
            symbol_id: The symbol ID in the database
            metrics: CVDMetrics object with order flow data
            indicator_date: The date for the indicator

        """
        cursor = self.conn.cursor()

        try:
            if self.is_sqlite:
                # SQLite: Use INSERT OR REPLACE
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO CumulativeVolumeDelta
                    (SymbolID, CVD1h, CVD4h, CVD24h, BuyVolume1h, SellVolume1h,
                     BuyVolume24h, SellVolume24h, TradeCount1h, TradeCount24h,
                     AvgTradeSize, LargeBuyCount, LargeSellCount, IndicatorDate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol_id,
                        metrics.cvd_1h,
                        metrics.cvd_4h,
                        metrics.cvd_24h,
                        metrics.buy_volume_1h,
                        metrics.sell_volume_1h,
                        metrics.buy_volume_24h,
                        metrics.sell_volume_24h,
                        metrics.trade_count_1h,
                        metrics.trade_count_24h,
                        metrics.avg_trade_size,
                        metrics.large_buy_count,
                        metrics.large_sell_count,
                        indicator_date.isoformat(),
                    ),
                )
            else:
                # Azure SQL: Use MERGE
                cursor.execute(
                    """
                    MERGE INTO CumulativeVolumeDelta AS target
                    USING (SELECT ? AS SymbolID, ? AS IndicatorDate) AS source
                    ON target.SymbolID = source.SymbolID
                       AND target.IndicatorDate = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET
                            CVD1h = ?, CVD4h = ?, CVD24h = ?,
                            BuyVolume1h = ?, SellVolume1h = ?,
                            BuyVolume24h = ?, SellVolume24h = ?,
                            TradeCount1h = ?, TradeCount24h = ?,
                            AvgTradeSize = ?, LargeBuyCount = ?, LargeSellCount = ?
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, CVD1h, CVD4h, CVD24h,
                                BuyVolume1h, SellVolume1h, BuyVolume24h, SellVolume24h,
                                TradeCount1h, TradeCount24h, AvgTradeSize,
                                LargeBuyCount, LargeSellCount, IndicatorDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        symbol_id,
                        indicator_date,
                        # UPDATE values
                        metrics.cvd_1h,
                        metrics.cvd_4h,
                        metrics.cvd_24h,
                        metrics.buy_volume_1h,
                        metrics.sell_volume_1h,
                        metrics.buy_volume_24h,
                        metrics.sell_volume_24h,
                        metrics.trade_count_1h,
                        metrics.trade_count_24h,
                        metrics.avg_trade_size,
                        metrics.large_buy_count,
                        metrics.large_sell_count,
                        # INSERT values
                        symbol_id,
                        metrics.cvd_1h,
                        metrics.cvd_4h,
                        metrics.cvd_24h,
                        metrics.buy_volume_1h,
                        metrics.sell_volume_1h,
                        metrics.buy_volume_24h,
                        metrics.sell_volume_24h,
                        metrics.trade_count_1h,
                        metrics.trade_count_24h,
                        metrics.avg_trade_size,
                        metrics.large_buy_count,
                        metrics.large_sell_count,
                        indicator_date,
                    ),
                )

            self.conn.commit()
            app_logger.info(
                f"Saved CVD for {metrics.symbol}: "
                f"1h={metrics.cvd_1h:+,.0f}, "
                f"24h={metrics.cvd_24h:+,.0f}",
            )

        except Exception as e:
            app_logger.error(f"Error saving CVD metrics: {e!s}")
            self.conn.rollback()
            raise

    def get_latest_cvd_metrics(
        self,
        symbol_id: int,
    ) -> dict[str, object] | None:
        """Get the most recent CVD metrics for a symbol.

        Args:
            symbol_id: The symbol ID to query

        Returns:
            Dictionary with CVD metrics or None if not found

        """
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT CVD1h, CVD4h, CVD24h, BuyVolume1h, SellVolume1h,
                       BuyVolume24h, SellVolume24h, TradeCount1h, TradeCount24h,
                       AvgTradeSize, LargeBuyCount, LargeSellCount, IndicatorDate
                FROM CumulativeVolumeDelta
                WHERE SymbolID = ?
                ORDER BY IndicatorDate DESC
                LIMIT 1
            """

            if not self.is_sqlite:
                query = """
                    SELECT TOP 1 CVD1h, CVD4h, CVD24h, BuyVolume1h, SellVolume1h,
                           BuyVolume24h, SellVolume24h, TradeCount1h, TradeCount24h,
                           AvgTradeSize, LargeBuyCount, LargeSellCount, IndicatorDate
                    FROM CumulativeVolumeDelta
                    WHERE SymbolID = ?
                    ORDER BY IndicatorDate DESC
                """

            cursor.execute(query, (symbol_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "cvd_1h": row[0],
                    "cvd_4h": row[1],
                    "cvd_24h": row[2],
                    "buy_volume_1h": row[3],
                    "sell_volume_1h": row[4],
                    "buy_volume_24h": row[5],
                    "sell_volume_24h": row[6],
                    "trade_count_1h": row[7],
                    "trade_count_24h": row[8],
                    "avg_trade_size": row[9],
                    "large_buy_count": row[10],
                    "large_sell_count": row[11],
                    "indicator_date": row[12],
                }

        except Exception as e:
            app_logger.error(f"Error fetching CVD metrics: {e!s}")
            raise

        return None

    def get_cvd_history(
        self,
        symbol_id: int,
        days: int = 7,
    ) -> list[dict[str, object]]:
        """Get historical CVD metrics for a symbol.

        Args:
            symbol_id: The symbol ID to query
            days: Number of days of history to retrieve (default 7)

        Returns:
            List of dictionaries with CVD metrics

        """
        cursor = self.conn.cursor()
        results = []

        try:
            query = """
                SELECT CVD1h, CVD4h, CVD24h, BuyVolume1h, SellVolume1h,
                       BuyVolume24h, SellVolume24h, TradeCount1h, TradeCount24h,
                       AvgTradeSize, LargeBuyCount, LargeSellCount, IndicatorDate
                FROM CumulativeVolumeDelta
                WHERE SymbolID = ?
                  AND IndicatorDate >= date('now', ?)
                ORDER BY IndicatorDate DESC
            """
            days_param = f"-{days} days"

            if not self.is_sqlite:
                query = """
                    SELECT CVD1h, CVD4h, CVD24h, BuyVolume1h, SellVolume1h,
                           BuyVolume24h, SellVolume24h, TradeCount1h, TradeCount24h,
                           AvgTradeSize, LargeBuyCount, LargeSellCount, IndicatorDate
                    FROM CumulativeVolumeDelta
                    WHERE SymbolID = ?
                      AND IndicatorDate >= DATEADD(day, ?, GETUTCDATE())
                    ORDER BY IndicatorDate DESC
                """
                days_param = -days

            cursor.execute(query, (symbol_id, days_param))

            results.extend(
                {
                    "cvd_1h": row[0],
                    "cvd_4h": row[1],
                    "cvd_24h": row[2],
                    "buy_volume_1h": row[3],
                    "sell_volume_1h": row[4],
                    "buy_volume_24h": row[5],
                    "sell_volume_24h": row[6],
                    "trade_count_1h": row[7],
                    "trade_count_24h": row[8],
                    "avg_trade_size": row[9],
                    "large_buy_count": row[10],
                    "large_sell_count": row[11],
                    "indicator_date": row[12],
                }
                for row in cursor.fetchall()
            )

        except Exception as e:
            app_logger.error(f"Error fetching CVD history: {e!s}")
            raise

        return results

    # ==================== Hourly Snapshots Methods ====================

    def save_hourly_snapshot(
        self,
        snapshot: "CVDHourlySnapshot",
    ) -> None:
        """Save or update an hourly CVD snapshot.

        Uses UPSERT logic: if a snapshot for the same hour exists, it will
        be updated with accumulated values (not replaced).

        Args:
            snapshot: CVDHourlySnapshot object with hourly data

        """
        cursor = self.conn.cursor()
        hour_ts = snapshot.hour_timestamp.isoformat()

        try:
            if self.is_sqlite:
                # SQLite: Check if exists, then update or insert
                cursor.execute(
                    """
                    SELECT Id, CVD, BuyVolume, SellVolume, TradeCount,
                           LargeBuyCount, LargeSellCount, LastTradeId
                    FROM CVDHourlySnapshots
                    WHERE SymbolID = ? AND HourTimestamp = ?
                    """,
                    (snapshot.symbol_id, hour_ts),
                )
                existing = cursor.fetchone()

                if existing:
                    # Update: add new values to existing (accumulate)
                    # Only update if we have newer trades
                    existing_last_id = existing[7] or 0
                    if snapshot.last_trade_id and snapshot.last_trade_id > existing_last_id:
                        cursor.execute(
                            """
                            UPDATE CVDHourlySnapshots
                            SET CVD = CVD + ?,
                                BuyVolume = BuyVolume + ?,
                                SellVolume = SellVolume + ?,
                                TradeCount = TradeCount + ?,
                                LargeBuyCount = LargeBuyCount + ?,
                                LargeSellCount = LargeSellCount + ?,
                                AvgTradeSize = ?,
                                LastTradeId = ?,
                                UpdatedAt = CURRENT_TIMESTAMP
                            WHERE SymbolID = ? AND HourTimestamp = ?
                            """,
                            (
                                snapshot.cvd,
                                snapshot.buy_volume,
                                snapshot.sell_volume,
                                snapshot.trade_count,
                                snapshot.large_buy_count,
                                snapshot.large_sell_count,
                                snapshot.avg_trade_size,
                                snapshot.last_trade_id,
                                snapshot.symbol_id,
                                hour_ts,
                            ),
                        )
                else:
                    # Insert new snapshot
                    cursor.execute(
                        """
                        INSERT INTO CVDHourlySnapshots
                        (SymbolID, HourTimestamp, CVD, BuyVolume, SellVolume,
                         TradeCount, LargeBuyCount, LargeSellCount,
                         AvgTradeSize, LastTradeId)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            snapshot.symbol_id,
                            hour_ts,
                            snapshot.cvd,
                            snapshot.buy_volume,
                            snapshot.sell_volume,
                            snapshot.trade_count,
                            snapshot.large_buy_count,
                            snapshot.large_sell_count,
                            snapshot.avg_trade_size,
                            snapshot.last_trade_id,
                        ),
                    )
            else:
                # Azure SQL: Use MERGE with accumulation logic
                cursor.execute(
                    """
                    MERGE INTO CVDHourlySnapshots AS target
                    USING (SELECT ? AS SymbolID, ? AS HourTimestamp) AS source
                    ON target.SymbolID = source.SymbolID
                       AND target.HourTimestamp = source.HourTimestamp
                    WHEN MATCHED AND ? > ISNULL(target.LastTradeId, 0) THEN
                        UPDATE SET
                            CVD = target.CVD + ?,
                            BuyVolume = target.BuyVolume + ?,
                            SellVolume = target.SellVolume + ?,
                            TradeCount = target.TradeCount + ?,
                            LargeBuyCount = target.LargeBuyCount + ?,
                            LargeSellCount = target.LargeSellCount + ?,
                            AvgTradeSize = ?,
                            LastTradeId = ?,
                            UpdatedAt = GETUTCDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, HourTimestamp, CVD, BuyVolume, SellVolume,
                                TradeCount, LargeBuyCount, LargeSellCount,
                                AvgTradeSize, LastTradeId)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        snapshot.symbol_id,
                        hour_ts,
                        # MATCHED condition
                        snapshot.last_trade_id,
                        # UPDATE values
                        snapshot.cvd,
                        snapshot.buy_volume,
                        snapshot.sell_volume,
                        snapshot.trade_count,
                        snapshot.large_buy_count,
                        snapshot.large_sell_count,
                        snapshot.avg_trade_size,
                        snapshot.last_trade_id,
                        # INSERT values
                        snapshot.symbol_id,
                        hour_ts,
                        snapshot.cvd,
                        snapshot.buy_volume,
                        snapshot.sell_volume,
                        snapshot.trade_count,
                        snapshot.large_buy_count,
                        snapshot.large_sell_count,
                        snapshot.avg_trade_size,
                        snapshot.last_trade_id,
                    ),
                )

            self.conn.commit()

        except Exception as e:
            app_logger.error(f"Error saving hourly snapshot: {e!s}")
            self.conn.rollback()
            raise

    def save_hourly_snapshots(
        self,
        snapshots: list["CVDHourlySnapshot"],
    ) -> int:
        """Save multiple hourly snapshots.

        Args:
            snapshots: List of CVDHourlySnapshot objects

        Returns:
            Number of snapshots saved

        """
        saved = 0
        for snapshot in snapshots:
            try:
                self.save_hourly_snapshot(snapshot)
                saved += 1
            except (sqlite3.Error, TypeError, ValueError) as exc:
                app_logger.error(
                    f"Failed to save snapshot for hour {snapshot.hour_timestamp}: {exc!s}",
                )
        return saved

    def get_last_trade_id(self, symbol_id: int) -> int | None:
        """Get the last trade ID we have stored for a symbol.

        Args:
            symbol_id: The symbol ID to query

        Returns:
            Last trade ID or None if no data exists

        """
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT MAX(LastTradeId)
                FROM CVDHourlySnapshots
                WHERE SymbolID = ?
            """
            cursor.execute(query, (symbol_id,))
            row = cursor.fetchone()
        except (sqlite3.Error, TypeError) as e:
            app_logger.error(f"Error getting last trade ID: {e!s}")
            return None
        else:
            return row[0] if row and row[0] else None

    def get_oldest_snapshot_time(self, symbol_id: int) -> datetime | None:
        """Get the oldest snapshot time we have for a symbol.

        Args:
            symbol_id: The symbol ID to query

        Returns:
            Oldest snapshot datetime or None if no data exists

        """
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT MIN(HourTimestamp)
                FROM CVDHourlySnapshots
                WHERE SymbolID = ?
            """
            cursor.execute(query, (symbol_id,))
            row = cursor.fetchone()
        except (sqlite3.Error, TypeError) as e:
            app_logger.error(f"Error getting oldest snapshot time: {e!s}")
            return None
        else:
            if row and row[0]:
                return datetime.fromisoformat(row[0]).replace(tzinfo=UTC)
            return None

    def aggregate_cvd_for_hours(
        self,
        symbol_id: int,
        hours: int,
    ) -> dict[str, float | int] | None:
        """Aggregate CVD data for the last N hours from hourly snapshots.

        Args:
            symbol_id: The symbol ID to query
            hours: Number of hours to aggregate (e.g., 1, 4, 24)

        Returns:
            Dictionary with aggregated CVD metrics or None if no data

        """
        cursor = self.conn.cursor()
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=hours)

        try:
            if self.is_sqlite:
                query = """
                    SELECT
                        SUM(CVD) as total_cvd,
                        SUM(BuyVolume) as total_buy_volume,
                        SUM(SellVolume) as total_sell_volume,
                        SUM(TradeCount) as total_trade_count,
                        SUM(LargeBuyCount) as total_large_buys,
                        SUM(LargeSellCount) as total_large_sells,
                        AVG(AvgTradeSize) as avg_trade_size,
                        COUNT(*) as hour_count
                    FROM CVDHourlySnapshots
                    WHERE SymbolID = ?
                      AND HourTimestamp >= ?
                """
                cursor.execute(query, (symbol_id, cutoff.isoformat()))
            else:
                query = """
                    SELECT
                        SUM(CVD) as total_cvd,
                        SUM(BuyVolume) as total_buy_volume,
                        SUM(SellVolume) as total_sell_volume,
                        SUM(TradeCount) as total_trade_count,
                        SUM(LargeBuyCount) as total_large_buys,
                        SUM(LargeSellCount) as total_large_sells,
                        AVG(AvgTradeSize) as avg_trade_size,
                        COUNT(*) as hour_count
                    FROM CVDHourlySnapshots
                    WHERE SymbolID = ?
                      AND HourTimestamp >= ?
                """
                cursor.execute(query, (symbol_id, cutoff))

            row = cursor.fetchone()

        except (sqlite3.Error, TypeError) as e:
            app_logger.error(f"Error aggregating CVD for {hours}h: {e!s}")
            return None
        else:
            if row and row[7] > 0:  # hour_count > 0
                return {
                    "cvd": row[0] or 0,
                    "buy_volume": row[1] or 0,
                    "sell_volume": row[2] or 0,
                    "trade_count": int(row[3] or 0),
                    "large_buy_count": int(row[4] or 0),
                    "large_sell_count": int(row[5] or 0),
                    "avg_trade_size": row[6] or 0,
                    "hour_count": row[7],
                }

            return None

    def cleanup_old_snapshots(self, symbol_id: int, keep_hours: int = 48) -> int:
        """Remove hourly snapshots older than keep_hours.

        Args:
            symbol_id: The symbol ID to clean up
            keep_hours: Number of hours of data to keep (default 48)

        Returns:
            Number of rows deleted

        """
        cursor = self.conn.cursor()
        cutoff = datetime.now(UTC) - timedelta(hours=keep_hours)

        try:
            if self.is_sqlite:
                cursor.execute(
                    """
                    DELETE FROM CVDHourlySnapshots
                    WHERE SymbolID = ? AND HourTimestamp < ?
                    """,
                    (symbol_id, cutoff.isoformat()),
                )
            else:
                cursor.execute(
                    """
                    DELETE FROM CVDHourlySnapshots
                    WHERE SymbolID = ? AND HourTimestamp < ?
                    """,
                    (symbol_id, cutoff),
                )

            deleted = cursor.rowcount
            self.conn.commit()

        except (sqlite3.Error, TypeError) as e:
            app_logger.error(f"Error cleaning up old snapshots: {e!s}")
            self.conn.rollback()
            return 0
        else:
            if deleted > 0:
                app_logger.info(
                    f"Cleaned up {deleted} old CVD snapshots for symbol {symbol_id}",
                )

            return deleted
