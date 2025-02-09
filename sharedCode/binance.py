from datetime import datetime, timedelta, timezone

import pandas as pd
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import TickerPrice
from source_repository import SourceID, Symbol


def fetch_binance_price(symbol: Symbol) -> TickerPrice:
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
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return None


def fetch_close_prices_from_Binance(
    symbol: str, lookback_days: int = 14
) -> pd.DataFrame:
    client = BinanceClient()

    try:
        start_time = datetime.now() - timedelta(days=lookback_days)

        klines = client.get_historical_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            start_str=start_time.strftime("%d %b %Y"),
            limit=lookback_days,
        )

        # Create DataFrame with numeric types
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

        # Convert price columns to float
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        return df

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching data for {symbol}: {e.message}")
        return pd.DataFrame()
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return pd.DataFrame()


def fetch_daily_kline(symbol: Symbol, day: datetime = datetime.now(timezone.utc)):
    """Fetch open and close prices from Binance for the last full day."""
    client = BinanceClient()

    # Get yesterday's date
    end_time = day.replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)

    try:
        # Fetch 1-day Kline (candlestick) data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1DAY,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
        )

        if not klines:
            app_logger.error(f"No Kline data found for {symbol}")
            return None

        open_price = float(klines[0][1])  # Open price
        high_price = float(klines[0][2])  # High price
        low_price = float(klines[0][3])  # Low price
        close_price = float(klines[0][4])  # Close price
        volume = float(klines[0][5])  # Volume
        quoute_asset_volume = float(klines[0][7])  # Quote asset volume

        return (
            open_price,
            close_price,
            high_price,
            low_price,
            volume,
            quoute_asset_volume,
        )
    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return None


if __name__ == "__main__":
    symbol = Symbol(
        symbol_id=1,
        symbol_name="BTC",
        full_name="Bitcoin",
        source_id=SourceID.BINANCE,
    )

    # # Fetch current price
    # price = fetch_binance_price(symbol)
    # if price is not None:
    #     print(price)

    # # Fetch close prices
    # df = fetch_close_prices_from_Binance(symbol.binance_name)
    # if not df.empty:
    #     print(df)
    # else:
    #     print("No data found")

    # Fetch open and close prices for the last full day
    response = fetch_daily_kline(symbol, datetime.now(timezone.utc) - timedelta(days=1))
    if response is not None:
        print(f"Yesterday price: {response}")
    else:
        print("No data found")
