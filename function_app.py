"""Azure Functions app for Crypto Morning Reports."""

import asyncio
import os
from datetime import UTC, datetime

import azure.functions as func
from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from infra.telegram_logging_handler import app_logger
from integrations.onedrive_uploader import upload_to_onedrive
from reports.current_report import generate_crypto_situation_report
from reports.daily_report import process_daily_report
from reports.weekly_report import process_weekly_report
from shared_code.telegram import send_telegram_message


load_dotenv()

app = func.FunctionApp()


async def run_report(report_type="daily", run_id: str = "AM"):
    """Run the specified type of cryptocurrency report (daily or weekly).

    Args:
        report_type: Type of report - 'daily' or 'weekly'
        run_id: Identifier for the run - 'AM' for morning, 'PM' for evening
    """
    app_logger.info(
        f"{report_type.capitalize()} report ({run_id}) started at {datetime.now(UTC).isoformat()}",
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
                await process_daily_report(
                    conn,
                    telegram_enabled,
                    telegram_token,
                    telegram_chat_id,
                    run_id=run_id,
                )
            elif report_type == "weekly":
                await process_weekly_report(
                    conn,
                    telegram_enabled,
                    telegram_token,
                    telegram_chat_id,
                )
        finally:
            if conn:
                conn.close()

    except Exception:
        app_logger.exception("Function failed with error")
        raise


@app.timer_trigger(schedule="0 4 * * *", arg_name="morningTimer", use_monitor=False)
def morning_report(_morning_timer: func.TimerRequest) -> None:
    """Azure Function triggered daily at 4 AM UTC to generate morning reports."""
    asyncio.run(run_report("daily", run_id="AM"))


@app.timer_trigger(schedule="0 16 * * *", arg_name="eveningTimer", use_monitor=False)
def evening_report(_evening_timer: func.TimerRequest) -> None:
    """Azure Function triggered daily at 4 PM UTC to generate evening reports."""
    asyncio.run(run_report("daily", run_id="PM"))


@app.timer_trigger(schedule="0 3 * * 0", arg_name="weeklyTimer", use_monitor=False)
def weekly_report(_weekly_timer: func.TimerRequest) -> None:
    """Azure Function triggered weekly on Sundays at 3 AM UTC to generate weekly reports."""
    asyncio.run(run_report("weekly"))


@app.route(route="manual-trigger")
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP-triggered Azure Function for manually executing reports.

    Query parameters:
        type: 'daily' or 'weekly' (default: 'daily')
        run_id: 'AM' or 'PM' for daily reports (default: 'AM')
    """
    report_type = req.params.get("type", "daily")
    run_id = req.params.get("run_id", "AM").upper()
    if report_type not in ["daily", "weekly"]:
        return func.HttpResponse("Invalid report type. Use 'daily' or 'weekly'.", status_code=400)
    if run_id not in ["AM", "PM"]:
        return func.HttpResponse("Invalid run_id. Use 'AM' or 'PM'.", status_code=400)

    try:
        asyncio.run(run_report(report_type, run_id=run_id))
        return func.HttpResponse(
            f"{report_type.capitalize()} report ({run_id}) executed successfully",
            status_code=200,
        )
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        return func.HttpResponse(f"Function execution failed: {e!s}", status_code=500)


@app.route(route="crypto-situation")
async def crypto_situation(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function to generate a situation report for a specific cryptocurrency.

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
                    f"Failed to generate report for {symbol}.",
                    status_code=500,
                )

            if report.startswith(f"Symbol {symbol} not found"):
                return func.HttpResponse(
                    f"Symbol '{symbol}' not found in the database.",
                    status_code=404,
                )

            if report.startswith(("Failed", "Error")):
                return func.HttpResponse(
                    f"Error generating report: {report}",
                    status_code=500,
                )  # Save to OneDrive if requested
            if save_to_onedrive:
                today_date = datetime.now(UTC).strftime("%Y-%m-%d-%H-%M")
                onedrive_filename = f"{today_date}.md"

                # Use "current_situation/SYMBOL" as folder path
                folder_path = f"current_situation/{symbol.upper()}"

                await upload_to_onedrive(
                    filename=onedrive_filename,
                    content=report,
                    folder_path=folder_path,
                )

            # Send to Telegram if requested
            if send_to_telegram:
                telegram_enabled = os.environ.get("TELEGRAM_ENABLED", "False").lower() == "true"
                telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
                telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

                if telegram_enabled and telegram_token and telegram_chat_id:
                    await send_telegram_message(
                        enabled=telegram_enabled,
                        token=telegram_token,
                        chat_id=telegram_chat_id,
                        message=report,
                        parse_mode="MarkdownV2",
                    )

            # Return the report content
            return func.HttpResponse(report, mimetype="text/markdown")

        finally:
            if conn:
                conn.close()

    except (ValueError, KeyError, TypeError, OSError, RuntimeError, AttributeError) as e:
        app_logger.error(f"Error in crypto_situation function: {e!s}")
        return func.HttpResponse(f"An error occurred: {e!s}", status_code=500)
