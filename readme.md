# Crypto Morning Reports

An automated cryptocurrency market analysis tool that generates comprehensive daily reports about the crypto market, delivering insights through Telegram messages.

## Features

### Technical Analysis
- **RSI (Relative Strength Index)**
  - Tracks overbought and oversold conditions
  - Helps identify potential market reversals

- **Moving Averages**
  - Simple Moving Average (SMA)
  - Exponential Moving Average (EMA)
  - Multiple timeframes analysis

- **MACD (Moving Average Convergence Divergence)**
  - Momentum indicator
  - Trend direction and strength analysis
  - Signal line crossovers

- **Market Capitalization**
  - Track market dominance
  - Market value comparisons
  - Market cap rankings

- **Price Change Analysis**
  - 24-hour price changes
  - 7-day price changes
  - Percentage-based comparisons
  - Sorted by performance

- **Price Range Monitoring**
  - 24-hour high/low tracking
  - Range percentage calculation
  - Volatility insights
  - Historical price ranges

- **Volume Analysis**
  - 24-hour trading volume
  - Multi-exchange volume aggregation (Binance, KuCoin)
  - Volume-based ranking
  - USD-denominated values

### Additional Features
- Daily and weekly automated reports
- Telegram integration for instant notifications
- Multi-exchange price monitoring (Binance, KuCoin)
- Customizable cryptocurrency tracking
- News aggregation and analysis

## Setup

### Prerequisites
- Python 3.8+
- Azure Functions Core Tools
- SQL Server
- Telegram Bot Token

### Environment Variables
Create a `.env` file in the root directory with the following variables:
```
TELEGRAM_ENABLED=true
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SQL_PASSWORD=your_sql_password
KUCOIN_API_KEY=your_kucoin_api_key
KUCOIN_API_SECRET=your_kucoin_secret
KUCOIN_API_PASSPHRASE=your_kucoin_passphrase
PERPLEXITY_API_KEY=your_perplexity_api_key
```

### Installation
1. Clone the repository
```bash
git clone https://github.com/yourusername/CryptoMorningReports.git
cd CryptoMorningReports
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Manual Trigger
You can manually trigger reports using the HTTP endpoint:
```bash
curl "http://localhost:7071/api/manual-trigger?type=daily"
```

### Automated Reports
The application runs automatically based on the following schedule:
- Daily reports: Every day at 5:00 UTC
- Weekly reports: Every Sunday at 4:00 UTC

## Project Structure
```
CryptoMorningReports/
├── reports/              # Report generation modules
├── technical_analysis/   # Technical indicators calculation
├── news/                # News aggregation and analysis
├── sharedCode/          # Shared utilities and API clients
├── infra/               # Infrastructure and configuration
└── function_app.py      # Azure Functions entry point
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)