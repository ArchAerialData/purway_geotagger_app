"""PAC (Path Average Concentration) calculation utility."""
from __future__ import annotations
import math


def calculate_pac(
    methane_concentration: float | None,
    relative_altitude: float | None,
    precision: int = 2,
) -> float | None:
    """
    Calculate Path Average Concentration.

    PAC = methane_concentration / relative_altitude

    Args:
        methane_concentration: PPM value from sensor
        relative_altitude: AGL altitude in meters
        precision: Decimal places for rounding (default: 2)

    Returns:
        PAC value rounded to specified precision, or None if inputs are invalid.
        Invalid inputs: None values, zero altitude, negative altitude.
    """
    if methane_concentration is None or relative_altitude is None:
        return None
    if not math.isfinite(methane_concentration) or not math.isfinite(relative_altitude) or relative_altitude <= 0:
        return None  # Avoid division by zero or nonsensical negative altitude
    result = methane_concentration / relative_altitude
    return round(result, precision) if math.isfinite(result) else None
