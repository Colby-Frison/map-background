"""Resolve a place name or coordinate pair to a map center and label."""

from __future__ import annotations

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

from map_background.parse import parse_coordinates

USER_AGENT = "map-background"
_GEOCODER_TIMEOUT = 10
_LOCALITY_KEYS = ("city", "town", "village", "municipality", "hamlet")


class LocationError(Exception):
    """The place could not be resolved."""


def resolve_location(
    location: str,
    *,
    label: str | None,
    need_label: bool,
) -> tuple[tuple[float, float], str | None]:
    """Return ``((latitude, longitude), label)`` for a CLI location string.

    Coordinate input is reverse-geocoded to ``City, Country`` only when a
    label is needed and ``--label`` was not passed. Place names keep the
    text the user typed.
    """
    try:
        coordinates = parse_coordinates(location)
    except ValueError as exc:
        raise LocationError(str(exc)) from exc

    if coordinates is not None:
        if not need_label:
            return coordinates, None
        if label:
            return coordinates, label
        return coordinates, _reverse_label(coordinates)

    point = _geocode_place(location)
    if not need_label:
        return point, None
    return point, label or location.strip()


def _geolocator() -> Nominatim:
    return Nominatim(user_agent=USER_AGENT, timeout=_GEOCODER_TIMEOUT)


def _geocode_place(location: str) -> tuple[float, float]:
    try:
        found = _geolocator().geocode(location)
    except GeocoderTimedOut as exc:
        raise LocationError("Geocoding service timed out. Try again in a moment.") from exc
    except GeocoderServiceError as exc:
        raise LocationError(f"Geocoding service failed: {exc}") from exc
    if found is None:
        raise LocationError(f"Location not found: {location}")
    return found.latitude, found.longitude


def _reverse_label(coordinates: tuple[float, float]) -> str:
    try:
        found = _geolocator().reverse(coordinates, language="en")
    except GeocoderTimedOut as exc:
        raise LocationError("Geocoding service timed out. Try again in a moment.") from exc
    except GeocoderServiceError as exc:
        raise LocationError(f"Geocoding service failed: {exc}") from exc
    if found is None:
        raise LocationError(
            "Could not find a name for those coordinates. Pass --label to set one."
        )
    address = found.raw.get("address", {})
    label = _city_country(address)
    if label is None:
        raise LocationError(
            "Could not determine a city name for those coordinates. Pass --label to set one."
        )
    return label


def _city_country(address: dict) -> str | None:
    country = address.get("country")
    if not country:
        return None
    for key in _LOCALITY_KEYS:
        name = address.get(key)
        if name:
            return f"{name}, {country}"
    return None
