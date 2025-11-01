"""Test script for SOPR API endpoints."""

import logging
from datetime import UTC, datetime, timedelta

import requests


yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

# Test base SOPR endpoint
try:
    response = requests.get(
        "https://bitcoin-data.com/v1/sopr", params={"day": yesterday}, timeout=30
    )
    if response.text:
        try:
            data = response.json()
        except Exception:
            logging.exception("Failed to parse JSON response from SOPR API")
except Exception:
    logging.exception("Failed to test SOPR API with day parameter")

# Try without parameters
try:
    response = requests.get("https://bitcoin-data.com/v1/sopr", timeout=30)
except Exception:
    logging.exception("Failed to test SOPR API without parameters")

# Try alternative date format
for param_name in ["date", "timestamp", "from", "start"]:
    try:
        response = requests.get(
            "https://bitcoin-data.com/v1/sopr", params={param_name: yesterday}, timeout=30
        )
    except Exception:
        logging.exception("Failed to test SOPR API with %s parameter", param_name)
