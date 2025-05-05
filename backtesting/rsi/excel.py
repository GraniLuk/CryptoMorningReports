from datetime import datetime, timezone


def save_to_excel(df, prefix, symbol_name=None):
    """Helper function to save DataFrame to Excel with consistent naming"""
    current_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    if symbol_name:
        filename = f"{prefix}_{symbol_name}_{current_date}.xlsx"
    else:
        filename = f"{prefix}_{current_date}.xlsx"
    df.to_excel(filename, index=False)
    print(f"\nResults saved to '{filename}'")
