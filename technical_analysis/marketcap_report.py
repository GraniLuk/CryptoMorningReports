from typing import List
from prettytable import PrettyTable
import requests
from source_repository import Symbol
from technical_analysis.marketcap_repository import save_marketcap_results

def fetch_marketcap_report(symbols: List[Symbol], conn) -> PrettyTable:
    results = []
    missing_symbols = []

    # Get all market caps in one API call
    symbol_ids = ','.join([s.coingecko_name.lower() for s in symbols])
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'ids': symbol_ids,
        'order': 'market_cap_desc',
        'per_page': 250,
        'page': 1,
        'sparkline': 'false'
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            
            # Create lookup dictionary
            market_caps = {coin['id']: coin['market_cap'] for coin in data}
            
            for crypto in symbols:
                market_cap = market_caps.get(crypto.coingecko_name.lower(), 0)
                
                if market_cap > 0:
                    results.append({
                        'symbol': crypto.symbol_name,
                        'symbol_id': crypto.symbol_id,
                        'name': crypto.full_name,
                        'market_cap': market_cap
                    })
                else:
                    missing_symbols.append(crypto.symbol_name)                       
    except Exception as e:
        print(f"Error fetching market caps: {e}")

    # Sort results by market cap descending
    sorted_results = sorted(results, key=lambda x: x['market_cap'], reverse=True)
    
    # Create and format PrettyTable
    table = PrettyTable()
    table.field_names = ["Symbol", "Market Cap (USD)"]
    table.align["Symbol"] = "l"
    table.align["Market Cap (USD)"] = "r"
    
    for result in sorted_results:
        market_cap = f"${result['market_cap']:,.2f}"
        table.add_row([result['symbol'], market_cap])
    
    # Save results (assuming similar structure as volume_repository)
    save_marketcap_results(conn, sorted_results)
    
    return table

if __name__ == "__main__":
    from source_repository import Symbol, fetch_symbols
    from infra.sql_connection import connect_to_sql
    from dotenv import load_dotenv
    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    table = fetch_marketcap_report(symbols, conn)
    print(table)