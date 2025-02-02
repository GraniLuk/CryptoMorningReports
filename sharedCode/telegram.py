import logging
import re
import requests
import time

MAX_TELEGRAM_LENGTH = 4096

async def send_telegram_message(enabled, token, chat_id, message, parse_mode="HTML"):
    if not enabled:
        logging.info('Telegram notifications are disabled')
        return
    
    if message is None or len(message) == 0:
        logging.error('Empty message, skipping telegram notification')
        return
    
    if parse_mode == "MarkdownV2":
        message = enforce_markdown_v2(message)
        
    if parse_mode == "HTML":
        message = sanitize_html(message)
    
    try:
        # Split message into chunks
        chunks = [message[i:i + MAX_TELEGRAM_LENGTH] 
                 for i in range(0, len(message), MAX_TELEGRAM_LENGTH)]
        
        for chunk in chunks:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            response = requests.post(url, json={
                'chat_id': chat_id,
                'text': chunk,
                'parse_mode': parse_mode
            })
            response.raise_for_status()
            time.sleep(0.5) 
            
        return True
        
    except Exception as e:
        logging.error(f"Failed to send telegram message: {str(e)} with message {message}")
        return False
    
def enforce_markdown_v2(text):
    # Escape unescaped special chars not in formatting blocks
    return re.sub(
        r'(?<!\\)([_*\[\]()~`>#+=|{}.!-])', 
        r'\\\1', 
        text
    )
    
def sanitize_html(message):
    """
    Escapes any HTML-like substrings that are not valid Telegram allowed tags.
    Allowed tags: b, i, u, s, code, pre, a (opening/closing, with optional attributes for <a>).
    """
    # List the allowed tag names. For the <a> tag, we allow attributes.
    allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a']

    # Regex to match any HTML tag
    tag_regex = re.compile(r'</?([a-zA-Z]+)([^>]*)>')

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

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    import os
    load_dotenv()
    # Example usage
    telegram_enabled = True
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    message = f"""
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
    asyncio.run(send_telegram_message(telegram_enabled, telegram_token, telegram_chat_id, message, parse_mode))