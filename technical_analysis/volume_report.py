from technical_analysis.volume_repository import save_volume_results
from typing import List
from prettytable import PrettyTable
import requests
from source_repository import Symbol

def fetch_volume_report(symbols: List[Symbol], conn) -> PrettyTable:
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
                'symbol_id': crypto.symbol_id,
                'name': crypto.full_name,
                'binance': binance_volume,
                'kucoin': kucoin_volume,
                'total': total_volume
            })
        else:
            missing_symbols.append(crypto.symbol_name)

    # Sort results by total volume descending
    sorted_results = sorted(results, key=lambda x: x['total'], reverse=True)
    
    # Create and format PrettyTable
    table = PrettyTable()
    table.field_names = ["Symbol", "Volume (USD)"]
    table.align["Symbol"] = "l"  # Left align
    table.align["Volume (USD)"] = "r"  # Right align
    
    for result in sorted_results:
        volume = f"${result['total']:,.2f}"
        table.add_row([result['symbol'], volume])
    
    save_volume_results(conn, sorted_results)
    
    return table        
        
if __name__ == "__main__":
    from source_repository import Symbol, SourceID
    from infra.sql_connection import connect_to_sql
    from dotenv import load_dotenv
    load_dotenv()
    conn = connect_to_sql()
    symbols = [
        Symbol(symbol_id=1, symbol_name="BTC", full_name="Bitcoin", source_id=SourceID.BINANCE),
        Symbol(symbol_id=2, symbol_name="ETH", full_name="Ethereum", source_id=SourceID.BINANCE)
    ]

    table = fetch_volume_report(symbols, conn)
    print(table)