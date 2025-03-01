from datetime import datetime, timedelta
from decimal import Decimal

from backtesting.rsi.excel import save_to_excel
from backtesting.rsi.strategy import run_strategy_for_symbol_internal
from source_repository import fetch_symbols
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi

if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql

    load_dotenv()
    conn = connect_to_sql()
    symbol_to_execute = "XRP"
    rsi = 24
    TP = 1.2
    SL = 1.05
    daysAfterToBuy = 2
    # Option 2: Execute for a single symbol (uncomment below to run for just one symbol)
    symbols = fetch_symbols(conn)
    if symbols:
        filtered_symbols = [
            symbol for symbol in symbols if symbol.symbol_name == symbol_to_execute
        ]
        # Calculate the date 4 years before today
        five_years_ago = datetime.now() - timedelta(days=5 * 365)

        # Assuming you have a valid connection and symbol_id
        candles_data = get_candles_with_rsi(
            conn, filtered_symbols[0].symbol_id, five_years_ago
        )
        result_df, ratio = run_strategy_for_symbol_internal(
            conn, filtered_symbols[0], rsi, Decimal(TP), Decimal(SL), daysAfterToBuy
        )
        print(f"{filtered_symbols[0].symbol_name}: TP Ratio = {ratio:.2f}")
        if not result_df.empty:
            total_profit = result_df["profit"].sum()
        else:
            total_profit = 0.0

        if not result_df.empty:
            save_to_excel(
                result_df, "strategy_results", filtered_symbols[0].symbol_name
            )
