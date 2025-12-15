"""Telegram logging handler for sending log messages via Telegram."""

import logging
import os
import traceback
from typing import ClassVar

import requests


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
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
        # Format the message with better structure for Telegram
        message = self._format_telegram_message(record)
        self.send_telegram_message(message)

    def _format_telegram_message(self, record):
        """Format log record for better readability in Telegram."""
        # Emoji mapping for log levels
        emoji_map = {
            "WARNING": "⚠️",
            "ERROR": "🔴",
            "CRITICAL": "🚨",
        }

        emoji = emoji_map.get(record.levelname, "[i]")

        # Format time safely
        if self.formatter:
            time_str = self.formatter.formatTime(record)
        else:
            time_str = logging.Formatter().formatTime(record)

        # Build the message with HTML formatting
        lines = [
            f"{emoji} <b>{record.levelname}</b>",
            f"<b>Module:</b> {record.filename}",
            f"<b>Time:</b> {time_str}",
        ]

        # Add the main message
        lines.append(f"\n<b>Message:</b>\n{record.getMessage()}")

        # Add exception info if present
        if record.exc_info:
            # Get exception type and message
            exc_type, exc_value, exc_tb = record.exc_info
            lines.append(f"\n<b>Exception:</b> {exc_type.__name__}: {exc_value}")

            # Add traceback (limit to last few frames to avoid message length issues)
            if exc_tb:
                tb_lines = traceback.format_tb(exc_tb)
                # Keep last 5 frames
                tb_text = "".join(tb_lines[-5:])
                lines.append(f"\n<b>Traceback (last 5 frames):</b>\n<pre>{tb_text}</pre>")

        return "\n".join(lines)

    def send_telegram_message(self, message):
        """Send a message via Telegram API."""
        telegram_max_message_length = 4096
        if message is None or len(message) == 0:
            return
        if len(message) > telegram_max_message_length:
            # Truncate with indicator
            message = message[: telegram_max_message_length - 50] + "\n\n... (message truncated)"
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
        except (requests.RequestException, OSError):  # noqa: S110
            # Silently fail to avoid logging loops
            pass


def setup_logger():
    """Set up the application logger with console and Telegram handlers."""
    logger = logging.getLogger("AppLogger")

    # Get log level from environment variable, default to INFO
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)  # Set the logger's level to the lowest level you want to capture

    # Formatter
    format_str = "%(asctime)s - %(name)s - %(filename)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(format_str)
    colored_formatter = ColoredFormatter(format_str)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(colored_formatter)
    logger.addHandler(console_handler)

    # Telegram Handler (WARNING and ERROR levels)
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
        # Changed from ERROR to WARNING to capture both WARNING and ERROR logs
        telegram_handler.setLevel(logging.WARNING)
        telegram_handler.setFormatter(formatter)
        logger.addHandler(telegram_handler)
        logger.info("Telegram handler initialized - will send WARNING and ERROR logs to Telegram")
    else:
        logger.warning(
            "Telegram handler not configured - missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID",
        )

    return logger


# Create the logger instance
app_logger = setup_logger()
