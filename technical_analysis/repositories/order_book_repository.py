"""Repository for managing Order Book Metrics data in the database."""

import os
from datetime import datetime
from typing import TYPE_CHECKING

from infra.telegram_logging_handler import app_logger


if TYPE_CHECKING:
    from shared_code.binance import OrderBookMetrics


class OrderBookRepository:
    """Repository for Order Book liquidity metrics data."""

    def __init__(self, conn):
        """Initialize the order book repository with a database connection."""
        self.conn = conn
        self.is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    def save_order_book_metrics(
        self,
        symbol_id: int,
        metrics: "OrderBookMetrics",
        indicator_date: datetime,
    ):
        """Save order book metrics to database.

        Args:
            symbol_id: The symbol ID in the database
            metrics: OrderBookMetrics object with liquidity data
            indicator_date: The date for the indicator

        """
        cursor = self.conn.cursor()

        try:
            if self.is_sqlite:
                # SQLite: Use INSERT OR REPLACE
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO OrderBookMetrics
                    (SymbolID, BestBid, BestBidQty, BestAsk, BestAskQty,
                     SpreadPct, BidVolume2Pct, AskVolume2Pct, BidAskRatio,
                     LargestBidWall, LargestBidWallPrice, LargestAskWall,
                     LargestAskWallPrice, IndicatorDate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol_id,
                        metrics.best_bid,
                        metrics.best_bid_qty,
                        metrics.best_ask,
                        metrics.best_ask_qty,
                        metrics.spread_pct,
                        metrics.bid_volume_2pct,
                        metrics.ask_volume_2pct,
                        metrics.bid_ask_ratio,
                        metrics.largest_bid_wall,
                        metrics.largest_bid_wall_price,
                        metrics.largest_ask_wall,
                        metrics.largest_ask_wall_price,
                        indicator_date.isoformat(),
                    ),
                )
            else:
                # Azure SQL: Use MERGE
                cursor.execute(
                    """
                    MERGE INTO OrderBookMetrics AS target
                    USING (SELECT ? AS SymbolID, ? AS IndicatorDate) AS source
                    ON target.SymbolID = source.SymbolID
                       AND target.IndicatorDate = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET
                            BestBid = ?, BestBidQty = ?, BestAsk = ?, BestAskQty = ?,
                            SpreadPct = ?, BidVolume2Pct = ?, AskVolume2Pct = ?,
                            BidAskRatio = ?, LargestBidWall = ?, LargestBidWallPrice = ?,
                            LargestAskWall = ?, LargestAskWallPrice = ?
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, BestBid, BestBidQty, BestAsk, BestAskQty,
                                SpreadPct, BidVolume2Pct, AskVolume2Pct, BidAskRatio,
                                LargestBidWall, LargestBidWallPrice, LargestAskWall,
                                LargestAskWallPrice, IndicatorDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        symbol_id,
                        indicator_date,
                        # Update values
                        metrics.best_bid,
                        metrics.best_bid_qty,
                        metrics.best_ask,
                        metrics.best_ask_qty,
                        metrics.spread_pct,
                        metrics.bid_volume_2pct,
                        metrics.ask_volume_2pct,
                        metrics.bid_ask_ratio,
                        metrics.largest_bid_wall,
                        metrics.largest_bid_wall_price,
                        metrics.largest_ask_wall,
                        metrics.largest_ask_wall_price,
                        # Insert values
                        symbol_id,
                        metrics.best_bid,
                        metrics.best_bid_qty,
                        metrics.best_ask,
                        metrics.best_ask_qty,
                        metrics.spread_pct,
                        metrics.bid_volume_2pct,
                        metrics.ask_volume_2pct,
                        metrics.bid_ask_ratio,
                        metrics.largest_bid_wall,
                        metrics.largest_bid_wall_price,
                        metrics.largest_ask_wall,
                        metrics.largest_ask_wall_price,
                        indicator_date,
                    ),
                )

            self.conn.commit()
            app_logger.info(
                f"Saved Order Book for {metrics.symbol}: "
                f"B/A Ratio={metrics.bid_ask_ratio:.2f}, "
                f"Spread={metrics.spread_pct:.4f}%",
            )

        except Exception as e:
            app_logger.error(f"Error saving order book metrics: {e!s}")
            self.conn.rollback()
            raise

    def get_latest_order_book_metrics(
        self,
        symbol_id: int,
    ) -> dict[str, object] | None:
        """Get the most recent order book metrics for a symbol.

        Args:
            symbol_id: The symbol ID to query

        Returns:
            Dictionary with order book metrics or None if not found

        """
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT BestBid, BestBidQty, BestAsk, BestAskQty,
                       SpreadPct, BidVolume2Pct, AskVolume2Pct, BidAskRatio,
                       LargestBidWall, LargestBidWallPrice,
                       LargestAskWall, LargestAskWallPrice, IndicatorDate
                FROM OrderBookMetrics
                WHERE SymbolID = ?
                ORDER BY IndicatorDate DESC
                LIMIT 1
            """

            if not self.is_sqlite:
                query = """
                    SELECT TOP 1 BestBid, BestBidQty, BestAsk, BestAskQty,
                           SpreadPct, BidVolume2Pct, AskVolume2Pct, BidAskRatio,
                           LargestBidWall, LargestBidWallPrice,
                           LargestAskWall, LargestAskWallPrice, IndicatorDate
                    FROM OrderBookMetrics
                    WHERE SymbolID = ?
                    ORDER BY IndicatorDate DESC
                """

            cursor.execute(query, (symbol_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "best_bid": row[0],
                    "best_bid_qty": row[1],
                    "best_ask": row[2],
                    "best_ask_qty": row[3],
                    "spread_pct": row[4],
                    "bid_volume_2pct": row[5],
                    "ask_volume_2pct": row[6],
                    "bid_ask_ratio": row[7],
                    "largest_bid_wall": row[8],
                    "largest_bid_wall_price": row[9],
                    "largest_ask_wall": row[10],
                    "largest_ask_wall_price": row[11],
                    "indicator_date": row[12],
                }

        except Exception as e:
            app_logger.error(f"Error fetching order book metrics: {e!s}")
            raise

        return None

    def get_order_book_history(
        self,
        symbol_id: int,
        days: int = 7,
    ) -> list[dict[str, object]]:
        """Get historical order book metrics for a symbol.

        Args:
            symbol_id: The symbol ID to query
            days: Number of days of history to retrieve (default 7)

        Returns:
            List of dictionaries with order book metrics

        """
        cursor = self.conn.cursor()
        results = []

        try:
            query = """
                SELECT BestBid, BestBidQty, BestAsk, BestAskQty,
                       SpreadPct, BidVolume2Pct, AskVolume2Pct, BidAskRatio,
                       LargestBidWall, LargestBidWallPrice,
                       LargestAskWall, LargestAskWallPrice, IndicatorDate
                FROM OrderBookMetrics
                WHERE SymbolID = ?
                  AND IndicatorDate >= date('now', ?)
                ORDER BY IndicatorDate DESC
            """
            days_param = f"-{days} days"

            if not self.is_sqlite:
                query = """
                    SELECT BestBid, BestBidQty, BestAsk, BestAskQty,
                           SpreadPct, BidVolume2Pct, AskVolume2Pct, BidAskRatio,
                           LargestBidWall, LargestBidWallPrice,
                           LargestAskWall, LargestAskWallPrice, IndicatorDate
                    FROM OrderBookMetrics
                    WHERE SymbolID = ?
                      AND IndicatorDate >= DATEADD(day, ?, GETDATE())
                    ORDER BY IndicatorDate DESC
                """
                days_param = -days

            cursor.execute(query, (symbol_id, days_param))
            rows = cursor.fetchall()

            results.extend(
                {
                    "best_bid": row[0],
                    "best_bid_qty": row[1],
                    "best_ask": row[2],
                    "best_ask_qty": row[3],
                    "spread_pct": row[4],
                    "bid_volume_2pct": row[5],
                    "ask_volume_2pct": row[6],
                    "bid_ask_ratio": row[7],
                    "largest_bid_wall": row[8],
                    "largest_bid_wall_price": row[9],
                    "largest_ask_wall": row[10],
                    "largest_ask_wall_price": row[11],
                    "indicator_date": row[12],
                }
                for row in rows
            )

        except Exception as e:
            app_logger.error(f"Error fetching order book history: {e!s}")
            raise

        return results
