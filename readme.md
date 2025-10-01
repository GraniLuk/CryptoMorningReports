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
- (Optional) Docker + Azure Container Registry access for custom image deployments

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
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

1. Clone the repository.

   ```bash
   git clone https://github.com/yourusername/CryptoMorningReports.git
   cd CryptoMorningReports
   ```

2. Install dependencies.

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

## Deploying with a Custom Container (Pandoc-enabled)

Because `pypandoc` requires the native Pandoc binary, the recommended production deployment is a custom Linux container that bundles Pandoc. The provided `Dockerfile` uses the official Azure Functions Python 4.x base image and installs Pandoc via `apt-get`.

### Build and push to Azure Container Registry (ACR)

```bash
# Authenticate with Azure (ensure you are in the correct subscription)
az login

# Variables
RESOURCE_GROUP="my-functions-rg"
ACR_NAME="myregistry"
IMAGE_NAME="cryptomorningreports"
IMAGE_TAG="v1"

# Log in to ACR (requires acrpull/push permissions)
az acr login --name "$ACR_NAME"

# Build and push the image
docker build -t $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG .
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG
```

> **Security tip:** Prefer managed identity or ACR tokens instead of admin credentials when granting your Function App access to the registry.

### Configure the Azure Function App

1. Create (or update) a Linux Consumption/Premium Function App with the container settings pointing to `acrname.azurecr.io/cryptomorningreports:v1`.
2. Assign the Function App a **Managed Identity** and grant it the `AcrPull` role on the registry.
3. Set required application settings (API keys, Gmail credentials, etc.) in the Function App configuration—never bake secrets into the image.
4. Restart the Function App after updating the image tag.

For repeat deployments, update `IMAGE_TAG`, rebuild, push, and restart the Function App. Consider using GitHub Actions or Azure Container Registry Tasks for automated builds.

## Infrastructure as Code & CI/CD

### Bicep template

The `infra/bicep/main.bicep` template provisions all Azure infrastructure required for the containerized function:

- **Azure Container Registry (ACR)** for storing the Pandoc-enabled image (admin disabled, uses managed identity).
- **Storage account** that provides `AzureWebJobsStorage` and content share.
- **Elastic Premium App Service Plan** sized via `hostingPlanSku` parameter.
- **Linux Function App** running the container image with mandatory app settings pre-configured.
- **ACR pull role assignment** for the Function App’s system-assigned managed identity.

Pass additional application settings via the `appSettings` array parameter (for example to inject API keys). The GitHub Actions workflow handles this automatically using the `FUNCTION_APP_SETTINGS_JSON` secret described below.

### GitHub Actions workflow

`.github/workflows/main_bitcoinchecker.yml` now performs an end-to-end deployment:

1. Sets up Python 3.11, installs dependencies, and runs `pytest`.
2. Logs in to Azure using OpenID Connect (service principal credentials stored as secrets).
3. Builds and pushes the container image defined by `Dockerfile` to ACR (`docker/build-push-action@v5`).
4. Deploys infrastructure and the new image by running the Bicep template with `az deployment group create`.

#### Required repository variables (`Settings → Secrets and variables → Actions`)

Configure the following **variables** (values without quotes):

| Variable | Description |
| --- | --- |
| `ACR_NAME` | Name of the target Azure Container Registry (e.g. `cryptomorningreports`). |
| `ACR_SKU` | *(Optional, default `Basic`)* ACR SKU to deploy (`Basic`, `Standard`, `Premium`). |
| `AZURE_LOCATION` | Azure region for all resources (e.g. `westeurope`). |
| `AZURE_RESOURCE_GROUP` | Resource group name hosting the Function App stack. |
| `AZURE_STORAGE_ACCOUNT_NAME` | Globally unique storage account name. |
| `AZURE_HOSTING_PLAN_NAME` | App Service plan name (Elastic Premium or Premium Container). |
| `AZURE_HOSTING_PLAN_SKU` | *(Optional, default `EP1`)* SKU for the plan (`EP1`, `EP2`, `EP3`, `PC2`, `PC3`, `PC4`). |
| `AZURE_FUNCTION_APP_NAME` | Function App name that will run the container. |

#### Required secrets

| Secret | Description |
| --- | --- |
| `AZURE_CLIENT_ID` | Service principal client ID with rights over the resource group and ACR. |
| `AZURE_TENANT_ID` | Azure AD tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Subscription containing the resources. |
| `FUNCTION_APP_SETTINGS_JSON` | JSON array (as a single line) describing extra app settings, e.g. `[{"name":"GMAIL_USERNAME","value":"user@example.com"},{"name":"GMAIL_PASSWORD","value":"xxxx"}]`. |

Secrets such as `GMAIL_PASSWORD`, `PERPLEXITY_API_KEY`, etc., should be included inside `FUNCTION_APP_SETTINGS_JSON`. The workflow stores them in an `appsettings.json` file that is passed to the Bicep deployment.

> **Tip:** Use a staging environment (GitHub Actions environments) to keep production secrets isolated from development.

## Project Structure

```text
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
