import logging
import aiohttp

async def send_telegram_message(enabled, token, chat_id, message, parse_mode="HTML"):
    if not enabled:
        logging.info('Telegram notifications are disabled')
        return
    
     # Truncate message if longer than Telegram's limit
    MAX_TELEGRAM_LENGTH = 4096
    if len(message) > MAX_TELEGRAM_LENGTH:
        message = message[:MAX_TELEGRAM_LENGTH]
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.text()
                logging.info('Telegram API response: %s', result)
    except Exception as e:
        logging.error('Failed to send Telegram message: %s', str(e))