# Telegram Error & Warning Logging

## Overview

The application now sends all WARNING and ERROR level logs to your Telegram channel automatically. This helps you stay informed about issues even when you're not actively monitoring the application.

## What Gets Sent to Telegram?

- **⚠️ WARNING logs**: Rate limit warnings, quota warnings, configuration issues
- **🔴 ERROR logs**: Failed API calls, exceptions, critical failures
- **🚨 CRITICAL logs**: System-critical errors

## Configuration

To enable Telegram notifications for warnings and errors, ensure these environment variables are set:

### Required Environment Variables

```bash
# Enable Telegram logging
TELEGRAM_ENABLED=true

# Your Telegram bot token (same as for reports)
TELEGRAM_TOKEN=your_bot_token_here

# Your Telegram chat ID (same channel where reports are sent)
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Where to Add These Variables

1. **For Azure Functions**: Add to Application Settings in Azure Portal
2. **For Local Development**: Add to your `.env` file or `local.settings.json` (unencrypted version)
3. **For scheduled tasks**: Ensure they're in your system environment

### Example `.env` file:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890
```

## Message Format

Telegram notifications are formatted with HTML for better readability:

```
⚠️ WARNING
Module: gemini_client.py
Time: 2025-12-15 17:07:47

Message:
Failed with gemini-2.5-pro: 429 RESOURCE_EXHAUSTED...

Exception: ServerError: 503 UNAVAILABLE

Traceback (last 5 frames):
[traceback details...]
```

## Log Levels

The application uses the following log levels:

- **DEBUG**: Detailed diagnostic info (not sent to Telegram)
- **INFO**: General informational messages (not sent to Telegram)
- **WARNING**: ⚠️ Sent to Telegram - something unexpected but recoverable
- **ERROR**: 🔴 Sent to Telegram - an error occurred that needs attention
- **CRITICAL**: 🚨 Sent to Telegram - system-critical failure

## Controlling Log Level

You can control the overall log level (for console output) with:

```bash
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Note: Telegram notifications will always capture WARNING and above, regardless of LOG_LEVEL setting.

## Testing

To test if Telegram logging is working:

1. Ensure `TELEGRAM_ENABLED=true`
2. Run the application
3. Trigger a warning or error (or wait for one to occur naturally)
4. Check your Telegram channel for the notification

## Troubleshooting

### Not Receiving Notifications?

1. **Check environment variables**: Ensure `TELEGRAM_ENABLED=true` and credentials are set
2. **Check bot permissions**: Ensure your bot has permission to send messages to the channel
3. **Check the console logs**: Look for the message "Telegram handler initialized - will send WARNING and ERROR logs to Telegram"
4. **Check for warnings**: If you see "Telegram handler not configured - missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID", the credentials are missing

### Too Many Notifications?

If you're getting too many WARNING notifications, you can:

1. Fix the underlying issues causing warnings
2. Modify `telegram_logging_handler.py` to only send ERROR level:
   ```python
   telegram_handler.setLevel(logging.ERROR)  # Only errors, not warnings
   ```

## Examples from Your Logs

Based on your example logs, you'll now receive Telegram notifications for:

1. ⚠️ **Rate Limit Warnings**: When Gemini API quota is exceeded
2. ⚠️ **Fallback Model Warnings**: When primary model fails and fallback is used
3. 🔴 **API Errors**: When all retry attempts are exhausted
4. 🔴 **Server Overload**: When model is unavailable (503 errors)

## Implementation Details

The logging system uses Python's standard `logging` module with a custom `TelegramHandler`:

- Located in: `infra/telegram_logging_handler.py`
- Initialized automatically when application starts
- Formats messages with HTML for better readability
- Includes exception tracebacks (last 5 frames to avoid message length issues)
- Automatically truncates long messages to fit Telegram's 4096 character limit

## Related Files

- `infra/telegram_logging_handler.py` - Main logging handler
- `shared_code/telegram/sending.py` - Telegram sending utilities (for reports)
- `docs/TELEGRAM_FORMATTING.md` - Telegram formatting guide (for reports)
