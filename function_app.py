import asyncio
import logging
import os
from datetime import datetime

import azure.functions as func
from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from infra.telegram_logging_handler import app_logger
from reports.daily_report import process_daily_report
from reports.weekly_report import process_weekly_report

load_dotenv()

app = func.FunctionApp()


async def run_report(report_type="daily"):
    logging.info(
        f"{report_type.capitalize()} report function started at {datetime.now().isoformat()}"
    )

    try:
        # Load configuration
        telegram_enabled = os.environ["TELEGRAM_ENABLED"].lower() == "true"
        telegram_token = os.environ["TELEGRAM_TOKEN"]
        telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
        logger = app_logger
        logger.info("Configuration loaded. Telegram enabled: %s", telegram_enabled)

        conn = connect_to_sql()
        try:
            if report_type == "daily":
                await process_daily_report(
                    conn, telegram_enabled, telegram_token, telegram_chat_id
                )
            elif report_type == "weekly":
                await process_weekly_report(
                    conn, telegram_enabled, telegram_token, telegram_chat_id
                )
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Function failed with error: {str(e)}")
        raise


@app.timer_trigger(schedule="0 4 * * *", arg_name="dailyTimer", use_monitor=False)
def DailyReport(dailyTimer: func.TimerRequest) -> None:
    asyncio.run(run_report("daily"))


@app.timer_trigger(schedule="0 3 * * 0", arg_name="weeklyTimer", use_monitor=False)
def WeeklyReport(weeklyTimer: func.TimerRequest) -> None:
    asyncio.run(run_report("weekly"))


@app.route(route="manual-trigger")
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    report_type = req.params.get("type", "daily")
    if report_type not in ["daily", "weekly"]:
        return func.HttpResponse(
            "Invalid report type. Use 'daily' or 'weekly'.", status_code=400
        )

    try:
        asyncio.run(run_report(report_type))
        return func.HttpResponse(
            f"{report_type.capitalize()} report executed successfully", status_code=200
        )
    except Exception as e:
        return func.HttpResponse(
            f"Function execution failed: {str(e)}", status_code=500
        )
