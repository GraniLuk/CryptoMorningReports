from azure.monitor.query import LogsQueryClient
from azure.identity import DefaultAzureCredential
from infra.telegram_logging_handler import app_logger
import os
from datetime import timedelta

def fetch_gstgmt_ratio_range():
    try:
        # Initialize credentials and Logs Query Client
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)

        # Define your Application Insights workspace ID
        workspace_id = os.environ.get("PriceAlerts_APPINSIGHTS_WORKSPACE_ID")
        if not workspace_id:
            app_logger.error("Workspace ID environment variable not set")
            return None
            
        app_logger.info(f"Using workspace ID: {workspace_id}")

        # Query to fetch last 24h min and max
        query = """
        AppMetrics
| where TimeGenerated >= ago(24h)
| where Name == "crypto_ratio"
| summarize dailyMin = min(Sum), dailyMax = max(Sum)
        """

        # Add timespan parameter for 24 hours
        timespan = timedelta(hours=24)
        response = client.query_workspace(workspace_id, query, timespan=timespan)
        if response and len(response.tables) > 0 and len(response.tables[0].rows) > 0:
            min_value = response.tables[0].rows[0][0]
            max_value = response.tables[0].rows[0][1]
            range_24h = (max_value - min_value) / min_value * 100
            return min_value, max_value, range_24h
        return None, None, None
    except Exception as e:
        app_logger.error(f"Error fetching ratio range: {str(e)}")
        return None, None, None
    
if __name__ == "__main__":
   print(fetch_gstgmt_ratio_range())