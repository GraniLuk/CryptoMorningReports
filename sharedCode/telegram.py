import logging
import requests
import time

MAX_TELEGRAM_LENGTH = 4096

async def send_telegram_message(enabled, token, chat_id, message, parse_mode="HTML"):
    if not enabled:
        logging.info('Telegram notifications are disabled')
        return
    
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
        logging.error(f"Failed to send telegram message: {str(e)}")
        return False