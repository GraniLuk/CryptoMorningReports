import json
import os

import aiohttp

from infra.telegram_logging_handler import app_logger


async def upload_to_onedrive(filename: str, content: str, folder_path: str):
    """
    Sends content to an Azure Logic App to be saved in OneDrive.

    Args:
        filename (str): The name for the file.
        content (str): The content to be saved in the file.
        folder_path (str, optional): The target folder path in OneDrive (e.g., "/Documents/Reports").
            If not provided, files will be saved in the default location.
    """
    logic_app_url = os.environ.get("ONEDRIVE_LOGIC_APP_URL")
    logger = app_logger

    if not logic_app_url:
        logger.error(
            "ONEDRIVE_LOGIC_APP_URL environment variable not set. Cannot upload to OneDrive."
        )
        return False

    # Set the base folder path for crypto reports
    base_folder = "/Brain/Personal/Projects/CryptoMorningReports/Analysis"

    # If a specific folder path is provided, append it to the base folder
    if folder_path:
        full_path = f"{base_folder}/{folder_path}"
    else:
        full_path = f"{base_folder}"

    payload = {
        "filename": filename,
        "content": content,
        "folderPath": full_path,
    }

    headers = {"Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                logic_app_url, headers=headers, data=json.dumps(payload)
            ) as response:
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                logger.info(
                    f"Successfully uploaded '{filename}' to OneDrive via Logic App. Status: {response.status}"
                )
                return True
    except aiohttp.ClientError as e:
        logger.error(f"Error uploading '{filename}' to OneDrive via Logic App: {e}")
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during OneDrive upload for '{filename}': {e}"
        )
        return False
