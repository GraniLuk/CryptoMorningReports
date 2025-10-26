# ruff: noqa: N999
def format_to_6digits_withoutTrailingZeros(num):
    return f"{num:.6f}".rstrip("0").rstrip(".")
