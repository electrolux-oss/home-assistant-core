"""Utility functions used by the Electrolux Group integration."""


def round_to_valid_step(value: float, minimum: float, step: float) -> float:
    """Utility function for rounding a value to the closest multiple of a step."""
    return round((value - minimum) / step) * step + minimum
