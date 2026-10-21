"""Tests for command-line parsing. These do not download map data."""

import argparse

import pytest

from map_background.cli import build_parser
from map_background.geocode import _city_country
from map_background.parse import (
    framed_bounds,
    kilometers_to_meters,
    parse_aspect,
    parse_coordinates,
    pixel_height,
)


def test_parse_aspect_ratio() -> None:
    assert parse_aspect("16:9") == pytest.approx(16 / 9)
    assert parse_aspect("4:3") == pytest.approx(4 / 3)
    assert parse_aspect("1:1") == 1
    assert parse_aspect("1.5") == 1.5


def test_parse_aspect_rejects_invalid_values() -> None:
    for value in ("nope", "16:9:1", "0:9", "-1", "0"):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_aspect(value)


def test_parse_coordinates() -> None:
    assert parse_coordinates("37.9838, 23.7275") == (37.9838, 23.7275)
    assert parse_coordinates("37.9838,23.7275") == (37.9838, 23.7275)
    assert parse_coordinates("-33.8688, 151.2093") == (-33.8688, 151.2093)
    assert parse_coordinates("Athens, Greece") is None


def test_parse_coordinates_rejects_out_of_range_pairs() -> None:
    with pytest.raises(ValueError):
        parse_coordinates("91, 0")
    with pytest.raises(ValueError):
        parse_coordinates("0, 181")


def test_kilometers_to_meters() -> None:
    assert kilometers_to_meters(10) == 10_000
    assert kilometers_to_meters(18) == 18_000
    with pytest.raises(ValueError):
        kilometers_to_meters(0)


def test_pixel_height_matches_common_ratios() -> None:
    assert pixel_height(1920, 16 / 9) == 1080
    assert pixel_height(1920, 4 / 3) == 1440
    assert pixel_height(1920, 1) == 1920


def test_framed_bounds_center_crops_to_aspect() -> None:
    left, bottom, right, top = framed_bounds(0, 0, 200, 100, 1)
    assert right - left == pytest.approx(100)
    assert top - bottom == pytest.approx(100)
    assert (left + right) / 2 == pytest.approx(100)
    assert (bottom + top) / 2 == pytest.approx(50)

    left, bottom, right, top = framed_bounds(0, 0, 100, 200, 16 / 9)
    assert (right - left) / (top - bottom) == pytest.approx(16 / 9)
    assert (left + right) / 2 == pytest.approx(50)


def test_parser_converts_aspect_and_radius() -> None:
    args = build_parser().parse_args(
        ["--location", "Athens, Greece", "--aspect", "4:3", "--radius-km", "2.5"]
    )
    assert args.aspect == pytest.approx(4 / 3)
    assert args.radius_km == 2.5
    assert args.network_type == "all"
    assert args.width == 1920
    assert args.output == "map.png"
    assert args.no_water is False


def test_parser_rejects_bad_output_and_aspect() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--location", "Athens", "--aspect", "wide"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--location", "Athens", "--output", "map.jpg"])


def test_city_country_label() -> None:
    assert _city_country({"city": "Athens", "country": "Greece"}) == "Athens, Greece"
    assert _city_country({"town": "Delphi", "country": "Greece"}) == "Delphi, Greece"
    assert _city_country({"country": "Greece"}) is None
