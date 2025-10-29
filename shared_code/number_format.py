def format_to_6digits_without_trailing_zeros(num):
    return f"{num:.6f}".rstrip("0").rstrip(".")
