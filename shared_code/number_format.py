"""Number formatting utilities for cryptocurrency values."""


def format_to_6digits_without_trailing_zeros(num):
    """Format a number to 6 decimal places without trailing zeros."""
    return f"{num:.6f}".rstrip("0").rstrip(".")
