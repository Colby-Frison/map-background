"""Parse map size, location, and radius values from the command line."""

from __future__ import annotations

import argparse
import math


def parse_aspect(value: str) -> float:
    """Return width / height for a ratio like ``16:9`` or a positive number."""
    text = value.strip()
    if ":" in text:
        parts = text.split(":")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(
                "Aspect ratio must look like 16:9 or a positive number."
            )
        try:
            width = float(parts[0])
            height = float(parts[1])
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "Aspect ratio must look like 16:9 or a positive number."
            ) from exc
        if width <= 0 or height <= 0:
            raise argparse.ArgumentTypeError("Aspect ratio values must be greater than 0.")
        return width / height

    try:
        ratio = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Aspect ratio must look like 16:9 or a positive number."
        ) from exc
    if not math.isfinite(ratio) or ratio <= 0:
        raise argparse.ArgumentTypeError("Aspect ratio must be greater than 0.")
    return ratio


def parse_coordinates(value: str) -> tuple[float, float] | None:
    """Return ``(lat, lon)`` when ``value`` is a coordinate pair.

    Place names such as ``Athens, Greece`` return ``None``. Numeric pairs
    outside the valid latitude and longitude ranges raise ``ValueError``.
    """
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        return None
    try:
        latitude = float(parts[0])
        longitude = float(parts[1])
    except ValueError:
        return None
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Coordinates must be finite numbers.")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError(
            "Latitude must be between -90 and 90 and longitude between -180 and 180."
        )
    return latitude, longitude


def kilometers_to_meters(radius_km: float) -> float:
    """Convert a radius in kilometers to meters."""
    if not math.isfinite(radius_km) or radius_km <= 0:
        raise ValueError("Radius must be greater than 0.")
    return radius_km * 1000


def pixel_height(width: int, aspect: float) -> int:
    """Return the pixel height for a width and width/height aspect ratio."""
    if width <= 0:
        raise ValueError("Width must be greater than 0.")
    if not math.isfinite(aspect) or aspect <= 0:
        raise ValueError("Aspect ratio must be greater than 0.")
    return max(1, round(width / aspect))


def framed_bounds(
    left: float,
    bottom: float,
    right: float,
    top: float,
    aspect: float,
) -> tuple[float, float, float, float]:
    """Center-crop bounds so their width divided by height equals ``aspect``."""
    if not math.isfinite(aspect) or aspect <= 0:
        raise ValueError("Aspect ratio must be greater than 0.")
    width = right - left
    height = top - bottom
    if width <= 0 or height <= 0:
        raise ValueError("Bounds must have a positive width and height.")

    center_x = (left + right) / 2
    center_y = (bottom + top) / 2
    if width / height > aspect:
        width = height * aspect
    else:
        height = width / aspect
    return (
        center_x - width / 2,
        center_y - height / 2,
        center_x + width / 2,
        center_y + height / 2,
    )
