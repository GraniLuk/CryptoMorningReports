from datetime import UTC, datetime, timedelta

import requests


yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Testing SOPR API for date: {yesterday}")
print("-" * 50)

# Test base SOPR endpoint
print("\n1. Testing /v1/sopr endpoint:")
try:
    response = requests.get("https://bitcoin-data.com/v1/sopr", params={"day": yesterday})
    print(f"   Status Code: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('Content-Type')}")
    print(f"   Response Length: {len(response.text)} chars")
    print(f"   Response Text: {response.text[:200]}")
    if response.text:
        try:
            data = response.json()
            print(f"   JSON Data: {data}")
        except Exception as e:
            print(f"   JSON Parse Error: {e}")
except Exception as e:
    print(f"   Request Error: {e}")

# Try without parameters
print("\n2. Testing /v1/sopr without date parameter:")
try:
    response = requests.get("https://bitcoin-data.com/v1/sopr")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Text: {response.text[:200]}")
except Exception as e:
    print(f"   Request Error: {e}")

# Try alternative date format
print("\n3. Testing with different date parameter names:")
for param_name in ["date", "timestamp", "from", "start"]:
    try:
        response = requests.get("https://bitcoin-data.com/v1/sopr", params={param_name: yesterday})
        print(
            f'   Param "{param_name}": Status {response.status_code}, Length {len(response.text)}'
        )
    except Exception as e:
        print(f'   Param "{param_name}": Error {e}')
