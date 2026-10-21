"""Download OpenStreetMap data from the first public Overpass server that answers.

The default server, overpass-api.de, is often full. OSMnx will pause and retry
that same server. These helpers turn that wait off and move to another public
server as soon as one refuses the connection.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
from urllib.parse import urlparse

import requests
from osmnx import _http, _overpass, settings
from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError

# Private.coffee and VK Maps publish global coverage without a rate limit.
# The FOSSGIS server is last because it is frequently at capacity.
OVERPASS_ENDPOINTS = (
    "https://overpass.private.coffee/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
    "https://overpass-api.de/api",
)
CONNECT_TIMEOUT = 10

_T = TypeVar("_T")
_preferred: str | None = None
_installed = False


class MapServerError(Exception):
    """Every public Overpass server failed for this download."""


def call_overpass(action: Callable[[], _T], description: str) -> _T:
    """Run ``action`` against each server until one returns data.

    ``InsufficientResponseError`` is not a server failure. It means the area
    has no matching map data, so another server is not asked.
    """
    _install_fail_fast()
    failures: list[str] = []
    for endpoint in _endpoint_order():
        host = urlparse(endpoint).netloc
        settings.overpass_url = endpoint
        print(f"{description} from {host}...", flush=True)
        try:
            result = action()
        except InsufficientResponseError:
            raise
        except (ResponseStatusCodeError, requests.RequestException, OSError) as exc:
            print(f"{host} is unavailable ({_short_reason(exc)}), trying another server.", flush=True)
            failures.append(host)
            continue
        _remember(endpoint)
        return result

    tried = ", ".join(failures)
    raise MapServerError(f"Every public map server was unavailable ({tried}).")


def reset_overpass_preference() -> None:
    """Forget which server last succeeded. Used by tests."""
    global _preferred
    _preferred = None


def _endpoint_order() -> tuple[str, ...]:
    if _preferred is None:
        return OVERPASS_ENDPOINTS
    return (_preferred, *[endpoint for endpoint in OVERPASS_ENDPOINTS if endpoint != _preferred])


def _remember(endpoint: str) -> None:
    global _preferred
    _preferred = endpoint


def _install_fail_fast() -> None:
    """Replace OSMnx's request so a busy server does not trigger a long pause."""
    global _installed
    settings.overpass_rate_limit = False
    settings.http_user_agent = "map-background/1.0"
    settings.http_referer = "map-background/1.0"
    if _installed:
        return
    _overpass._overpass_request = _overpass_request_fail_fast
    _installed = True


def _short_reason(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        return "timed out"
    if isinstance(exc, requests.ConnectionError):
        return "connection failed"
    text = str(exc).splitlines()[0].strip()
    if len(text) > 120:
        text = text[:117] + "..."
    return text or type(exc).__name__


def _overpass_request_fail_fast(data: dict) -> dict:
    """POST one Overpass query and return its JSON, using the OSMnx cache.

    A 4xx or 5xx response raises immediately. OSMnx would otherwise sleep and
    retry the same host, including on HTTP 429 and 504.
    """
    url = settings.overpass_url.rstrip("/") + "/interpreter"
    prepared_url = str(requests.Request("GET", url, params=data).prepare().url)
    cached = _http._retrieve_from_cache(prepared_url)
    if isinstance(cached, dict):
        return cached

    response = requests.post(
        url,
        data=data,
        timeout=(CONNECT_TIMEOUT, settings.requests_timeout),
        headers=_http._get_http_headers(),
        **settings.requests_kwargs,
    )
    host = urlparse(url).netloc
    if response.status_code >= 400:
        raise ResponseStatusCodeError(f"{host} responded {response.status_code} {response.reason}")

    response_json = _http._parse_response(response)
    if not isinstance(response_json, dict):
        raise InsufficientResponseError("The map server did not return map data.")
    _http._save_to_cache(prepared_url, response_json, response.ok)
    return response_json
