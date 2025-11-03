"""Telegram message sending functions.

This module handles all Telegram API communication including sending
text messages, documents, and managing message delivery with retries.
"""

import time
from pathlib import Path

import requests

from infra.telegram_logging_handler import app_logger

from .constants import TELEGRAM_MAX_DOCUMENT_SIZE, TELEGRAM_MAX_MESSAGE_LENGTH
from .text_processing import enforce_markdown_v2, sanitize_html, smart_split


async def send_telegram_message(
    *,
    enabled: bool,
    token: str | None,
    chat_id: str | None,
    message: str | None,
    parse_mode: str | None = "HTML",
    disable_web_page_preview: bool = False,
    disable_notification: bool = False,
    protect_content: bool = False,
) -> bool | None:
    """Send a message to a Telegram chat."""
    if not enabled:
        app_logger.info("Telegram notifications are disabled")
        return None

    if message is None or len(message) == 0:
        app_logger.error("Empty message, skipping telegram notification")
        return None

    original_parse_mode = parse_mode

    if parse_mode == "MarkdownV2":
        message = enforce_markdown_v2(message)
    elif parse_mode == "HTML":
        message = sanitize_html(message)
    elif parse_mode not in (None, ""):
        app_logger.warning(
            "Unsupported parse_mode '%s' provided. Falling back to raw text (no parse mode).",
            parse_mode,
        )
        parse_mode = None

    try:
        # Split message into chunks at paragraph boundaries where possible
        chunks = smart_split(message, TELEGRAM_MAX_MESSAGE_LENGTH, parse_mode)

        for chunk in chunks:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload: dict[str, str | bool | None] = {
                "chat_id": chat_id,
                "text": chunk,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if disable_web_page_preview:
                payload["disable_web_page_preview"] = True
            if disable_notification:
                payload["disable_notification"] = True
            if protect_content:
                payload["protect_content"] = True

            response = requests.post(url, json=payload, timeout=30)

            if not response.ok:
                # Gather diagnostics
                try:
                    err_json = response.json()
                except (ValueError, TypeError, KeyError):
                    err_json = {"raw_text": (response.text[:500] if response.text else None)}
                app_logger.error(
                    "Telegram API error (status=%s, parse_mode=%s "
                    "original_parse_mode=%s, chunk_len=%d): %s",
                    response.status_code,
                    parse_mode,
                    original_parse_mode,
                    len(chunk),
                    err_json,
                )
                response.raise_for_status()
            time.sleep(0.5)

    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        # Avoid logging the entire large message to keep logs clean / protect data
        message_truncate_threshold = 600
        snippet = (
            (message[:500] + "...<truncated>")
            if len(message) > message_truncate_threshold
            else message
        )
        app_logger.exception(
            "Failed to send telegram message | snippet: %s | error: %s",
            snippet,
            e,
        )
        return False

    else:
        return True


async def try_send_report_with_html_or_markdown(
    telegram_enabled,
    telegram_token,
    telegram_chat_id,
    message,
):
    """Send a report message trying HTML first, then falling back to MarkdownV2."""
    # Try HTML first
    success = await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=message,
        parse_mode="HTML",
    )

    # If HTML failed, try MarkdownV2
    if not success:
        success = await send_telegram_message(
            enabled=telegram_enabled,
            token=telegram_token,
            chat_id=telegram_chat_id,
            message=message,
            parse_mode="MarkdownV2",
        )

    return success


def _validate_telegram_params(*, enabled: bool, token: str, chat_id: str) -> bool:
    """Validate basic Telegram parameters."""
    if not enabled:
        app_logger.info("Telegram notifications are disabled")
        return False

    if not token or not chat_id:
        app_logger.error("Missing token or chat_id for send_telegram_document")
        return False

    return True


def _check_file_size(size: int, filename: str) -> bool:
    """Check if file size exceeds Telegram limits."""
    if size > TELEGRAM_MAX_DOCUMENT_SIZE:
        app_logger.error(
            "File %s exceeds Telegram max size (%d > %d)",
            filename,
            size,
            TELEGRAM_MAX_DOCUMENT_SIZE,
        )
        return False
    return True


def _send_document_request(token: str, files: dict, data: dict, filename: str) -> bool:
    """Send document request to Telegram API."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    response = requests.post(url, data=data, files=files, timeout=30)
    if not response.ok:
        try:
            err_json = response.json()
        except (ValueError, TypeError, KeyError):
            err_json = {"raw": response.text[:300]}
        app_logger.error("Failed to send document (status=%s): %s", response.status_code, err_json)
        return False
    app_logger.info("Document %s successfully sent to Telegram", filename)
    return True


async def send_telegram_document(
    *,
    enabled: bool,
    token: str,
    chat_id: str,
    file_bytes: bytes | None = None,
    filename: str = "report.txt",
    caption: str | None = None,
    parse_mode: str | None = None,
    local_path: str | None = None,
) -> bool:
    """Send a document (e.g. markdown report) to Telegram.

    Either provide file_bytes OR a local_path. If both are provided local_path takes precedence.
    Returns True on success, False otherwise.
    """
    if not _validate_telegram_params(enabled=enabled, token=token, chat_id=chat_id):
        return False

    try:
        if local_path:
            if not Path(local_path).exists():
                app_logger.error("Local file does not exist: %s", local_path)
                return False
            file_size = Path(local_path).stat().st_size
            if not _check_file_size(file_size, local_path):
                return False

            # Use context manager for file handling
            with Path(local_path).open("rb") as file_handle:
                files = {
                    "document": (filename, file_handle, "application/octet-stream"),
                }
                data = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption[:1024]  # Telegram caption limit
                if parse_mode:
                    data["parse_mode"] = parse_mode

                return _send_document_request(token, files, data, filename)
        else:
            if file_bytes is None:
                app_logger.error("Neither file_bytes nor local_path provided for document")
                return False
            if not _check_file_size(len(file_bytes), filename):
                return False

            # Handle bytes directly (no file to close)
            files = {
                "document": (filename, file_bytes, "application/octet-stream"),
            }
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption[:1024]  # Telegram caption limit
            if parse_mode:
                data["parse_mode"] = parse_mode

            return _send_document_request(token, files, data, filename)
    except (OSError, ValueError, TypeError, KeyError, requests.RequestException) as e:
        app_logger.exception("Exception while sending document: %s", e)
        return False

