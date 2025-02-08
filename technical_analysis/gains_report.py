from technical_analysis.repositories.priceRangeRepository import save_price_range_results
from prettytable import PrettyTable
from infra.telegram_logging_handler import app_logger
from typing import List
from source_repository import Symbol
from sharedCode.priceChecker import fetch_current_price


def fetch_24change_report(symbols : List[Symbol], conn) -> PrettyTable:
    results = []
    for symbol in symbols:
        try:
            
    