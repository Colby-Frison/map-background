"""Failover across public Overpass servers. These tests do not use the network."""

import pytest
import requests
from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError

from map_background.overpass import (
    OVERPASS_ENDPOINTS,
    MapServerError,
    call_overpass,
    reset_overpass_preference,
)


@pytest.fixture(autouse=True)
def _clear_preferred_server() -> None:
    reset_overpass_preference()


def test_failover_uses_the_next_server() -> None:
    attempts: list[str] = []

    def action() -> str:
        from osmnx import settings

        attempts.append(settings.overpass_url)
        if len(attempts) == 1:
            raise ResponseStatusCodeError("502")
        return "ok"

    assert call_overpass(action, "Downloading streets") == "ok"
    assert attempts == [OVERPASS_ENDPOINTS[0], OVERPASS_ENDPOINTS[1]]


def test_later_download_starts_at_the_server_that_worked() -> None:
    def fail_then_succeed() -> str:
        from osmnx import settings

        if settings.overpass_url == OVERPASS_ENDPOINTS[0]:
            raise requests.ConnectionError("down")
        return "ok"

    call_overpass(fail_then_succeed, "Downloading streets")

    attempts: list[str] = []

    def record() -> str:
        from osmnx import settings

        attempts.append(settings.overpass_url)
        return "ok"

    call_overpass(record, "Downloading water")
    assert attempts == [OVERPASS_ENDPOINTS[1]]


def test_every_server_unavailable() -> None:
    def fail() -> None:
        raise requests.ConnectionError("down")

    with pytest.raises(MapServerError, match="unavailable"):
        call_overpass(fail, "Downloading streets")


def test_empty_map_data_is_not_treated_as_a_down_server() -> None:
    attempts = 0

    def empty() -> None:
        nonlocal attempts
        attempts += 1
        raise InsufficientResponseError("none")

    with pytest.raises(InsufficientResponseError):
        call_overpass(empty, "Downloading streets")
    assert attempts == 1
