import asyncio
import logging
import os
from datetime import UTC, datetime

import azure.functions as func
from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from infra.telegram_logging_handler import app_logger
from reports.current_report import generate_crypto_situation_report
from reports.daily_report import process_daily_report
from reports.weekly_report import process_weekly_report


load_dotenv()

app = func.FunctionApp()


async def run_report(report_type="daily"):
    logging.info(
        f"{report_type.capitalize()} report function started at {datetime.now(UTC).isoformat()}"
    )

    logger = app_logger

    try:
        # Load configuration
        telegram_enabled = os.environ["TELEGRAM_ENABLED"].lower() == "true"
        telegram_token = os.environ["TELEGRAM_TOKEN"]
        telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
        logger.info("Configuration loaded. Telegram enabled: %s", telegram_enabled)

        conn = connect_to_sql()
        try:
            if report_type == "daily":
                await process_daily_report(conn, telegram_enabled, telegram_token, telegram_chat_id)
            elif report_type == "weekly":
                await process_weekly_report(
                    conn, telegram_enabled, telegram_token, telegram_chat_id
                )
        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.error(f"Function failed with error: {e!s}")
        raise


@app.timer_trigger(schedule="0 4 * * *", arg_name="dailyTimer", use_monitor=False)
def daily_report(_daily_timer: func.TimerRequest) -> None:
    asyncio.run(run_report("daily"))


@app.timer_trigger(schedule="0 3 * * 0", arg_name="weeklyTimer", use_monitor=False)
def weekly_report(_weekly_timer: func.TimerRequest) -> None:
    asyncio.run(run_report("weekly"))


@app.route(route="manual-trigger")
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    report_type = req.params.get("type", "daily")
    if report_type not in ["daily", "weekly"]:
        return func.HttpResponse("Invalid report type. Use 'daily' or 'weekly'.", status_code=400)

    try:
        asyncio.run(run_report(report_type))
        return func.HttpResponse(
            f"{report_type.capitalize()} report executed successfully", status_code=200
        )
    except Exception as e:
        return func.HttpResponse(f"Function execution failed: {e!s}", status_code=500)


@app.route(route="crypto-situation")
async def crypto_situation(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger function to generate a situation report for a specific cryptocurrency.

    Query parameters:
    - symbol: Cryptocurrency symbol (e.g., "BTC", "ETH") [required]
    - save_to_onedrive: Set to "true" to save the report to OneDrive [optional]
    - send_to_telegram: Set to "true" to send the report to Telegram [optional]

    Returns:
    - HTTP 200 with report content if successful
    - HTTP 400 if symbol parameter is missing
    - HTTP 404 if symbol is not found in the database
    - HTTP 500 if an error occurs during report generation
    """
    try:
        # Get required parameters
        symbol = req.params.get("symbol")

        if not symbol:
            return func.HttpResponse(
                "Please provide a cryptocurrency symbol using the 'symbol' query parameter.",
                status_code=400,
            )

        # Get optional parameters
        save_to_onedrive = req.params.get("save_to_onedrive", "").lower() == "true"
        send_to_telegram = req.params.get("send_to_telegram", "").lower() == "true"

        # Connect to database
        conn = connect_to_sql()
        try:
            # Generate the report
            report = await generate_crypto_situation_report(conn, symbol.upper())

            if not report:
                return func.HttpResponse(
                    f"Failed to generate report for {symbol}.", status_code=500
                )

            if report.startswith(f"Symbol {symbol} not found"):
                return func.HttpResponse(
                    f"Symbol '{symbol}' not found in the database.", status_code=404
                )

            if report.startswith(("Failed", "Error")):
                return func.HttpResponse(
                    f"Error generating report: {report}", status_code=500
                )  # Save to OneDrive if requested
            if save_to_onedrive:
                from integrations.onedrive_uploader import upload_to_onedrive

                today_date = datetime.now(UTC).strftime("%Y-%m-%d-%H-%M")
                onedrive_filename = f"{today_date}.md"

                # Use "current_situation/SYMBOL" as folder path
                folder_path = f"current_situation/{symbol.upper()}"

                await upload_to_onedrive(
                    filename=onedrive_filename, content=report, folder_path=folder_path
                )

            # Send to Telegram if requested
            if send_to_telegram:
                from shared_code.telegram import send_telegram_message

                telegram_enabled = os.environ.get("TELEGRAM_ENABLED", "False").lower() == "true"
                telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
                telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

                if telegram_enabled and telegram_token and telegram_chat_id:
                    await send_telegram_message(
                        telegram_enabled,
                        telegram_token,
                        telegram_chat_id,
                        report,
                        parse_mode="MarkdownV2",
                    )

            # Return the report content
            return func.HttpResponse(report, mimetype="text/markdown")

        finally:
            if conn:
                conn.close()

    except Exception as e:
        app_logger.error(f"Error in crypto_situation function: {e!s}")
        return func.HttpResponse(f"An error occurred: {e!s}", status_code=500)
