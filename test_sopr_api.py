"""Test script for SOPR API endpoints."""

from datetime import UTC, datetime, timedelta

import requests

from infra.telegram_logging_handler import app_logger


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
            app_logger.exception("Failed to parse JSON response from SOPR API")
except Exception:
    app_logger.exception("Failed to test SOPR API with day parameter")

# Try without parameters
try:
    response = requests.get("https://bitcoin-data.com/v1/sopr", timeout=30)
except Exception:
    app_logger.exception("Failed to test SOPR API without parameters")

# Try alternative date format
for param_name in ["date", "timestamp", "from", "start"]:
    try:
        response = requests.get(
            "https://bitcoin-data.com/v1/sopr", params={param_name: yesterday}, timeout=30
        )
    except Exception:
        app_logger.exception("Failed to test SOPR API with %s parameter", param_name)
