"""Telegram logging handler for sending log messages via Telegram."""

import logging
import os
from typing import ClassVar

import requests


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",   # Green
        "WARNING": "\033[33m", # Yellow
        "ERROR": "\033[31m",   # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET: ClassVar[str] = "\033[0m"

    def format(self, record):
        """Format the log record with color codes for the level name."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class TelegramHandler(logging.Handler):
    """Custom logging handler that sends log messages via Telegram."""

    def __init__(self, token, chat_id):
        """Initialize the Telegram handler with bot token and chat ID.

        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID to send messages to

        """
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def emit(self, record):
        """Emit a log record by sending it via Telegram."""
        log_entry = self.format(record)
        self.send_telegram_message(log_entry)

    def send_telegram_message(self, message):
        """Send a message via Telegram API."""
        telegram_max_message_length = 4096
        if message is None or len(message) == 0:
            return
        if len(message) > telegram_max_message_length:
            message = message[:telegram_max_message_length]
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": None}
        requests.post(url, json=payload, timeout=30)


def setup_logger():
    """Set up the application logger with console and Telegram handlers."""
    logger = logging.getLogger("AppLogger")
    
    # Get log level from environment variable, default to INFO
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)  # Set the logger's level to the lowest level you want to capture

    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    colored_formatter = ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(colored_formatter)
    logger.addHandler(console_handler)

    # Telegram Handler (ERROR level)
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    telegram_enabled = os.environ.get("TELEGRAM_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if not telegram_enabled:
        return logger

    if telegram_token and telegram_chat_id:
        telegram_handler = TelegramHandler(telegram_token, telegram_chat_id)
        telegram_handler.setLevel(logging.ERROR)
        telegram_handler.setFormatter(formatter)
        logger.addHandler(telegram_handler)
    else:
        pass

    return logger


# Create the logger instance
app_logger = setup_logger()
