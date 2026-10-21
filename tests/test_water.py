"""Water geometry tests. These do not download map data."""

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon, box

from map_background.water import prepare_water, sea_from_coastline


def _covers(frame: gpd.GeoDataFrame, x: float, y: float) -> bool:
    return bool(frame.union_all().covers(Point(x, y)))


def _lines(geometries: list) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"natural": ["coastline"] * len(geometries)}, geometry=geometries)


def test_northbound_coastline_fills_the_eastern_water() -> None:
    clip = box(0, 0, 100, 100)
    sea = sea_from_coastline(_lines([LineString([(50, 0), (50, 100)])]), clip)

    assert _covers(sea, 75, 50)
    assert not _covers(sea, 25, 50)


def test_southbound_coastline_fills_the_western_water() -> None:
    clip = box(0, 0, 100, 100)
    sea = sea_from_coastline(_lines([LineString([(50, 100), (50, 0)])]), clip)

    assert _covers(sea, 25, 50)
    assert not _covers(sea, 75, 50)


def test_island_coastline_leaves_the_interior_as_land() -> None:
    clip = box(0, 0, 100, 100)
    # Counterclockwise ring: land is on the left, so the interior is land.
    island = LineString([(40, 40), (60, 40), (60, 60), (40, 60), (40, 40)])
    sea = sea_from_coastline(_lines([island]), clip)

    assert _covers(sea, 10, 10)
    assert not _covers(sea, 50, 50)


def test_closed_riverbank_and_wide_centerline_become_areas() -> None:
    bank = LineString([(0, 0), (30, 0), (30, 10), (0, 10), (0, 0)])
    river = LineString([(0, 50), (100, 50)])
    features = gpd.GeoDataFrame(
        {"waterway": ["riverbank", "river"], "width": [None, "40"]},
        geometry=[bank, river],
    )

    areas, lines = prepare_water(features, box(-10, -10, 120, 80))

    assert lines.empty
    assert _covers(areas, 15, 5)
    assert _covers(areas, 50, 50)
    assert not _covers(areas, 50, 80)


def test_narrow_stream_stays_a_line() -> None:
    stream = LineString([(0, 0), (10, 0)])
    features = gpd.GeoDataFrame(
        {"waterway": ["stream"], "width": ["2"]},
        geometry=[stream],
    )

    areas, lines = prepare_water(features, box(-5, -5, 15, 5))

    assert areas.empty
    assert len(lines) == 1


def test_lake_polygon_is_kept() -> None:
    lake = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    features = gpd.GeoDataFrame({"natural": ["water"]}, geometry=[lake])

    areas, lines = prepare_water(features, box(-5, -5, 20, 20))

    assert lines.empty
    assert _covers(areas, 5, 5)
