# Running Azure Functions Locally

This guide shows you how to run your Azure Functions locally without deploying to Azure.

## Prerequisites

- Python 3.11 installed
- Virtual environment set up (`.venv`)
- All dependencies installed (`pip install -r requirements.txt`)

## Quick Start

### 1. Set Up Environment Variables

Copy the example file and fill in your values:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` with your actual configuration values.

### 2. Run a Report

Use the PowerShell helper script:

```powershell
# Run daily report (default)
.\run-local.ps1

# Run daily report (explicit)
.\run-local.ps1 daily

# Run weekly report
.\run-local.ps1 weekly

# Run current situation report for a specific symbol
.\run-local.ps1 current BTC
.\run-local.ps1 current ETH
```

### 3. Alternative: Direct Python Execution

You can also run directly with Python:

```powershell
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1

# Run daily report
python local_runner.py daily

# Run weekly report
python local_runner.py weekly

# Run current situation report
python local_runner.py current BTC
```

## Configuration

### Required Environment Variables

Your `.env` file must include:

```env
# Database
SQL_SERVER=your_server.database.windows.net
SQL_DATABASE=your_database
SQL_USERNAME=your_username
SQL_PASSWORD=your_password

# Telegram
TELEGRAM_ENABLED=true
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# AI API
AI_API_KEY=your_api_key
AI_API_TYPE=gemini
```

### Optional Environment Variables

```env
# OneDrive (for saving reports)
ONEDRIVE_CLIENT_ID=...
ONEDRIVE_CLIENT_SECRET=...
ONEDRIVE_TENANT_ID=...
ONEDRIVE_REFRESH_TOKEN=...

# Email (for email reports)
EMAIL_SENDER=...
EMAIL_RECEIVER=...
EMAIL_PASSWORD=...

# Article Caching (optional)
# ARTICLE_CACHE_ROOT=/path/to/custom/cache
# ARTICLE_CACHE_ROOT=~/crypto_cache/articles  # Supports user home expansion
# If not set, defaults to news/cache relative to project root
#
# For Azure Functions local.settings.json, add to Values section:
# "ARTICLE_CACHE_ROOT": "/path/to/custom/cache"
```

## Troubleshooting

### Virtual Environment Issues

If you get errors about missing packages:

```powershell
# Recreate virtual environment
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Database Connection Issues

- Ensure your SQL Server allows connections from your local IP
- Check firewall rules in Azure Portal
- Verify credentials in `.env` file

### Logging

Logs will be output to:
- Console (stdout/stderr)
- Telegram (if enabled)

Set logging level in your code if needed:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## What's Different from Azure?

When running locally:
- ✅ All business logic works the same
- ✅ Database connections work (if firewall allows)
- ✅ Telegram notifications work
- ✅ API calls work (Gemini, Perplexity, etc.)
- ❌ No timer triggers (you run manually)
- ❌ No HTTP endpoints (unless you use Azure Functions Core Tools)
- ⚠️ Storage might use local emulator instead of Azure Storage

## Using Azure Functions Core Tools (Optional)

For a full Azure Functions experience locally, install Core Tools:

```powershell
# Install via npm
npm install -g azure-functions-core-tools@4

# Or via chocolatey
choco install azure-functions-core-tools

# Then run
func start
```

This will give you:
- HTTP endpoints at http://localhost:7071
- Timer trigger simulation
- Full Azure Functions runtime

## Production Deployment

When your Azure subscription is back:

```powershell
# Via GitHub Actions (recommended)
git add .
git commit -m "Update report"
git push

# Or manually via Azure Functions Core Tools
func azure functionapp publish YourFunctionAppName
```
