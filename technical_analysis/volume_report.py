from typing import List
from prettytable import PrettyTable
import requests

from source_repository import Symbol

def get_volumes(symbols: List[Symbol], conn) -> PrettyTable:
    results = []
    missing_symbols = []

    for crypto in symbols:      
        # Get Binance volume
        binance_volume = 0.0
        try:
            binance_response = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": crypto.binance_name}
            )
            if binance_response.status_code == 200:
                binance_data = binance_response.json()
                binance_volume = float(binance_data.get('quoteVolume', 0))
        except Exception as e:
            pass

        # Get KuCoin volume
        kucoin_volume = 0.0
        try:
            kucoin_response = requests.get(
                "https://api.kucoin.com/api/v1/market/stats",
                params={"symbol": crypto.kucoin_name}
            )
            if kucoin_response.status_code == 200:
                kucoin_data = kucoin_response.json()
                kucoin_volume = float(kucoin_data.get('data', {}).get('volValue', 0))
        except Exception as e:
            pass

        total_volume = binance_volume + kucoin_volume
        
        if total_volume > 0:
            results.append({
                'symbol': crypto.symbol_name,
                'name': crypto.full_name,
                'binance': binance_volume,
                'kucoin': kucoin_volume,
                'total': total_volume
            })
        else:
            missing_symbols.append(crypto.symbol_name)

    # Sort results by total volume descending
    sorted_results = sorted(results, key=lambda x: x['total'], reverse=True)
    
    return sorted_results, missing_symbols

def print_combined_volumes(results, missing):
    print("Combined 24h Trading Volume (USD)")
    print("----------------------------------")
    print(f"{'Symbol':<8} {'Name':<15} {'Binance':<15} {'KuCoin':<15} {'Total':<15}")
    for item in results:
        print(f"{item['symbol']:<8} {item['name']:<15} "
              f"${item['binance']:>12,.2f}  "
              f"${item['kucoin']:>12,.2f}  "
              f"${item['total']:>12,.2f}")
    
    if missing:
        print("\nSymbols not found on either exchange:")
        print(", ".join(missing))
        
        

results, missing = get_volumes(user_crypto_list)
print_combined_volumes(results, missing)