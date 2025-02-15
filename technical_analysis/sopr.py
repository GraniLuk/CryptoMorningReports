import requests
from datetime import datetime
from prettytable import PrettyTable
from infra.telegram_logging_handler import app_logger
from technical_analysis.repositories.sopr_repository import save_sopr_results

# Configuration
API_BASE = "https://bitcoin-data.com/"

def fetch_sopr_metrics(conn) -> tuple:
    """
    Retrieves yesterday's SOPR variants from BGeometrics API and saves to database

    Args:
        conn: Database connection

    Returns:
        tuple: (PrettyTable) containing formatted table for display
    """
    metrics = {}
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        # Fetch base SOPR
        response = requests.get(f"{API_BASE}/v1/sopr", params={"day": yesterday})
        metrics["SOPR"] = response.json()[0]
        
        # Fetch STH-SOPR
        response = requests.get(f"{API_BASE}/v1/sth-sopr", params={"day": yesterday})
        metrics["STH-SOPR"] = response.json()[0]
        
        # Fetch LTH-SOPR
        response = requests.get(f"{API_BASE}/v1/lth-sopr", params={"day": yesterday})
        metrics["LTH-SOPR"] = response.json()[0]
        
        # Create pretty table for display
        table = PrettyTable()
        table.field_names = ["Indicator", "Value"]
        table.align["Indicator"] = "l"  # Left align indicator names
        table.align["Value"] = "r"      # Right align values
        
        for metric, data in metrics.items():
            value = float(data.get('sopr') or data.get('sthSopr') or data.get('lthSopr'))
            table.add_row([metric, f"{value:.4f}"])
        
        # Save results to database
        if conn:
            save_sopr_results(conn, metrics)
            app_logger.info("SOPR metrics fetched and saved successfully")
        
        return table
    
    except Exception as e:
        app_logger.error(f"Error fetching SOPR metrics: {str(e)}")
        return None

if __name__ == "__main__":
    table = fetch_sopr_metrics()
    if table:
        print("\nCurrent SOPR Metrics:")
        print(table)
    else:
        print("Failed to retrieve SOPR data")
