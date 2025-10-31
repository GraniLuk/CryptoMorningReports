"""Candle data fetching utilities for different timeframes."""

from datetime import UTC, datetime, timedelta

from infra.telegram_logging_handler import app_logger
from shared_code.common_price import Candle
from source_repository import Symbol


class CandleFetcher:
    """Base class for fetching candles of different timeframes."""

    def __init__(self, timeframe: str, fetch_function, repository_class):
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
        self, symbols: list[Symbol], conn, end_time: datetime | None = None
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
        self.logger.info(f"Fetching {self.timeframe} candles for {len(symbols)} symbols")

        candles = []
        for symbol in symbols:
            candle = self.fetch_function(symbol, end_time, conn)
            if candle is not None:
                candles.append(candle)
                self.logger.debug(f"Fetched {self.timeframe} candle for {symbol.symbol_name}")
            else:
                self.logger.warning(
                    f"Failed to fetch {self.timeframe} candle for {symbol.symbol_name}"
                )

        self.logger.info(f"Successfully fetched {len(candles)} {self.timeframe} candles")
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
        self, symbol, start_time: datetime, end_time: datetime, conn, gap_type: str
    ):
        """Fill gaps in a specific time range."""
        self.logger.info(
            f"Found {gap_type} gap: {self.timeframe} candles for "
            f"{symbol.symbol_name} missing from {start_time} to {end_time}"
        )
        expected_diff = self._get_expected_time_diff()
        current_time = start_time
        while current_time <= end_time:
            self.logger.debug(
                f"Fetching missing {self.timeframe} candle for "
                f"{symbol.symbol_name} at {current_time}"
            )
            self.fetch_function(symbol, current_time, conn)
            current_time += expected_diff

    def _check_beginning_gap(self, symbol, all_candles, start_time: datetime, conn):
        """Check and fill gaps at the beginning of the range."""
        if all_candles:
            first_candle_date = self._ensure_timezone(all_candles[0].end_date)
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
                        f"Found gap in {self.timeframe} candles for "
                        f"{symbol.symbol_name} between {current_date} and {next_date}"
                    )
                    # Fetch missing candles
                    current_time = current_date + expected_diff
                    while current_time < next_date:
                        self.logger.debug(
                            f"Fetching missing {self.timeframe} candle for "
                            f"{symbol.symbol_name} at {current_time}"
                        )
                        self.fetch_function(symbol, current_time, conn)
                        current_time += expected_diff

    def _check_end_gap(self, symbol, all_candles, end_time: datetime, conn):
        """Check and fill gaps at the end of the range."""
        if all_candles:
            last_candle_date = self._ensure_timezone(all_candles[-1].end_date)
            if last_candle_date < end_time:
                self._fill_gaps_in_range(
                    symbol, last_candle_date + self._get_expected_time_diff(), end_time, conn, "end"
                )

    def check_if_all_candles(self, symbol, conn, days_back: int = 30):
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
            f"Checking {self.timeframe} candles for {symbol.symbol_name} "
            f"from {start_time} to {end_time}"
        )

        # Get existing candles from DB
        all_candles = repo.get_candles(symbol, start_time, end_time)

        if not all_candles:
            self.logger.info(
                f"No {self.timeframe} candles found in DB for {symbol.symbol_name}, fetching all"
            )
            current_time = start_time
            expected_diff = self._get_expected_time_diff()
            while current_time <= end_time:
                self.logger.debug(
                    f"Fetching {self.timeframe} candle for {symbol.symbol_name} at {current_time}"
                )
                self.fetch_function(symbol, current_time, conn)
                current_time += expected_diff
        else:
            self.logger.info(
                f"Found {len(all_candles)} {self.timeframe} candles in DB for {symbol.symbol_name}"
            )

            # Sort candles by end_date
            all_candles.sort(key=lambda x: x.end_date)

            # Check for gaps at different positions
            self._check_beginning_gap(symbol, all_candles, start_time, conn)
            self._check_middle_gaps(symbol, all_candles, conn)
            self._check_end_gap(symbol, all_candles, end_time, conn)
