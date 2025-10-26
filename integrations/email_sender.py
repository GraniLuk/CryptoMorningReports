import asyncio
import os
import smtplib
import ssl
from collections.abc import Iterable, Sequence
from email.message import EmailMessage

from infra.telegram_logging_handler import app_logger


def _normalise_recipients(recipients: Iterable[str]) -> list[str]:
    return [addr.strip() for addr in recipients if addr and addr.strip()]


def _send_email_sync(
    username: str,
    password: str,
    subject: str,
    body: str,
    recipients: Sequence[str],
    attachment_bytes: bytes,
    attachment_filename: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = username
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    message.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="epub+zip",
        filename=attachment_filename,
    )

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(username, password)
        server.send_message(message)


async def send_email_with_epub_attachment(
    subject: str,
    body: str,
    attachment_bytes: bytes,
    attachment_filename: str,
    recipients: Iterable[str],
) -> bool:
    username = os.environ.get("GMAIL_USERNAME")
    password = os.environ.get("GMAIL_PASSWORD")

    recipient_list = _normalise_recipients(recipients)

    if not username or not password:
        app_logger.error("Missing Gmail credentials; set GMAIL_USERNAME and GMAIL_PASSWORD.")
        return False

    if not recipient_list:
        app_logger.error("No valid recipients provided for email dispatch.")
        return False

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            _send_email_sync,
            username,
            password,
            subject,
            body,
            recipient_list,
            attachment_bytes,
            attachment_filename,
        )
        app_logger.info("Sent EPUB report email to %s", ", ".join(recipient_list))
        return True
    except smtplib.SMTPAuthenticationError:
        app_logger.exception("SMTP authentication failed for Gmail account %s", username)
    except Exception:
        app_logger.exception("Failed to send EPUB report email via Gmail")
    return False
