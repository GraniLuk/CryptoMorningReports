import html
import logging
import re
import time

import requests


MAX_TELEGRAM_LENGTH = 4096
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit for standard bots


async def send_telegram_message(
    enabled,
    token,
    chat_id,
    message,
    parse_mode: str | None = "HTML",
    disable_web_page_preview: bool = False,
    disable_notification: bool = False,
    protect_content: bool = False,
):
    if not enabled:
        logging.info("Telegram notifications are disabled")
        return None

    if message is None or len(message) == 0:
        logging.error("Empty message, skipping telegram notification")
        return None

    original_parse_mode = parse_mode

    if parse_mode == "MarkdownV2":
        message = enforce_markdown_v2(message)
    elif parse_mode == "HTML":
        message = sanitize_html(message)
    elif parse_mode not in (None, ""):
        logging.warning(
            "Unsupported parse_mode '%s' provided. Falling back to raw text (no parse mode).",
            parse_mode,
        )
        parse_mode = None

    try:
        # Split message into chunks at paragraph boundaries where possible
        chunks = smart_split(message, MAX_TELEGRAM_LENGTH, parse_mode)

        for chunk in chunks:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
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

            response = requests.post(url, json=payload)

            if not response.ok:
                # Gather diagnostics
                try:
                    err_json = response.json()
                except Exception:
                    err_json = {"raw_text": (response.text[:500] if response.text else None)}
                logging.error(
                    "Telegram API error (status=%s, parse_mode=%s original_parse_mode=%s, chunk_len=%d): %s",
                    response.status_code,
                    parse_mode,
                    original_parse_mode,
                    len(chunk),
                    err_json,
                )
                response.raise_for_status()
            time.sleep(0.5)

        return True

    except Exception as e:
        # Avoid logging the entire large message to keep logs clean / protect data
        snippet = (message[:500] + "...<truncated>") if len(message) > 600 else message
        logging.error(
            "Failed to send telegram message: %s | snippet: %s", str(e), snippet
        )
        return False


def enforce_markdown_v2(text: str) -> str:
    """Escape characters required by Telegram MarkdownV2 while preserving existing
    code spans. We do a lightweight parse: split by backticks and only escape in the
    non-code segments (even indices after split). This is not a full Markdown parser
    but sufficient for typical report content.
    """
    # Telegram MarkdownV2 special chars to escape:
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    special_pattern = re.compile(r"([_\*\[\]\(\)~`>#\+\-=\|{}\.\!])")
    parts = text.split("`")
    for i in range(0, len(parts), 2):  # only escape outside code spans
        parts[i] = special_pattern.sub(r"\\\1", parts[i])
    # Rejoin with unescaped backticks between parts
    return "`".join(parts)


def sanitize_html(message):
    """
    Escapes any HTML-like substrings that are not valid Telegram allowed tags.
    Allowed tags: b, i, u, s, code, pre, a (opening/closing, with optional attributes for <a>).
    """
    # List the allowed tag names. For the <a> tag, we allow attributes.
    allowed_tags = ["b", "i", "u", "s", "code", "pre", "a"]

    # Regex to match any HTML tag
    tag_regex = re.compile(r"</?([a-zA-Z]+)([^>]*)>")

    def replace_tag(match):
        tag_name = match.group(1).lower()
        full_tag = match.group(0)
        # Check if tag_name is one of the allowed tags.
        if tag_name in allowed_tags:
            # For safety, you can choose to do extra validation on attributes if needed.
            return full_tag
        # Escape the entire tag if not allowed.
        return html.escape(full_tag)

    # Replace any found HTML tag with our conditional replacement.
    return tag_regex.sub(replace_tag, message)


async def try_send_report_with_HTML_or_Markdown(
    telegram_enabled, telegram_token, telegram_chat_id, message
):
    # Try HTML first
    success = await send_telegram_message(
        telegram_enabled, telegram_token, telegram_chat_id, message, parse_mode="HTML"
    )

    # If HTML failed, try MarkdownV2
    if not success:
        success = await send_telegram_message(
            telegram_enabled,
            telegram_token,
            telegram_chat_id,
            message,
            parse_mode="MarkdownV2",
        )

    return success


def smart_split(text: str, limit: int, parse_mode: str | None) -> list[str]:
    """Split the text into <=limit sized chunks, preferring to break on double newlines
    (paragraphs). If a single paragraph exceeds the limit, fall back to hard slicing.
    For HTML parse_mode we also try not to cut inside an open tag (very naive: ensure
    open '<' without closing '>' inside the slice gets extended to the closing '>').
    """
    if len(text) <= limit:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = []
    current_len = 0
    for p in paragraphs:
        p_block = (p + "\n\n")  # keep delimiter
        if len(p_block) > limit:
            # Flush current
            if current:
                chunks.append("".join(current).rstrip())
                current = []
                current_len = 0
            # Hard slice this oversize paragraph
            for i in range(0, len(p_block), limit):
                slice_ = p_block[i : i + limit]
                if parse_mode == "HTML":
                    slice_ = _extend_to_close_tag(p_block, i, slice_, limit)
                chunks.append(slice_)
            continue
        if current_len + len(p_block) <= limit:
            current.append(p_block)
            current_len += len(p_block)
        else:
            chunks.append("".join(current).rstrip())
            current = [p_block]
            current_len = len(p_block)

    if current:
        chunks.append("".join(current).rstrip())
    return chunks


async def send_telegram_document(
    enabled: bool,
    token: str,
    chat_id: str,
    file_bytes: bytes | None = None,
    filename: str = "report.txt",
    caption: str | None = None,
    parse_mode: str | None = None,
    local_path: str | None = None,
):
    """Send a document (e.g. markdown report) to Telegram.
    Either provide file_bytes OR a local_path. If both are provided local_path takes precedence.
    Returns True on success, False otherwise.
    """
    if not enabled:
        logging.info("Telegram notifications are disabled")
        return False

    if not token or not chat_id:
        logging.error("Missing token or chat_id for send_telegram_document")
        return False

    file_handle = None
    close_after = False
    try:
        if local_path:
            if not os.path.exists(local_path):
                logging.error("Local file does not exist: %s", local_path)
                return False
            file_size = os.path.getsize(local_path)
            if file_size > MAX_DOCUMENT_SIZE:
                logging.error(
                    "File %s exceeds Telegram max size (%d > %d)",
                    local_path,
                    file_size,
                    MAX_DOCUMENT_SIZE,
                )
                return False
            file_handle = open(local_path, "rb")
            close_after = True
        else:
            if file_bytes is None:
                logging.error("Neither file_bytes nor local_path provided for document")
                return False
            if len(file_bytes) > MAX_DOCUMENT_SIZE:
                logging.error(
                    "In-memory file exceeds Telegram max size (%d > %d)",
                    len(file_bytes),
                    MAX_DOCUMENT_SIZE,
                )
                return False
            file_handle = file_bytes
            close_after = False

        url = f"https://api.telegram.org/bot{token}/sendDocument"
        files = {
            "document": (filename, file_handle, "application/octet-stream"),
        }
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption[:1024]  # Telegram caption limit
        if parse_mode:
            data["parse_mode"] = parse_mode

        response = requests.post(url, data=data, files=files)
        if not response.ok:
            try:
                err_json = response.json()
            except Exception:
                err_json = {"raw": response.text[:300]}
            logging.error(
                "Failed to send document (status=%s): %s", response.status_code, err_json
            )
            return False
        logging.info("Document %s successfully sent to Telegram", filename)
        return True
    except Exception as e:
        logging.error("Exception while sending document: %s", e)
        return False
    finally:
        if close_after and hasattr(file_handle, "close"):
            try:
                file_handle.close()  # type: ignore[attr-defined]
            except Exception:
                pass


def _extend_to_close_tag(full_text: str, start_index: int, slice_: str, limit: int) -> str:
    """If the slice ends in the middle of an HTML tag (has unmatched '<'), extend until
    the closing '>' if possible within a small lookahead window. This is a heuristic to
    reduce parse errors when using HTML parse_mode."""
    if slice_.count("<") == slice_.count(">"):
        return slice_
    # Look ahead up to 200 chars beyond limit (Telegram still enforces limit, so we must respect it)
    # If we can't fix within limit, return original slice.
    # Since we cannot exceed limit, we actually can only shrink, not extend. So instead we try to
    # trim back to last '>' to avoid dangling '<'.
    last_gt = slice_.rfind(">")
    last_lt = slice_.rfind("<")
    if last_lt > last_gt:
        # drop dangling part after last '<'
        return slice_[:last_lt]
    return slice_


if __name__ == "__main__":
    import asyncio
    import os

    from dotenv import load_dotenv

    load_dotenv()
    # Example usage
    telegram_enabled = True
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    message = """
    Based on the provided search results, here's an analysis of the most insightful and detailed articles for each category:                                                                                                                                                   
1. Bitcoin:                                                                              
<b>Article: Bitcoin hits new all-time high above $109000 ahead of Trump's inauguration</b>                                                                                        
<a href="https://economictimes.indiatimes.com/markets/cryptocurrency/bitcoin-hits-record-above-109000-awaiting-trump/articleshow/117390933.cms">Source</a>

Key insights:
• Bitcoin reached a new record high of $109,114 before settling at $107,508.
• The rally is attributed to Trump's election victory and the nomination of cryptocurrency advocate Paul Atkins to lead the US securities regulator.
• Other major altcoins also saw significant gains: XRP (2.9%), Ethereum (4.2%), Chainlink (15%), Cardano (2.4%), Hedera (5.3%), Bitget Token (6.4%), Uniswap (5%), and $TRUMP (24%).
• The total crypto market cap rose to $2.132 trillion, with Bitcoin's dominance at 57.34%.

This article provides valuable insights into Bitcoin's price movement and its correlation with political events, as well as offering a broader perspective on the cryptocurrency market.

2. Ethereum:
<b>Article: What is Ethereum 2.0? - Complete Analysis of Future Roadmap</b>
<a href="https://www.tokenmetrics.com/blog/ethereum-2-0">Source</a>

Key insights:
• Ethereum 2.0 aims to address scalability, security, and energy efficiency issues.      
• Key technical changes include switching to Proof-of-Stake (PoS) and implementing sharding.
• The upgrade is divided into several phases: Beacon Chain (launched December 2020), Shard Chains (expected 2023), Merging (late 2023 or early 2024), and Execution Environments (2024 or later).
• Ethereum 2.0 is expected to significantly increase transaction speed and capacity, reduce costs, and improve energy efficiency.

This article provides a comprehensive overview of Ethereum 2.0, explaining its technical aspects and potential impact on the network's performance and scalability.

3. Other cryptocurrencies from the list [BTC, ETH]:
No additional noteworthy information to report beyond what has already been covered in the Bitcoin and Ethereum sections.

4. Other cryptocurrencies not from the list [BTC, ETH]:
<b>Article: Bitcoin hits new all-time high above $109000 ahead of Trump's inauguration</b>
<a href="https://economictimes.indiatimes.com/markets/cryptocurrency/bitcoin-hits-record-above-109000-awaiting-trump/articleshow/117390933.cms">Source</a>

Key insights:
• XRP rose 2.9%
• Chainlink led with a 15% surge
• Cardano increased by 2.4%
• Hedera rose 5.3%
• Bitget Token increased 6.4%
• Uniswap rose 5%
• $TRUMP soared 24%

This article provides a brief overview of other cryptocurrencies' performance, showing significant gains across various altcoins in correlation with Bitcoin's rise.
"""
    parse_mode = "HTML"
    asyncio.run(
        send_telegram_message(
            telegram_enabled, telegram_token, telegram_chat_id, message, parse_mode
        )
    )
