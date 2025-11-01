"""BSC blockchain activity monitoring for STEPN contracts."""

from datetime import UTC, datetime, timedelta

import requests

from infra.telegram_logging_handler import app_logger


class BSCAPIError(Exception):
    """Exception raised for BSCScan API errors."""


def get_yesterday_transaction_count(contract_address, api_key):
    """Get the transaction count for a BSC contract address from yesterday."""

    # Get block numbers for time range
    def get_block_number(timestamp):
        response = requests.get(
            "https://api.bscscan.com/api",
            params={
                "module": "block",
                "action": "getblocknobytime",
                "timestamp": timestamp,
                "closest": "before",
                "apikey": api_key,
            },
            timeout=30,
        ).json()
        if response["status"] != "1":
            msg = f"Block API Error: {response['message']}"
            raise BSCAPIError(msg)
        return int(response["result"])

    # Calculate yesterday's timestamps
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)
    start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)

    # Get corresponding block numbers
    start_block = get_block_number(int(start_of_yesterday.timestamp()))
    end_block = get_block_number(int(end_of_yesterday.timestamp()))

    # API call with correct block numbers
    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract_address,
        "startblock": start_block,
        "endblock": end_block,
        "sort": "desc",
        "apikey": api_key,
    }

    # Define the API endpoint and parameters
    url = "https://api.bscscan.com/api"

    # Make the API request
    response = requests.get(url, params=params, timeout=30)
    data = response.json()

    # Check if the response is successful
    if data["status"] == "1":
        transactions = data["result"]
        return len(transactions)
    msg = f"API Error: {data['message']}"
    raise BSCAPIError(msg)


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    # Example usage
    api_key = os.environ["BSC_SCAN_API_KEY"]
    # Usage
    stepn_contract_address = "0x3019BF2a2eF8040C242C9a4c5c4BD4C81678b2A1"

    try:
        count = get_yesterday_transaction_count(stepn_contract_address, api_key)
        app_logger.info(f"Yesterday's transaction count: {count}")
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        app_logger.error(f"An error occurred: {e}", exc_info=True)
