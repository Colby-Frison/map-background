"""Download lakes, rivers, and streams around a point."""

from __future__ import annotations

import geopandas as gpd
import osmnx as ox
from osmnx._errors import InsufficientResponseError

WATER_TAGS = {
    "natural": "water",
    "waterway": ["river", "canal", "stream"],
}
_POLYGON_TYPES = ("Polygon", "MultiPolygon")
_LINE_TYPES = ("LineString", "MultiLineString")


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


def split_water(features: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Split features into polygon bodies and linear waterways."""
    geometry_types = features.geometry.geom_type
    polygons = features[geometry_types.isin(_POLYGON_TYPES)]
    lines = features[geometry_types.isin(_LINE_TYPES)]
    return polygons, lines
