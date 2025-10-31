"""Test script for SOPR API endpoints."""

import contextlib
from datetime import UTC, datetime, timedelta

import requests


yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

# Test base SOPR endpoint
try:
    response = requests.get("https://bitcoin-data.com/v1/sopr", params={"day": yesterday})
    if response.text:
        with contextlib.suppress(Exception):
            data = response.json()
except Exception:
    pass

# Try without parameters
with contextlib.suppress(Exception):
    response = requests.get("https://bitcoin-data.com/v1/sopr")

# Try alternative date format
for param_name in ["date", "timestamp", "from", "start"]:
    with contextlib.suppress(Exception):
        response = requests.get("https://bitcoin-data.com/v1/sopr", params={param_name: yesterday})
