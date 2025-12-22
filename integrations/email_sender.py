"""Email sending functionality for report distribution."""

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
    """Send an email with an EPUB attachment via Gmail SMTP."""
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
    except smtplib.SMTPAuthenticationError:
        app_logger.exception("SMTP authentication failed for Gmail account %s", username)
    except (OSError, ValueError, TypeError, ConnectionError, smtplib.SMTPException):
        app_logger.exception("Failed to send EPUB report email via Gmail")
    else:
        app_logger.info("Sent EPUB report email to %s", ", ".join(recipient_list))
        return True
    return False


async def send_epub_report_via_email(
    epub_bytes: bytes,
    epub_filename: str,
    today_date: str,
    run_id: str,
) -> None:
    """Send EPUB analysis report via email to configured recipients.

    Args:
        epub_bytes: EPUB file content as bytes
        epub_filename: Name for the EPUB attachment
        today_date: Current date string
        run_id: Run identifier (AM/PM)
    """
    recipients_env = os.environ.get("DAILY_REPORT_EMAIL_RECIPIENTS", "")
    recipients = [addr.strip() for addr in recipients_env.split(",") if addr.strip()]

    if not recipients:
        app_logger.info(
            "No recipients configured in DAILY_REPORT_EMAIL_RECIPIENTS; skipping email dispatch.",
        )
        return

    email_body = (
        "Hi,\n\n"
        f"Please find attached the EPUB version of the {run_id} "
        "crypto analysis with news.\n\n"
        "Regards,\n"
        "Crypto Morning Reports Bot"
    )
    email_sent = await send_email_with_epub_attachment(
        subject=f"Crypto Analysis with News {today_date} ({run_id})",
        body=email_body,
        attachment_bytes=epub_bytes,
        attachment_filename=epub_filename,
        recipients=recipients,
    )
    if not email_sent:
        app_logger.warning("Failed to send EPUB analysis report via email.")
