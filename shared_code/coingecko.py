from pycoingecko import CoinGeckoAPI

from infra.telegram_logging_handler import app_logger
from shared_code.common_price import TickerPrice
from source_repository import SourceID, Symbol


def fetch_coingecko_price(symbol: Symbol) -> TickerPrice:
    """Fetch current price from CoinGecko API and return as TickerPrice object"""
    try:
        cg = CoinGeckoAPI()
        price_data = cg.get_price(ids=symbol.full_name, vs_currencies="usd")
        return TickerPrice(
            source=SourceID.COINGECKO,
            symbol=symbol.symbol_name,
            low=price_data[symbol.full_name]["usd"],
            high=price_data[symbol.full_name]["usd"],
            last=price_data[symbol.full_name]["usd"],
            volume=0,
            volume_quote=0,
        )
    except Exception as e:
        app_logger.error(f"Error fetching price from CoinGecko: {e}")
        raise
