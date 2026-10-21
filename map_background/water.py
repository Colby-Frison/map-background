"""Download water bodies and turn coastlines into filled sea polygons.

OpenStreetMap draws the ocean as directed ``natural=coastline`` lines, with
land on the left and water on the right. Wide rivers are often
``waterway=riverbank`` polygons, or centerlines that carry a ``width`` tag.
"""

from __future__ import annotations

import math
import re

import geopandas as gpd
import pandas as pd
import osmnx as ox
from osmnx._errors import InsufficientResponseError
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

WATER_TAGS = {
    "natural": ["water", "coastline"],
    "waterway": ["river", "canal", "stream", "riverbank", "dock"],
    "landuse": "reservoir",
}
_POLYGON_TYPES = ("Polygon", "MultiPolygon")
_LINE_TYPES = ("LineString", "MultiLineString")
_CENTERLINE_VALUES = ("river", "canal", "stream")
_BANK_VALUES = ("riverbank", "dock")
_WIDE_RIVER_METERS = 15
_WIDTH_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)")


def fetch_water(
    point: tuple[float, float],
    dist_m: float,
) -> gpd.GeoDataFrame | None:
    """Return water features within ``dist_m`` of ``point``, or ``None`` if none exist."""
    try:
        features = ox.features.features_from_point(point, WATER_TAGS, dist=dist_m)
    except InsufficientResponseError:
        return None
    if features is None or features.empty:
        return None
    return features


def prepare_water(
    features: gpd.GeoDataFrame | None,
    clip: Polygon,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Return ``(areas, centerlines)`` ready to draw, in the same CRS as ``features``.

    ``clip`` is the map rectangle in that CRS. Coastlines are polygonized
    against it and only the water side is kept.
    """
    crs = None if features is None else features.crs
    empty = gpd.GeoDataFrame(geometry=[], crs=crs)
    if features is None or features.empty:
        return empty, empty

    areas = features.loc[_is_area(features)].copy()
    banks = _polygons_from_closed_lines(features.loc[_is_bank_line(features)])
    coastlines = features.loc[_is_coastline(features)]
    centerlines = features.loc[_is_centerline(features)].copy()
    thin_lines, wide_rivers = _split_wide_rivers(centerlines)
    sea = sea_from_coastline(coastlines, clip)
    return _concat([areas, banks, wide_rivers, sea], crs), thin_lines


def sea_from_coastline(coastlines: gpd.GeoDataFrame, clip: Polygon) -> gpd.GeoDataFrame:
    """Fill the water side of directed coastline segments inside ``clip``."""
    crs = None if coastlines is None else coastlines.crs
    empty = gpd.GeoDataFrame(geometry=[], crs=crs)
    if coastlines is None or coastlines.empty or clip.is_empty:
        return empty

    pieces = _clipped_lines(coastlines.geometry, clip)
    if not pieces:
        return empty

    water: list[Polygon] = []
    fused = unary_union(pieces + [clip.boundary])
    for polygon in polygonize(fused):
        if polygon.is_empty or not polygon.is_valid or polygon.area <= 1:
            continue
        point = polygon.representative_point()
        if clip.covers(point) and _on_water_side(point, pieces):
            water.append(polygon)
    if not water:
        return empty
    return gpd.GeoDataFrame(geometry=water, crs=crs)


def _is_area(features: gpd.GeoDataFrame) -> pd.Series:
    return features.geometry.geom_type.isin(_POLYGON_TYPES)


def _is_coastline(features: gpd.GeoDataFrame) -> pd.Series:
    return _text(features, "natural").eq("coastline") & features.geometry.geom_type.isin(_LINE_TYPES)


def _is_bank_line(features: gpd.GeoDataFrame) -> pd.Series:
    return _text(features, "waterway").isin(_BANK_VALUES) & features.geometry.geom_type.isin(_LINE_TYPES)


def _is_centerline(features: gpd.GeoDataFrame) -> pd.Series:
    return _text(features, "waterway").isin(_CENTERLINE_VALUES) & features.geometry.geom_type.isin(
        _LINE_TYPES
    )


def _text(features: gpd.GeoDataFrame, column: str) -> pd.Series:
    if column not in features.columns:
        return pd.Series(pd.NA, index=features.index, dtype="object")
    return features[column]


def _polygons_from_closed_lines(features: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    polygons: list[Polygon] = []
    if features is not None and not features.empty:
        for geometry in features.geometry:
            polygons.extend(_closed_polygons(geometry))
    return gpd.GeoDataFrame(geometry=polygons, crs=None if features is None else features.crs)


def _closed_polygons(geometry: BaseGeometry | None) -> list[Polygon]:
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        line = geometry
        if line.is_closed and len(line.coords) >= 4:
            polygon = Polygon(line)
            if polygon.is_valid and polygon.area > 0:
                return [polygon]
        return []
    if geometry.geom_type == "MultiLineString":
        polygons: list[Polygon] = []
        for part in geometry.geoms:
            polygons.extend(_closed_polygons(part))
        return polygons
    return []


def _split_wide_rivers(lines: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Buffer centerlines that declare a width, and keep the rest as strokes."""
    crs = lines.crs
    if lines.empty:
        return lines, gpd.GeoDataFrame(geometry=[], crs=crs)

    buffers: list[Polygon] = []
    keep: list[int] = []
    has_width = "width" in lines.columns
    for index, row in lines.iterrows():
        width = _width_meters(row["width"]) if has_width else None
        geometry = row.geometry
        if width is not None and geometry is not None and not geometry.is_empty:
            buffers.append(geometry.buffer(width / 2))
        else:
            keep.append(index)
    wide = gpd.GeoDataFrame(geometry=buffers, crs=crs)
    thin = lines.loc[keep]
    return thin, wide


def _width_meters(value: object) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    match = _WIDTH_PATTERN.search(str(value))
    if match is None:
        return None
    width = float(match.group(1))
    if width < _WIDE_RIVER_METERS or width > 5000:
        return None
    return width


def _clipped_lines(geometries: gpd.GeoSeries, clip: Polygon) -> list[LineString]:
    pieces: list[LineString] = []
    for geometry in geometries:
        if geometry is None or geometry.is_empty:
            continue
        pieces.extend(_line_parts(geometry.intersection(clip)))
    return pieces


def _line_parts(geometry: BaseGeometry) -> list[LineString]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        line = geometry
        return [line] if len(line.coords) >= 2 else []
    if geometry.geom_type in {"MultiLineString", "GeometryCollection"}:
        parts: list[LineString] = []
        for part in geometry.geoms:
            parts.extend(_line_parts(part))
        return parts
    return []


def _on_water_side(point: BaseGeometry, lines: list[LineString]) -> bool:
    """Return whether ``point`` sits to the right of the nearest coastline.

    Coastline ways are directed so that water is on the right.
    """
    nearest = min(lines, key=lambda line: line.distance(point))
    length = nearest.length
    if length == 0:
        return False
    distance = nearest.project(point)
    step = min(1.0, length / 2)
    start = max(0.0, distance - step)
    end = min(length, distance + step)
    if end <= start:
        return False
    origin = nearest.interpolate(start)
    ahead = nearest.interpolate(end)
    dx = ahead.x - origin.x
    dy = ahead.y - origin.y
    cross = dx * (point.y - origin.y) - dy * (point.x - origin.x)
    return cross < 0


def _concat(frames: list[gpd.GeoDataFrame], crs) -> gpd.GeoDataFrame:
    filled = [frame for frame in frames if frame is not None and not frame.empty]
    if not filled:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    combined = pd.concat(filled, ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=crs)
