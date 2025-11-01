"""Candle data fetching utilities for different timeframes."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from infra.telegram_logging_handler import app_logger
from shared_code.common_price import Candle
from source_repository import Symbol


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


class CandleFetcher:
    """Base class for fetching candles of different timeframes."""

    def __init__(self, timeframe: str, fetch_function: Callable, repository_class: type):
        """Initialize the candle fetcher.

        Args:
            timeframe: String description of the timeframe (e.g., 'daily', 'hourly', '15min')
            fetch_function: Function to fetch a single candle from API
            repository_class: Repository class to use for database operations

        """
        self.timeframe = timeframe
        self.fetch_function = fetch_function
        self.repository_class = repository_class
        self.logger = app_logger

    def fetch_candles(
        self,
        symbols: list[Symbol],
        conn: "pyodbc.Connection | SQLiteConnectionWrapper",
        end_time: datetime | None = None,
    ) -> list[Candle]:
        """Fetch candles for given symbols and return a list of Candle objects.

        Args:
            symbols: List of Symbol objects
            conn: Database connection
            end_time: End time for fetching candles (defaults to current time)

        Returns:
            List of Candle objects

        """
        end_time = end_time or datetime.now(UTC)
        self.logger.info("Fetching %s candles for %d symbols", self.timeframe, len(symbols))

        candles = []
        for symbol in symbols:
            candle = self.fetch_function(symbol, end_time, conn)
            if candle is not None:
                candles.append(candle)
                self.logger.debug("Fetched %s candle for %s", self.timeframe, symbol.symbol_name)
            else:
                self.logger.warning(
                    "Failed to fetch %s candle for %s",
                    self.timeframe,
                    symbol.symbol_name,
                )

        self.logger.info("Successfully fetched %d %s candles", len(candles), self.timeframe)
        return candles

    def _get_expected_time_diff(self) -> timedelta:
        """Get the expected time difference based on timeframe."""
        if self.timeframe == "daily":
            return timedelta(days=1)
        if self.timeframe == "hourly":
            return timedelta(hours=1)
        if self.timeframe == "15min":
            return timedelta(minutes=15)
        return timedelta(hours=1)  # Default

    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime has UTC timezone."""
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    def _fill_gaps_in_range(
        self,
        symbol: Symbol,
        start_time: datetime,
        end_time: datetime,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper",
        gap_type: str,
    ):
        """Fill gaps in a specific time range."""
        self.logger.info(
            "Found %s gap: %s candles for %s missing from %s to %s",
            gap_type,
            self.timeframe,
            symbol.symbol_name,
            start_time,
            end_time,
        )
        expected_diff = self._get_expected_time_diff()
        current_time = start_time
        while current_time <= end_time:
            self.logger.debug(
                "Fetching missing %s candle for %s at %s",
                self.timeframe,
                symbol.symbol_name,
                current_time,
            )
            self.fetch_function(symbol, current_time, conn)
            current_time += expected_diff

    def _check_beginning_gap(
        self,
        symbol: Symbol,
        all_candles: list[Candle],
        start_time: datetime,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper",
    ):
        """Check and fill gaps at the beginning of the range."""
        if all_candles:
            first_candle_date_str = all_candles[0].end_date
            first_candle_date = self._ensure_timezone(datetime.fromisoformat(first_candle_date_str))
            if first_candle_date > start_time:
                self._fill_gaps_in_range(
                    symbol,
                    start_time,
                    first_candle_date - self._get_expected_time_diff(),
                    conn,
                    "beginning",
                )

    def _check_middle_gaps(self, symbol, all_candles, conn):
        """Check and fill gaps between existing candles."""
        if len(all_candles) > 1:
            expected_diff = self._get_expected_time_diff()
            for i in range(len(all_candles) - 1):
                current_candle = all_candles[i]
                next_candle = all_candles[i + 1]

                current_date = self._ensure_timezone(current_candle.end_date)
                next_date = self._ensure_timezone(next_candle.end_date)

                actual_diff = next_date - current_date
                if actual_diff > expected_diff:
                    self.logger.info(
                        "Found gap in %s candles for %s between %s and %s",
                        self.timeframe,
                        symbol.symbol_name,
                        current_date,
                        next_date,
                    )
                    # Fetch missing candles
                    current_time = current_date + expected_diff
                    while current_time < next_date:
                        self.logger.debug(
                            "Fetching missing %s candle for %s at %s",
                            self.timeframe,
                            symbol.symbol_name,
                            current_time,
                        )
                        self.fetch_function(symbol, current_time, conn)
                        current_time += expected_diff

    def _check_end_gap(
        self,
        symbol: Symbol,
        all_candles: list[Candle],
        end_time: datetime,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper",
    ):
        """Check and fill gaps at the end of the range."""
        if all_candles:
            last_candle_date_str = all_candles[-1].end_date
            last_candle_date = self._ensure_timezone(datetime.fromisoformat(last_candle_date_str))
            if last_candle_date < end_time:
                self._fill_gaps_in_range(
                    symbol,
                    last_candle_date + self._get_expected_time_diff(),
                    end_time,
                    conn,
                    "end",
                )

    def check_if_all_candles(
        self,
        symbol: Symbol,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper",
        days_back: int = 30,
    ):
        """Check if all candles for the symbol are available in the database.

        fetches missing ones from API.

        Args:
            symbol: Symbol object
            conn: Database connection
            days_back: Number of days to look back (default: 30)

        """
        repo = self.repository_class(conn)
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days_back)

        self.logger.info(
            "Checking %s candles for %s from %s to %s",
            self.timeframe,
            symbol.symbol_name,
            start_time,
            end_time,
        )

        # Get existing candles from DB
        all_candles = repo.get_candles(symbol, start_time, end_time)

        if not all_candles:
            self.logger.info(
                "No %s candles found in DB for %s, fetching all",
                self.timeframe,
                symbol.symbol_name,
            )
            current_time = start_time
            expected_diff = self._get_expected_time_diff()
            while current_time <= end_time:
                self.logger.debug(
                    "Fetching %s candle for %s at %s",
                    self.timeframe,
                    symbol.symbol_name,
                    current_time,
                )
                self.fetch_function(symbol, current_time, conn)
                current_time += expected_diff
        else:
            self.logger.info(
                "Found %d %s candles in DB for %s",
                len(all_candles),
                self.timeframe,
                symbol.symbol_name,
            )

            # Sort candles by end_date
            all_candles.sort(key=lambda x: x.end_date)

            # Check for gaps at different positions
            self._check_beginning_gap(symbol, all_candles, start_time, conn)
            self._check_middle_gaps(symbol, all_candles, conn)
            self._check_end_gap(symbol, all_candles, end_time, conn)
