"""Telegram messaging utilities and formatting functions.

MIGRATION NOTE: This file is being gradually migrated to the shared_code.telegram package.
The following functions have been moved:
- enforce_markdown_v2, sanitize_html, smart_split -> shared_code.telegram.text_processing
- send_telegram_message, send_telegram_document,
  try_send_report_with_html_or_markdown -> shared_code.telegram.sending

For backward compatibility, these functions are imported from the new package below.
"""

# Import text processing functions from new package for backward compatibility
from shared_code.telegram.text_processing import (
    enforce_markdown_v2,
    sanitize_html,
    smart_split,
)
# Import sending functions from new package for backward compatibility
from shared_code.telegram.sending import (
    send_telegram_document,
    send_telegram_message,
    try_send_report_with_html_or_markdown,
)


MAX_TELEGRAM_LENGTH = 4096
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit for standard bots


# Old function definitions removed - now imported from shared_code.telegram.sending:
# - send_telegram_message() (was lines 36-124)
# - try_send_report_with_html_or_markdown() (was lines 132-158)
# - send_telegram_document() (was lines 207-270)
# And helper functions:
# - _validate_telegram_params() (was lines 167-177)
# - _check_file_size() (was lines 180-191)
# - _send_document_request() (was lines 194-204)


# Old function definitions removed - now imported from shared_code.telegram.text_processing:
# - enforce_markdown_v2() (was lines 122-137)
# - sanitize_html() (was lines 139-157)
# - smart_split() (was lines 156-202)
# - _extend_to_close_tag() (was lines 308-322)


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
    Based on the provided search results, here's an analysis of the most
    insightful and detailed articles for each category:
1. Bitcoin:
<b>Article: Bitcoin hits new all-time high above $109000 ahead of Trump's inauguration</b>
<a href="https://economictimes.indiatimes.com/markets/cryptocurrency/bitcoin-hits-record-above-109000-awaiting-trump/articleshow/117390933.cms">Source</a>

Key insights:
• Bitcoin reached a new record high of $109,114 before settling at $107,508.
• The rally is attributed to Trump's election victory and the nomination of
  cryptocurrency advocate Paul Atkins to lead the US securities regulator.
• Other major altcoins also saw significant gains: XRP (2.9%), Ethereum (4.2%),
  Chainlink (15%), Cardano (2.4%), Hedera (5.3%), Bitget Token (6.4%),
  Uniswap (5%), and $TRUMP (24%).
• The total crypto market cap rose to $2.132 trillion, with Bitcoin's
  dominance at 57.34%.

This article provides valuable insights into Bitcoin's price movement and its
correlation with political events, as well as offering a broader perspective
on the cryptocurrency market.

2. Ethereum:
<b>Article: What is Ethereum 2.0? - Complete Analysis of Future Roadmap</b>
<a href="https://www.tokenmetrics.com/blog/ethereum-2-0">Source</a>

Key insights:
• Ethereum 2.0 aims to address scalability, security, and energy efficiency issues.
• Key technical changes include switching to Proof-of-Stake (PoS) and implementing sharding.
• The upgrade is divided into several phases: Beacon Chain (launched December 2020),
  Shard Chains (expected 2023), Merging (late 2023 or early 2024), and
  Execution Environments (2024 or later).
• Ethereum 2.0 is expected to significantly increase transaction speed and
  capacity, reduce costs, and improve energy efficiency.

This article provides a comprehensive overview of Ethereum 2.0, explaining its
technical aspects and potential impact on the network's performance and
scalability.

3. Other cryptocurrencies from the list [BTC, ETH]:
No additional noteworthy information to report beyond what has already been
covered in the Bitcoin and Ethereum sections.

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

This article provides a brief overview of other cryptocurrencies' performance,
showing significant gains across various altcoins in correlation with
Bitcoin's rise.
"""
    parse_mode = "HTML"
    asyncio.run(
        send_telegram_message(
            enabled=telegram_enabled,
            token=telegram_token,
            chat_id=telegram_chat_id,
            message=message,
            parse_mode=parse_mode,
        ),
    )
