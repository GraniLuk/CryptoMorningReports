from azure.monitor.query import LogsQueryClient
from azure.identity import DefaultAzureCredential
from telegram_logging_handler import app_logger
import os

def fetch_gstgmt_ratio_range():
    try:
        # Initialize credentials and Logs Query Client
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)

        # Define your Application Insights workspace ID
        workspace_id = os.getenv('PriceAlerts_APPINSIGHTS_WORKSPACE_ID')

        # Query to fetch last 24h min and max
        query = """
        customMetrics
            | where timestamp >= ago(24h)
            | where name == "crypto_ratio"
            | extend customMetric_value = iif(itemType == 'customMetric', valueMin, todouble(''))
            | summarize dailyMin = min(customMetric_value), dailyMax = max(customMetric_value)
        """

        response = client.query_workspace(workspace_id, query)
        if response and len(response.tables) > 0 and len(response.tables[0].rows) > 0:
            min_value = response.tables[0].rows[0][0]
            max_value = response.tables[0].rows[0][1]
            range_24h = (max_value - min_value) / min_value * 100
            return min_value, max_value, range_24h
        return None, None, None
    except Exception as e:
        app_logger.error(f"Error fetching ratio range: {str(e)}")
        return None, None, None