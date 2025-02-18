import requests
import datetime
import os
from decimal import Decimal

# API Configuration (Set these as environment variables)
COINGECKO_API = "https://api.coingecko.com/api/v3"
BASESCAN_API = "https://api.basescan.org/api"
CRYPTOPANIC_API = "https://cryptopanic.com/api/v1/posts/"
VIRTUAL_CONTRACT = "0x1dD7950c266fB1be96180a8FDb0591F70200E018"  # Example contract
BURN_ADDRESS = "0x000000000000000000000000000000000000dead"

def get_coingecko_data():
    """Fetch market data from CoinGecko"""
    try:
        response = requests.get(
            f"{COINGECKO_API}/coins/virtual-protocol",
            params={'localization': 'false', 'tickers': 'false'}
        )
        data = response.json()
        
        return {
            'price': data['market_data']['current_price']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
            'volume': data['market_data']['total_volume']['usd'],
            'circulating_supply': data['market_data']['circulating_supply']
        }
    except Exception as e:
        return {"error": f"CoinGecko API Error: {str(e)}"}

def get_burn_metrics(api_key):
    """Fetch burn metrics from BaseScan"""
    try:
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': BURN_ADDRESS,
            'startblock': 0,
            'endblock': 99999999,
            'apikey': api_key
        }
        
        response = requests.get(BASESCAN_API, params=params)
        data = response.json()
        
        today = datetime.date.today()
        daily_burn = 0
        
        for tx in data.get('result', []):
            tx_date = datetime.datetime.fromtimestamp(int(tx['timeStamp'])).date()
            if tx_date == today:
                daily_burn += Decimal(tx['value']) / Decimal(10**18)  # Convert from wei
                
        return {'daily_burn': float(daily_burn)}
    except Exception as e:
        return {"error": f"BaseScan API Error: {str(e)}"}

def get_regulatory_news(api_key):
    """Fetch regulatory news from CryptoPanic"""
    try:
        params = {
            'auth_token': api_key,
            'currencies': 'VIRTUAL',
            'filter': 'rising',
            'kind': 'news'
        }
        
        response = requests.get(CRYPTOPANIC_API, params=params)
        data = response.json()
        
        return [{
            'title': post['title'],
            'url': post['url'],
            'created_at': post['created_at']
        } for post in data.get('results', [])]
    except Exception as e:
        return {"error": str(e)}

def main():
    # Get API keys from environment
    basescan_key = os.getenv('BASESCAN_API_KEY')
    cryptopanic_key = os.getenv('CRYPTOPANIC_API_KEY')
    
    print("🔄 Fetching $VIRTUAL Ecosystem Metrics...\n")
    
    # Market Data
    market_data = get_coingecko_data()
    if 'error' in market_data:
        print(f"❌ Market Data Error: {market_data['error']}")
    else:
        print("💰 Market Data:")
        print(f"• Price: ${market_data['price']:.4f}")
        print(f"• Market Cap: ${market_data['market_cap']:,.0f}")
        print(f"• 24h Volume: ${market_data['volume']:,.0f}")
        print(f"• Circulating Supply: {market_data['circulating_supply']:,.0f} VIRTUAL\n")
    
    # Burn Metrics
    if basescan_key:
        burn_data = get_burn_metrics(basescan_key)
        if 'error' in burn_data:
            print(f"❌ Burn Metrics Error: {burn_data['error']}")
        else:
            print("🔥 Burn Metrics:")
            print(f"• Today's Burn: {burn_data['daily_burn']:,.0f} VIRTUAL")
            if 'circulating_supply' in market_data:
                burn_rate = (burn_data['daily_burn'] / market_data['circulating_supply']) * 100
                print(f"• Burn Rate: {burn_rate:.4f}%\n")
    else:
        print("⚠️ BaseScan API key missing (burn metrics skipped)\n")
    
    # Regulatory News
    if cryptopanic_key:
        news = get_regulatory_news(cryptopanic_key)
        if isinstance(news, list):
            print("📰 Latest Regulatory News:")
            for item in news[:3]:  # Show top 3
                print(f"• {item['title']}")
                print(f"  {item['url']}")
        else:
            print(f"❌ News Error: {news.get('error', 'Unknown error')}")
    else:
        print("⚠️ CryptoPanic API key missing (news skipped)")

if __name__ == "__main__":
    main()
