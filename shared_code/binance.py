"""Binance API integration for cryptocurrency data fetching."""

from datetime import UTC, date, datetime, timedelta

import pandas as pd
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

from infra.telegram_logging_handler import app_logger
from shared_code.common_price import Candle, TickerPrice
from source_repository import SourceID, Symbol


class FuturesMetrics:
    """Data class for futures market metrics."""

    def __init__(
        self,
        symbol: str,
        open_interest: float,
        open_interest_value: float,
        funding_rate: float,
        next_funding_time: datetime,
        timestamp: datetime,
    ):
        """Initialize futures market metrics with the provided data."""
        self.symbol = symbol
        self.open_interest = open_interest
        self.open_interest_value = open_interest_value
        self.funding_rate = funding_rate
        self.next_funding_time = next_funding_time
        self.timestamp = timestamp

    def __repr__(self):
        """Return a string representation of the FuturesMetrics object."""
        return (
            f"FuturesMetrics(symbol={self.symbol}, "
            f"open_interest={self.open_interest}, "
            f"open_interest_value={self.open_interest_value}, "
            f"funding_rate={self.funding_rate:.6f}%, "
            f"next_funding_time={self.next_funding_time})"
        )


def fetch_binance_futures_metrics(symbol: Symbol) -> FuturesMetrics | None:
    """Fetch Open Interest and Funding Rate from Binance Futures.

    Args:
        symbol: Symbol object with binance_name property

    Returns:
        FuturesMetrics object if successful, None otherwise

    """
    client = BinanceClient()

    try:
        # Fetch Open Interest
        oi_response = client.futures_open_interest(symbol=symbol.binance_name)
        open_interest = float(oi_response.get("openInterest", 0))
        oi_timestamp = datetime.fromtimestamp(oi_response.get("time", 0) / 1000, tz=UTC)

        # Fetch current price to calculate OI value
        ticker = client.futures_ticker(symbol=symbol.binance_name)
        last_price = float(ticker.get("lastPrice", 0))
        open_interest_value = open_interest * last_price

        # Fetch Funding Rate
        funding_response = client.futures_funding_rate(symbol=symbol.binance_name, limit=1)

        if not funding_response:
            app_logger.warning(f"No funding rate data for {symbol.symbol_name}")
            return None

        funding_rate = (
            float(funding_response[0].get("fundingRate", 0)) * 100
        )  # Convert to percentage

        # Get next funding time from mark price
        mark_price = client.futures_mark_price(symbol=symbol.binance_name)
        next_funding_time = datetime.fromtimestamp(
            mark_price.get("nextFundingTime", 0) / 1000,
            tz=UTC,
        )

        return FuturesMetrics(
            symbol=symbol.symbol_name,
            open_interest=open_interest,
            open_interest_value=open_interest_value,
            funding_rate=funding_rate,
            next_funding_time=next_funding_time,
            timestamp=oi_timestamp,
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching futures metrics for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error fetching futures metrics for {symbol.symbol_name}: {e!s}",
        )
        return None


class OrderBookMetrics:
    """Data class for order book liquidity metrics."""

    def __init__(
        self,
        symbol: str,
        best_bid: float,
        best_bid_qty: float,
        best_ask: float,
        best_ask_qty: float,
        spread_pct: float,
        bid_volume_2pct: float,
        ask_volume_2pct: float,
        bid_ask_ratio: float,
        largest_bid_wall: float,
        largest_bid_wall_price: float,
        largest_ask_wall: float,
        largest_ask_wall_price: float,
        depth_levels: dict,
        timestamp: datetime,
    ):
        """Initialize order book metrics with liquidity data."""
        self.symbol = symbol
        self.best_bid = best_bid
        self.best_bid_qty = best_bid_qty
        self.best_ask = best_ask
        self.best_ask_qty = best_ask_qty
        self.spread_pct = spread_pct
        self.bid_volume_2pct = bid_volume_2pct
        self.ask_volume_2pct = ask_volume_2pct
        self.bid_ask_ratio = bid_ask_ratio
        self.largest_bid_wall = largest_bid_wall
        self.largest_bid_wall_price = largest_bid_wall_price
        self.largest_ask_wall = largest_ask_wall
        self.largest_ask_wall_price = largest_ask_wall_price
        self.depth_levels = depth_levels  # {"0.5%": {"bid": x, "ask": y}, "1%": {...}, "2%": {...}}
        self.timestamp = timestamp

    def __repr__(self):
        """Return a string representation of the OrderBookMetrics object."""
        return (
            f"OrderBookMetrics(symbol={self.symbol}, "
            f"spread={self.spread_pct:.4f}%, "
            f"bid_ask_ratio={self.bid_ask_ratio:.2f}, "
            f"bid_vol_2pct=${self.bid_volume_2pct:,.0f}, "
            f"ask_vol_2pct=${self.ask_volume_2pct:,.0f})"
        )


def _calculate_order_book_metrics(
    symbol_name: str,
    bids: list,
    asks: list,
    current_price: float,
) -> OrderBookMetrics | None:
    """Calculate liquidity metrics from raw order book data.

    Args:
        symbol_name: Symbol name (e.g., "BTC")
        bids: List of [price, quantity] bid orders (highest first)
        asks: List of [price, quantity] ask orders (lowest first)
        current_price: Current market price for USD value calculation

    Returns:
        OrderBookMetrics object with calculated liquidity data

    """
    if not bids or not asks:
        return None

    try:
        # Best bid/ask
        best_bid = float(bids[0][0])
        best_bid_qty = float(bids[0][1])
        best_ask = float(asks[0][0])
        best_ask_qty = float(asks[0][1])

        # Mid-price and spread
        mid_price = (best_bid + best_ask) / 2
        spread_pct = ((best_ask - best_bid) / mid_price) * 100 if mid_price > 0 else 0

        # Calculate volume at different price levels
        def calc_volume_at_level(orders: list, mid: float, pct: float, is_bid: bool) -> float:
            """Calculate total USD volume within pct% of mid-price."""
            total_volume = 0.0
            for price_str, qty_str in orders:
                price = float(price_str)
                qty = float(qty_str)
                if is_bid:
                    # For bids, include orders above (mid * (1 - pct/100))
                    if price >= mid * (1 - pct / 100):
                        total_volume += price * qty
                else:
                    # For asks, include orders below (mid * (1 + pct/100))
                    if price <= mid * (1 + pct / 100):
                        total_volume += price * qty
            return total_volume

        # Calculate depth at multiple levels
        depth_levels = {}
        for pct in [0.5, 1.0, 2.0]:
            bid_vol = calc_volume_at_level(bids, mid_price, pct, is_bid=True)
            ask_vol = calc_volume_at_level(asks, mid_price, pct, is_bid=False)
            depth_levels[f"{pct}%"] = {"bid": bid_vol, "ask": ask_vol}

        bid_volume_2pct = depth_levels["2.0%"]["bid"]
        ask_volume_2pct = depth_levels["2.0%"]["ask"]

        # Bid/Ask ratio (avoid division by zero)
        bid_ask_ratio = bid_volume_2pct / ask_volume_2pct if ask_volume_2pct > 0 else 0

        # Find largest walls (orders > 2x average within 2% range)
        def find_largest_wall(orders: list, mid: float, pct: float, is_bid: bool) -> tuple:
            """Find the largest single order within pct% of mid-price."""
            largest_value = 0.0
            largest_price = 0.0
            for price_str, qty_str in orders:
                price = float(price_str)
                qty = float(qty_str)
                order_value = price * qty
                if is_bid:
                    if price >= mid * (1 - pct / 100) and order_value > largest_value:
                        largest_value = order_value
                        largest_price = price
                else:
                    if price <= mid * (1 + pct / 100) and order_value > largest_value:
                        largest_value = order_value
                        largest_price = price
            return largest_value, largest_price

        largest_bid_wall, largest_bid_wall_price = find_largest_wall(
            bids,
            mid_price,
            2.0,
            is_bid=True,
        )
        largest_ask_wall, largest_ask_wall_price = find_largest_wall(
            asks,
            mid_price,
            2.0,
            is_bid=False,
        )

        return OrderBookMetrics(
            symbol=symbol_name,
            best_bid=best_bid,
            best_bid_qty=best_bid_qty,
            best_ask=best_ask,
            best_ask_qty=best_ask_qty,
            spread_pct=spread_pct,
            bid_volume_2pct=bid_volume_2pct,
            ask_volume_2pct=ask_volume_2pct,
            bid_ask_ratio=bid_ask_ratio,
            largest_bid_wall=largest_bid_wall,
            largest_bid_wall_price=largest_bid_wall_price,
            largest_ask_wall=largest_ask_wall,
            largest_ask_wall_price=largest_ask_wall_price,
            depth_levels=depth_levels,
            timestamp=datetime.now(UTC),
        )

    except (IndexError, ValueError, TypeError, ZeroDivisionError) as e:
        app_logger.error(f"Error calculating order book metrics for {symbol_name}: {e!s}")
        return None


def fetch_binance_order_book(symbol: Symbol, limit: int = 100) -> OrderBookMetrics | None:
    """Fetch order book depth from Binance Spot API.

    Args:
        symbol: Symbol object with binance_name property
        limit: Number of price levels to fetch (default 100, max 5000)
               Weight: 1-100=5, 101-500=25, 501-1000=50, 1001-5000=250

    Returns:
        OrderBookMetrics object if successful, None otherwise

    """
    client = BinanceClient()

    try:
        # Fetch order book depth
        depth = client.get_order_book(symbol=symbol.binance_name, limit=limit)

        bids = depth.get("bids", [])
        asks = depth.get("asks", [])

        # Get current price for USD calculations
        ticker = client.get_ticker(symbol=symbol.binance_name)
        current_price = float(ticker.get("lastPrice", 0))

        return _calculate_order_book_metrics(
            symbol_name=symbol.symbol_name,
            bids=bids,
            asks=asks,
            current_price=current_price,
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching order book for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(f"Unexpected error fetching order book for {symbol.symbol_name}: {e!s}")
        return None


def fetch_binance_futures_order_book(symbol: Symbol, limit: int = 100) -> OrderBookMetrics | None:
    """Fetch order book depth from Binance Futures API.

    Args:
        symbol: Symbol object with binance_name property
        limit: Number of price levels to fetch (default 100)

    Returns:
        OrderBookMetrics object if successful, None otherwise

    """
    client = BinanceClient()

    try:
        # Fetch futures order book depth
        depth = client.futures_order_book(symbol=symbol.binance_name, limit=limit)

        bids = depth.get("bids", [])
        asks = depth.get("asks", [])

        # Get current futures price
        ticker = client.futures_ticker(symbol=symbol.binance_name)
        current_price = float(ticker.get("lastPrice", 0))

        return _calculate_order_book_metrics(
            symbol_name=symbol.symbol_name,
            bids=bids,
            asks=asks,
            current_price=current_price,
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error fetching futures order book for {symbol.symbol_name}: {e.message}",
        )
        return None
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error fetching futures order book for {symbol.symbol_name}: {e!s}",
        )
        return None


class CVDMetrics:
    """Data class for Cumulative Volume Delta (order flow) metrics."""

    def __init__(
        self,
        symbol: str,
        cvd_1h: float,
        cvd_4h: float,
        cvd_24h: float,
        buy_volume_1h: float,
        sell_volume_1h: float,
        buy_volume_24h: float,
        sell_volume_24h: float,
        trade_count_1h: int,
        trade_count_24h: int,
        avg_trade_size: float,
        large_buy_count: int,
        large_sell_count: int,
        timestamp: datetime,
    ):
        """Initialize CVD metrics with order flow data."""
        self.symbol = symbol
        self.cvd_1h = cvd_1h  # CVD for last 1 hour
        self.cvd_4h = cvd_4h  # CVD for last 4 hours
        self.cvd_24h = cvd_24h  # CVD for last 24 hours
        self.buy_volume_1h = buy_volume_1h
        self.sell_volume_1h = sell_volume_1h
        self.buy_volume_24h = buy_volume_24h
        self.sell_volume_24h = sell_volume_24h
        self.trade_count_1h = trade_count_1h
        self.trade_count_24h = trade_count_24h
        self.avg_trade_size = avg_trade_size
        self.large_buy_count = large_buy_count  # Trades > 2x average
        self.large_sell_count = large_sell_count
        self.timestamp = timestamp

    def __repr__(self):
        """Return a string representation of the CVDMetrics object."""
        return (
            f"CVDMetrics(symbol={self.symbol}, "
            f"cvd_1h={self.cvd_1h:+,.0f}, "
            f"cvd_24h={self.cvd_24h:+,.0f}, "
            f"buy_vol_24h=${self.buy_volume_24h:,.0f}, "
            f"sell_vol_24h=${self.sell_volume_24h:,.0f})"
        )


# CVD threshold for "large" trade multiplier
CVD_LARGE_TRADE_MULTIPLIER = 2.0


def fetch_binance_cvd(symbol: Symbol, hours: int = 24) -> CVDMetrics | None:
    """Fetch Cumulative Volume Delta from Binance aggregate trades.

    CVD = Sum of (buy volume - sell volume) over time.
    - Positive CVD = net buying pressure (bullish)
    - Negative CVD = net selling pressure (bearish)

    Uses aggregate trades endpoint which includes isBuyerMaker field:
    - isBuyerMaker=True: Seller was the taker (sell order)
    - isBuyerMaker=False: Buyer was the taker (buy order)

    Args:
        symbol: Symbol object with binance_name property
        hours: Number of hours to analyze (default 24, max recommended 24)

    Returns:
        CVDMetrics object if successful, None otherwise

    """
    client = BinanceClient()

    try:
        # Calculate time ranges
        now = datetime.now(UTC)
        start_time_24h = int((now - timedelta(hours=hours)).timestamp() * 1000)
        start_time_4h = int((now - timedelta(hours=4)).timestamp() * 1000)
        start_time_1h = int((now - timedelta(hours=1)).timestamp() * 1000)

        # Fetch aggregate trades for the period
        # Note: API returns max 1000 trades per call, we may need multiple calls
        all_trades = []
        last_trade_id = None

        # Fetch trades in batches (limit 1000 per call)
        while True:
            params = {
                "symbol": symbol.binance_name,
                "startTime": start_time_24h,
                "limit": 1000,
            }
            if last_trade_id:
                params["fromId"] = last_trade_id + 1
                del params["startTime"]

            trades = client.get_aggregate_trades(**params)

            if not trades:
                break

            all_trades.extend(trades)
            last_trade_id = trades[-1]["a"]  # 'a' is aggregate trade ID

            # Stop if we have enough trades or reached time limit
            if len(trades) < 1000:
                break

            # Safety limit to prevent infinite loops
            if len(all_trades) > 50000:
                app_logger.warning(
                    f"CVD fetch for {symbol.symbol_name}: Hit 50k trade limit",
                )
                break

        if not all_trades:
            app_logger.warning(f"No aggregate trades found for {symbol.symbol_name}")
            return None

        # Process trades and calculate CVD
        cvd_1h = 0.0
        cvd_4h = 0.0
        cvd_24h = 0.0
        buy_volume_1h = 0.0
        sell_volume_1h = 0.0
        buy_volume_24h = 0.0
        sell_volume_24h = 0.0
        trade_count_1h = 0
        trade_count_24h = 0
        trade_sizes = []

        for trade in all_trades:
            trade_time = trade["T"]  # Trade time in ms
            qty = float(trade["q"])  # Quantity
            price = float(trade["p"])  # Price
            is_buyer_maker = trade["m"]  # True = seller was taker (sell)
            usd_value = qty * price

            trade_sizes.append(usd_value)
            trade_count_24h += 1

            # Determine buy vs sell
            # isBuyerMaker=True means the buyer was maker, so taker was seller (SELL)
            # isBuyerMaker=False means the seller was maker, so taker was buyer (BUY)
            if is_buyer_maker:
                # Seller was taker = SELL
                sell_volume_24h += usd_value
                cvd_24h -= usd_value
            else:
                # Buyer was taker = BUY
                buy_volume_24h += usd_value
                cvd_24h += usd_value

            # 4h window
            if trade_time >= start_time_4h:
                if is_buyer_maker:
                    cvd_4h -= usd_value
                else:
                    cvd_4h += usd_value

            # 1h window
            if trade_time >= start_time_1h:
                trade_count_1h += 1
                if is_buyer_maker:
                    sell_volume_1h += usd_value
                    cvd_1h -= usd_value
                else:
                    buy_volume_1h += usd_value
                    cvd_1h += usd_value

        # Calculate average trade size and count large trades
        avg_trade_size = sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0
        large_threshold = avg_trade_size * CVD_LARGE_TRADE_MULTIPLIER

        large_buy_count = 0
        large_sell_count = 0

        for trade in all_trades:
            usd_value = float(trade["q"]) * float(trade["p"])
            if usd_value >= large_threshold:
                if trade["m"]:  # Seller was taker
                    large_sell_count += 1
                else:
                    large_buy_count += 1

        return CVDMetrics(
            symbol=symbol.symbol_name,
            cvd_1h=cvd_1h,
            cvd_4h=cvd_4h,
            cvd_24h=cvd_24h,
            buy_volume_1h=buy_volume_1h,
            sell_volume_1h=sell_volume_1h,
            buy_volume_24h=buy_volume_24h,
            sell_volume_24h=sell_volume_24h,
            trade_count_1h=trade_count_1h,
            trade_count_24h=trade_count_24h,
            avg_trade_size=avg_trade_size,
            large_buy_count=large_buy_count,
            large_sell_count=large_sell_count,
            timestamp=now,
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching CVD for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(f"Unexpected error fetching CVD for {symbol.symbol_name}: {e!s}")
        return None


def fetch_binance_price(symbol: Symbol) -> TickerPrice | None:
    """Fetch price data from Binance exchange."""
    # Initialize the client
    client = BinanceClient()
    try:
        # Get 24hr stats
        ticker = client.get_ticker(symbol=symbol.binance_name)
        return TickerPrice(
            source=SourceID.BINANCE,
            symbol=symbol.symbol_name,
            low=float(ticker["lowPrice"]),
            high=float(ticker["highPrice"]),
            last=float(ticker["lastPrice"]),
            volume=float(ticker["volume"]),
            volume_quote=float(ticker.get("quoteVolume", 0)),
        )
    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol}: {e!s}")
        return None


def fetch_close_prices_from_binance(symbol: str, lookback_days: int = 14) -> pd.DataFrame:
    """Fetch historical close prices from Binance for a given symbol."""
    client = BinanceClient()

    try:
        start_time = datetime.now(UTC) - timedelta(days=lookback_days)

        klines = client.get_historical_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            start_str=start_time.strftime("%d %b %Y"),
            limit=lookback_days,
        )

        # Create DataFrame with numeric types
        # Using list comprehension to create DataFrame with named columns
        if klines:
            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_volume",
                    "trades",
                    "taker_buy_base",
                    "taker_buy_quote",
                    "ignore",
                ],
            )
        else:
            # Return empty DataFrame with proper columns if no data
            return pd.DataFrame(columns=["timestamp", "close"])

        # Convert price columns to float
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching data for {symbol}: {e.message}")
        return pd.DataFrame()
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol}: {e!s}")
        return pd.DataFrame()
    else:
        return df


def fetch_binance_daily_kline(symbol: Symbol, end_date: date | None = None) -> Candle | None:
    """Fetch open and close prices from Binance for the last full day."""
    if end_date is None:
        end_date = datetime.now(UTC).date()
    client = BinanceClient()

    # Get yesterday's date
    end_date_timestamp = datetime.combine(end_date, datetime.min.time()).timestamp()
    start_date_timestamp = datetime.combine(
        end_date - timedelta(days=1),
        datetime.min.time(),
    ).timestamp()

    try:
        # Fetch 1-day Kline (candlestick) data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1DAY,
            startTime=int(start_date_timestamp * 1000),
            endTime=int(end_date_timestamp * 1000),
        )

        if not klines:
            app_logger.error(f"No Kline data found for {symbol}")
            return None

        return Candle(
            end_date=end_date.isoformat() if isinstance(end_date, date) else str(end_date),
            source=SourceID.BINANCE.value,
            open=float(klines[0][1]),
            close=float(klines[0][4]),
            symbol=symbol.symbol_name,
            low=float(klines[0][3]),
            high=float(klines[0][2]),
            last=float(klines[0][4]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][7]),
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol}: {e!s}")
        return None


# Adding hourly and fifteen-minute candle fetching functions


def fetch_binance_hourly_kline(symbol: Symbol, end_time: datetime) -> Candle | None:
    """Fetch open, close, high, low prices and volume from Binance for the specified hour.

    Args:
        symbol: Symbol object with binance_name property
        end_time: End time for the candle period (defaults to current hour)

    Returns:
        Candle object if successful, None otherwise

    """
    client = BinanceClient()

    # Start time is 1 hour before end time
    start_time = end_time - timedelta(hours=1)

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch 1-hour Kline data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1HOUR,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=1,
        )

        if not klines:
            app_logger.error(f"No hourly Kline data found for {symbol.symbol_name}")
            return None

        return Candle(
            end_date=end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            source=SourceID.BINANCE.value,
            open=float(klines[0][1]),
            close=float(klines[0][4]),
            symbol=symbol.symbol_name,
            low=float(klines[0][3]),
            high=float(klines[0][2]),
            last=float(klines[0][4]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][7]),
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching hourly data for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol.symbol_name} hourly data: {e!s}")
        return None


def fetch_binance_fifteen_min_kline(symbol: Symbol, end_time: datetime) -> Candle | None:
    """Fetch 15-minute kline data from Binance for the specified symbol and time.

    Args:
        symbol: Symbol object with binance_name property
        end_time: End time for the candle period (defaults to current 15-minute interval)

    Returns:
        Candle object if successful, None otherwise

    """
    client = BinanceClient()

    if end_time.tzinfo is None:
        # Convert naive datetime to timezone-aware
        end_time = end_time.replace(tzinfo=UTC)

    # Start time is 15 minutes before end time
    start_time = end_time - timedelta(minutes=15)

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch 15-minute Kline data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_15MINUTE,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=1,
        )

        if not klines:
            app_logger.error(f"No 15-minute Kline data found for {symbol.symbol_name}")
            return None

        return Candle(
            end_date=end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            source=SourceID.BINANCE.value,
            open=float(klines[0][1]),
            close=float(klines[0][4]),
            symbol=symbol.symbol_name,
            low=float(klines[0][3]),
            high=float(klines[0][2]),
            last=float(klines[0][4]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][7]),
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching 15-minute data for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol.symbol_name} 15-minute data: {e!s}")
        return None


def fetch_binance_fifteen_min_klines_batch(
    symbol: Symbol,
    start_time: datetime,
    end_time: datetime,
) -> list[Candle]:
    """Fetch multiple 15-minute klines from Binance in a single API call.

    This function is optimized to fetch up to 1000 candles in one request,
    significantly reducing API overhead compared to individual fetches.

    Args:
        symbol: Symbol object with binance_name property
        start_time: Start time for the candle range
        end_time: End time for the candle range

    Returns:
        List of Candle objects, empty list if fetch fails

    """
    max_candles_per_request = 1000
    client = BinanceClient()

    # Ensure timezone-aware datetimes
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    # Round to nearest 15 minutes
    start_minutes = (start_time.minute // 15) * 15
    start_time = start_time.replace(minute=start_minutes, second=0, microsecond=0)

    end_minutes = (end_time.minute // 15) * 15
    end_time = end_time.replace(minute=end_minutes, second=0, microsecond=0)

    # Calculate expected number of candles
    time_diff = end_time - start_time
    expected_candles = int(time_diff.total_seconds() / (15 * 60)) + 1

    # Binance API limit is 1000 candles per request
    if expected_candles > max_candles_per_request:
        app_logger.warning(
            f"Requested {expected_candles} candles for {symbol.symbol_name}, "
            f"limiting to {max_candles_per_request} (max per API call)",
        )
        expected_candles = max_candles_per_request

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch 15-minute Kline data in batch
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_15MINUTE,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=expected_candles,
        )

        if not klines:
            app_logger.error(f"No 15-minute Kline data found for {symbol.symbol_name}")
            return []

        # Convert each kline to Candle object
        candles = []
        for kline in klines:
            # kline[0] is the open time in milliseconds
            candle_end_time = datetime.fromtimestamp(
                kline[0] / 1000,
                tz=UTC,
            ) + timedelta(minutes=15)

            candles.append(
                Candle(
                    end_date=candle_end_time.isoformat(),
                    source=SourceID.BINANCE.value,
                    open=float(kline[1]),
                    close=float(kline[4]),
                    symbol=symbol.symbol_name,
                    low=float(kline[3]),
                    high=float(kline[2]),
                    last=float(kline[4]),
                    volume=float(kline[5]),
                    volume_quote=float(kline[7]),
                ),
            )

        app_logger.info(
            f"✓ Fetched {len(candles)} 15-minute candles for {symbol.symbol_name} "
            f"in single API call (requested {expected_candles})",
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error batch fetching 15-minute data for {symbol.symbol_name}: {e.message}",
        )
        return []
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error batch fetching {symbol.symbol_name} 15-minute data: {e!s}",
        )
        return []
    else:
        return candles


def fetch_binance_hourly_klines_batch(
    symbol: Symbol,
    start_time: datetime,
    end_time: datetime,
) -> list[Candle]:
    """Fetch multiple hourly klines from Binance in a single API call.

    This function is optimized to fetch up to 1000 candles in one request,
    significantly reducing API overhead compared to individual fetches.

    Args:
        symbol: Symbol object with binance_name property
        start_time: Start time for the candle range
        end_time: End time for the candle range

    Returns:
        List of Candle objects, empty list if fetch fails

    """
    max_candles_per_request = 1000
    client = BinanceClient()

    # Ensure timezone-aware datetimes
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    # Round to nearest hour
    start_time = start_time.replace(minute=0, second=0, microsecond=0)
    end_time = end_time.replace(minute=0, second=0, microsecond=0)

    # Calculate expected number of candles
    time_diff = end_time - start_time
    expected_candles = int(time_diff.total_seconds() / 3600) + 1  # 3600 seconds = 1 hour

    # Binance API limit is 1000 candles per request
    if expected_candles > max_candles_per_request:
        app_logger.warning(
            f"Requested {expected_candles} hourly candles for {symbol.symbol_name}, "
            f"limiting to {max_candles_per_request} (max per API call)",
        )
        expected_candles = max_candles_per_request

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch hourly Kline data in batch
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1HOUR,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=expected_candles,
        )

        if not klines:
            app_logger.error(f"No hourly Kline data found for {symbol.symbol_name}")
            return []

        # Convert each kline to Candle object
        candles = []
        for kline in klines:
            # kline[0] is the open time in milliseconds
            candle_end_time = datetime.fromtimestamp(
                kline[0] / 1000,
                tz=UTC,
            ) + timedelta(hours=1)

            candles.append(
                Candle(
                    end_date=candle_end_time.isoformat(),
                    source=SourceID.BINANCE.value,
                    open=float(kline[1]),
                    close=float(kline[4]),
                    symbol=symbol.symbol_name,
                    low=float(kline[3]),
                    high=float(kline[2]),
                    last=float(kline[4]),
                    volume=float(kline[5]),
                    volume_quote=float(kline[7]),
                ),
            )

        app_logger.info(
            f"✓ Fetched {len(candles)} hourly candles for {symbol.symbol_name} "
            f"in single API call (requested {expected_candles})",
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error batch fetching hourly data for {symbol.symbol_name}: {e.message}",
        )
        return []
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error batch fetching {symbol.symbol_name} hourly data: {e!s}",
        )
        return []
    else:
        return candles


def fetch_binance_daily_klines_batch(
    symbol: Symbol,
    start_date: date,
    end_date: date,
) -> list[Candle]:
    """Fetch multiple daily klines from Binance in a single API call.

    This function is optimized to fetch up to 1000 candles in one request,
    significantly reducing API overhead compared to individual fetches.

    Args:
        symbol: Symbol object with binance_name property
        start_date: Start date for the candle range
        end_date: End date for the candle range

    Returns:
        List of Candle objects, empty list if fetch fails

    """
    max_candles_per_request = 1000
    client = BinanceClient()

    # Convert dates to datetime objects for timestamp calculation
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

    # Calculate expected number of candles
    days_diff = (end_date - start_date).days + 1
    expected_candles = days_diff

    # Binance API limit is 1000 candles per request
    if expected_candles > max_candles_per_request:
        app_logger.warning(
            f"Requested {expected_candles} daily candles for {symbol.symbol_name}, "
            f"limiting to {max_candles_per_request} (max per API call)",
        )
        expected_candles = max_candles_per_request
        # Adjust end_datetime to match the limit
        end_datetime = start_datetime + timedelta(days=max_candles_per_request - 1)

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_datetime.timestamp() * 1000)
    end_timestamp_ms = int(end_datetime.timestamp() * 1000)

    try:
        # Fetch daily Kline data in batch
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1DAY,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=expected_candles,
        )

        if not klines:
            app_logger.error(f"No daily Kline data found for {symbol.symbol_name}")
            return []

        # Convert each kline to Candle object
        candles = []
        for kline in klines:
            # kline[0] is the open time in milliseconds
            candle_date = datetime.fromtimestamp(
                kline[0] / 1000,
                tz=UTC,
            ).date()

            # Use end of day for end_date (consistent with individual fetch)
            candle_end_datetime = datetime.combine(
                candle_date,
                datetime.max.time(),
                tzinfo=UTC,
            )

            candles.append(
                Candle(
                    end_date=candle_end_datetime.isoformat(),
                    source=SourceID.BINANCE.value,
                    open=float(kline[1]),
                    close=float(kline[4]),
                    symbol=symbol.symbol_name,
                    low=float(kline[3]),
                    high=float(kline[2]),
                    last=float(kline[4]),
                    volume=float(kline[5]),
                    volume_quote=float(kline[7]),
                ),
            )

        app_logger.info(
            f"✓ Fetched {len(candles)} daily candles for {symbol.symbol_name} "
            f"in single API call (requested {expected_candles})",
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error batch fetching daily data for {symbol.symbol_name}: {e.message}",
        )
        return []
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error batch fetching {symbol.symbol_name} daily data: {e!s}",
        )
        return []
    else:
        return candles


if __name__ == "__main__":
    symbol = Symbol(
        symbol_id=1,
        symbol_name="BTC",
        full_name="Bitcoin",
        source_id=SourceID.BINANCE,
        coingecko_name="bitcoin",
    )

    # Fetch open and close prices for the last full day
    response = fetch_binance_daily_kline(symbol, datetime.now(UTC) - timedelta(days=1))
    if response is not None:
        pass
    else:
        pass
