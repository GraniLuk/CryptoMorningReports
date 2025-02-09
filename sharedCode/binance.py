from datetime import date, datetime, timedelta, timezone

import pandas as pd
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import Candle, TickerPrice
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


def fetch_binance_daily_kline(symbol: Symbol, end_date: date = date.today()) -> Candle:
    """Fetch open and close prices from Binance for the last full day."""
    client = BinanceClient()

    # Get yesterday's date
    end_date_timestamp = datetime.combine(end_date, datetime.min.time()).timestamp()
    start_date_timestamp = datetime.combine(
        end_date - timedelta(days=1), datetime.min.time()
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
            end_date=end_date,
            source=SourceID.BINANCE,
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
    response = fetch_binance_daily_kline(
        symbol, datetime.now(timezone.utc) - timedelta(days=1)
    )
    if response is not None:
        print(f"Yesterday price: {response}")
    else:
        print("No data found")
