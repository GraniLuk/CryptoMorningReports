"""Repository for managing Cumulative Volume Delta (CVD) data in the database."""

import os
from datetime import datetime
from typing import TYPE_CHECKING

from infra.telegram_logging_handler import app_logger


if TYPE_CHECKING:
    from shared_code.binance import CVDMetrics


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

            for row in cursor.fetchall():
                results.append(
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
                    },
                )

        except Exception as e:
            app_logger.error(f"Error fetching CVD history: {e!s}")
            raise

        return results
        return results
