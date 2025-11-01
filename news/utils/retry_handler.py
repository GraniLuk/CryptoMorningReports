"""Retry handler for AI API requests with fallback model support."""

from collections.abc import Callable
from typing import Any

from infra.telegram_logging_handler import app_logger


def retry_with_fallback_models(
    models: list[str],
    request_func: Callable[[str], tuple[bool, Any]],
    operation_name: str = "API request",
) -> Any:
    """Retry a request with a list of fallback models.

    Args:
        models: List of model names to try in order
        request_func: Function that takes a model name and returns (success: bool, result: Any)
                     On success, result is the response content
                     On failure, result is the error message
        operation_name: Name of the operation for logging purposes

    Returns:
        The successful response content, or an error message if all retries fail

    """
    max_retries = len(models)
    current_try = 0

    while current_try < max_retries:
        current_model = models[current_try]
        app_logger.info(f"{operation_name}: Attempting with model: {current_model}")

        try:
            success, result = request_func(current_model)

            if success:
                app_logger.info(f"{operation_name}: Successfully processed with {current_model}")
                return result
            # Result contains error message
            if "504" in str(result) and current_try < max_retries - 1:
                app_logger.warning(
                    f"{operation_name}: Received 504 error with {current_model}, "
                    f"retrying with next model",
                )
                current_try += 1
                continue
            if current_try < max_retries - 1:
                app_logger.warning(
                    f"{operation_name}: Failed with {current_model}, retrying with next model",
                )
                current_try += 1
                continue
            app_logger.error(f"{operation_name}: {result}")
        except Exception as e:
            error_msg = f"Failed {operation_name}: {e!s}"
            app_logger.exception(error_msg)
            if current_try < max_retries - 1:
                current_try += 1
                continue
            return error_msg
        else:
            return result

    return f"Failed: All retry attempts exhausted after trying models: {', '.join(models)}"
