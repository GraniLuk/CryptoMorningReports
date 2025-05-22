from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.identity import DefaultAzureCredential
from infra.telegram_logging_handler import app_logger
import os
from datetime import timedelta


def fetch_gstgmt_ratio_range() -> tuple[float, float, float]:
    try:
        # Initialize credentials and Logs Query Client
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)

        # Define your Application Insights workspace ID
        workspace_id = os.environ.get("PriceAlerts_APPINSIGHTS_WORKSPACE_ID")
        if not workspace_id:
            app_logger.error("Workspace ID environment variable not set")
            return 0, 0, 0  # Return default values instead of None

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
        
        # Properly check response status according to Azure SDK pattern
        if response.status == LogsQueryStatus.SUCCESS:
            # Access tables directly from successful response
            if len(response.tables) > 0 and len(response.tables[0].rows) > 0:
                min_value = response.tables[0].rows[0][0]
                max_value = response.tables[0].rows[0][1]
                
                # Handle None values that might come from the query
                if min_value is None or max_value is None:
                    app_logger.info("Received None values from the query, using default values")
                    return 0, 0, 0
                    
                # Calculate range safely
                range_24h = (max_value - min_value) / min_value * 100 if min_value > 0 else 0
                return min_value, max_value, range_24h
        elif response.status == LogsQueryStatus.PARTIAL:
            # For partial results, we should use partial_data instead of tables
            app_logger.warning(f"Partial result received: {response.partial_error}")
            if len(response.partial_data) > 0 and len(response.partial_data[0].rows) > 0:
                # Process partial data if available
                min_value = response.partial_data[0].rows[0][0]
                max_value = response.partial_data[0].rows[0][1]
                
                # Handle None values that might come from the query
                if min_value is None or max_value is None:
                    app_logger.info("Received None values from the partial data, using default values")
                    return 0, 0, 0
                    
                # Calculate range safely
                range_24h = (max_value - min_value) / min_value * 100 if min_value > 0 else 0
                return min_value, max_value, range_24h
            
        app_logger.info("No data found in query response, using default values")
        return 0, 0, 0  # Return default values when no data
    except Exception as e:
        app_logger.error(f"Error fetching ratio range: {str(e)}")
        return 0, 0, 0  # Return default values on error


if __name__ == "__main__":
    print(fetch_gstgmt_ratio_range())
