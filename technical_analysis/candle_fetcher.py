from datetime import UTC, datetime, timedelta

from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import Candle
from source_repository import Symbol


class CandleFetcher:
    """Base class for fetching candles of different timeframes"""

    def __init__(self, timeframe: str, fetch_function, repository_class):
        """
        Initialize the candle fetcher

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
        """
        Fetches candles for given symbols and returns a list of Candle objects

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

    def check_if_all_candles(self, symbol, conn, days_back: int = 30):  # noqa: PLR0915
        """
        Checks if all candles for the symbol are available in the database,
        fetches missing ones from API

        Args:
            symbol: Symbol object
            conn: Database connection
            days_back: Number of days to look back (default: 30)
        """
        repo = self.repository_class(conn)
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days_back)

        self.logger.info(
            f"Checking {self.timeframe} candles for {symbol.symbol_name} from {start_time} to {end_time}"
        )

        # Get existing candles from DB
        all_candles = repo.get_candles(symbol, start_time, end_time)

        if not all_candles:
            self.logger.info(
                f"No {self.timeframe} candles found in DB for {symbol.symbol_name}, fetching all"
            )
            current_time = start_time
            while current_time <= end_time:
                self.logger.debug(
                    f"Fetching {self.timeframe} candle for {symbol.symbol_name} at {current_time}"
                )
                self.fetch_function(symbol, current_time, conn)

                # Increment based on timeframe
                if self.timeframe == "daily":
                    current_time += timedelta(days=1)
                elif self.timeframe == "hourly":
                    current_time += timedelta(hours=1)
                elif self.timeframe == "15min":
                    current_time += timedelta(minutes=15)
                else:
                    current_time += timedelta(hours=1)  # Default increment
        else:
            self.logger.info(
                f"Found {len(all_candles)} {self.timeframe} candles in DB for {symbol.symbol_name}"
            )

            # Define the expected time difference based on timeframe
            expected_diff = None
            if self.timeframe == "daily":
                expected_diff = timedelta(days=1)
            elif self.timeframe == "hourly":
                expected_diff = timedelta(hours=1)
            elif self.timeframe == "15min":
                expected_diff = timedelta(minutes=15)
            else:
                expected_diff = timedelta(hours=1)  # Default

            # Sort candles by end_date
            all_candles.sort(key=lambda x: x.end_date)

            # Check for missing candles at the beginning of the range
            if all_candles:
                # Ensure timezone consistency for comparison
                first_candle_date = all_candles[0].end_date
                if first_candle_date.tzinfo is None:
                    first_candle_date = first_candle_date.replace(tzinfo=UTC)

                if first_candle_date > start_time:
                    self.logger.info(
                        f"Found gap at beginning: {self.timeframe} candles for {symbol.symbol_name} missing from {start_time} to {first_candle_date}"
                    )
                    current_time = start_time
                    while current_time < first_candle_date:
                        self.logger.debug(
                            f"Fetching missing {self.timeframe} candle for {symbol.symbol_name} at {current_time}"
                        )
                        self.fetch_function(symbol, current_time, conn)
                        current_time += expected_diff

            # Check for gaps in the data
            if len(all_candles) > 1:
                # Check for missing candles between existing ones
                for i in range(len(all_candles) - 1):
                    current_candle = all_candles[i]
                    next_candle = all_candles[i + 1]

                    # Ensure timezone consistency
                    current_date = current_candle.end_date
                    next_date = next_candle.end_date

                    if current_date.tzinfo is None:
                        current_date = current_date.replace(tzinfo=UTC)
                    if next_date.tzinfo is None:
                        next_date = next_date.replace(tzinfo=UTC)

                    # Check if there's a gap
                    actual_diff = next_date - current_date
                    if actual_diff > expected_diff:
                        self.logger.info(
                            f"Found gap in {self.timeframe} candles for {symbol.symbol_name} between {current_date} and {next_date}"
                        )
                        # Fetch missing candles
                        current_time = current_date + expected_diff
                        while current_time < next_date:
                            self.logger.debug(
                                f"Fetching missing {self.timeframe} candle for {symbol.symbol_name} at {current_time}"
                            )
                            self.fetch_function(symbol, current_time, conn)
                            current_time += expected_diff

            # Check for missing candles at the end of the range
            if all_candles:
                # Ensure timezone consistency
                last_candle_date = all_candles[-1].end_date
                if last_candle_date.tzinfo is None:
                    last_candle_date = last_candle_date.replace(tzinfo=UTC)

                if last_candle_date < end_time:
                    self.logger.info(
                        f"Found gap at end: {self.timeframe} candles for {symbol.symbol_name} missing from {last_candle_date} to {end_time}"
                    )
                    current_time = last_candle_date + expected_diff
                    while current_time <= end_time:
                        self.logger.debug(
                            f"Fetching missing {self.timeframe} candle for {symbol.symbol_name} at {current_time}"
                        )
                        self.fetch_function(symbol, current_time, conn)
                        current_time += expected_diff
