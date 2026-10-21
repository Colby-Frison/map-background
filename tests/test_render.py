"""Render tests that do not call Overpass or Nominatim."""

import struct
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pytest
import requests
from shapely.geometry import LineString, Polygon

from map_background.render import MapError, render_map


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        assert image.read(8) == b"\x89PNG\r\n\x1a\n"
        image.read(4)
        assert image.read(4) == b"IHDR"
        return struct.unpack(">II", image.read(8))


def _sample_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(crs="EPSG:4326")
    graph.add_node(1, x=23.72, y=37.97)
    graph.add_node(2, x=23.74, y=37.99)
    graph.add_edge(1, 2)
    return graph


def _sample_water() -> gpd.GeoDataFrame:
    polygon = Polygon(
        [(23.725, 37.975), (23.735, 37.975), (23.735, 37.985), (23.725, 37.985)]
    )
    line = LineString([(23.72, 37.97), (23.74, 37.99)])
    return gpd.GeoDataFrame(geometry=[polygon, line], crs="EPSG:4326")


def test_render_saves_png_at_requested_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "map_background.render.ox.graph.graph_from_point",
        lambda *args, **kwargs: _sample_graph(),
    )
    monkeypatch.setattr("map_background.render.fetch_water", lambda *args, **kwargs: _sample_water())

    output = tmp_path / "map.png"
    render_map(
        (37.98, 23.73),
        1000,
        "drive",
        640,
        16 / 9,
        output,
        background="#000000",
        street_color="#262626",
        water_color="#1b3a4b",
        label_color="#6f6f6f",
        street_width=0.4,
        show_water=True,
        label="Athens, Greece",
    )

    assert _png_size(output) == (640, 360)
    from PIL import Image

    with Image.open(output) as image:
        assert image.getpixel((2, 2))[:3] == (0, 0, 0)
        assert image.getpixel((2, 2))[3] == 255


def test_render_saves_svg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "map_background.render.ox.graph.graph_from_point",
        lambda *args, **kwargs: _sample_graph(),
    )

    output = tmp_path / "map.svg"
    render_map(
        (37.98, 23.73),
        1000,
        "drive",
        640,
        1,
        output,
        background="#000000",
        street_color="#262626",
        water_color="#1b3a4b",
        label_color="#6f6f6f",
        street_width=0.4,
        show_water=False,
        label=None,
    )

    text = output.read_text(encoding="utf-8")
    assert text.lstrip().startswith("<?xml") or "<svg" in text[:200]


def test_render_reports_unreachable_map_server(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr("map_background.render.ox.graph.graph_from_point", fail)
    with pytest.raises(MapError, match="unavailable"):
        render_map(
            (37.98, 23.73),
            1000,
            "drive",
            320,
            16 / 9,
            Path("map.png"),
            background="#000000",
            street_color="#262626",
            water_color="#1b3a4b",
            label_color="#6f6f6f",
            street_width=0.4,
            show_water=False,
            label=None,
        )
