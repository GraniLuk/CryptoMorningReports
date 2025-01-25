from azure.monitor.query import LogsQueryClient
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
from telegram_logging_handler import app_logger

def fetch_gstgmt_ratio_range():
    # Initialize credentials and Logs Query Client
    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)

    # Define your Application Insights workspace ID
    workspace_id = "<WORKSPACE_ID>"

    # Query to fetch yesterday's min and max
    query = """
    customMetrics
    | where timestamp >= ago(2d) and timestamp < ago(1d)
    | where name == "crypto_ratio"
    | extend customMetric_value = iif(itemType == 'customMetric', valueMin, todouble(''))
    | summarize dailyMin = min(customMetric_value), dailyMax = max(customMetric_value) by bin(timestamp, 1d)
    """

    # Query time range for the past 2 days
    end_time = datetime.utcnow() - timedelta(days=1)
    start_time = end_time - timedelta(days=1)

    # Run the query
    response = client.query_workspace(
        workspace_id=workspace_id,
        query=query,
        timespan=(start_time, end_time),
    )

    # Process and print results
    if response.status == 'Success':
        for table in response.tables:
            return table.rows[0]
    else:
        app_logger.error(f"Query failed: {response.error}")