"""Draw a projected street map and save it as a PNG or SVG."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import osmnx as ox
import requests
from matplotlib import patheffects
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError

from map_background.parse import framed_bounds, pixel_height
from map_background.water import fetch_water, split_water

SAVE_DPI = 100
WATER_LINE_WIDTH = 0.8


class MapError(Exception):
    """The map could not be downloaded or drawn."""


def render_map(
    point: tuple[float, float],
    radius_m: float,
    network_type: str,
    width: int,
    aspect: float,
    output: Path,
    *,
    background: str,
    street_color: str,
    water_color: str,
    label_color: str,
    street_width: float,
    show_water: bool,
    label: str | None,
) -> Path:
    """Download streets (and water), draw them, and save ``output``."""
    height = pixel_height(width, aspect)
    graph = _street_graph(point, radius_m, network_type)
    graph = ox.projection.project_graph(graph)
    water = _water_features(point, radius_m, graph.graph["crs"]) if show_water else None

    figure, axes = plt.subplots(
        figsize=(width / SAVE_DPI, height / SAVE_DPI),
        facecolor=background,
        frameon=False,
    )
    axes.set_facecolor(background)
    try:
        _draw_water(axes, water, water_color)
        ox.plot.plot_graph(
            graph,
            ax=axes,
            node_size=0,
            edge_color=street_color,
            edge_linewidth=street_width,
            edge_alpha=1,
            bgcolor=background,
            show=False,
            close=False,
        )
        _frame_axes(axes, aspect)
        if label:
            _draw_label(axes, label, label_color)
        _save(figure, axes, output, background)
    finally:
        plt.close(figure)

    print(f"Saved {output} ({width}x{height})", flush=True)
    return output


def _street_graph(point: tuple[float, float], radius_m: float, network_type: str):
    print(f"Downloading streets ({network_type}, {radius_m / 1000:g} km radius)...", flush=True)
    try:
        graph = ox.graph.graph_from_point(point, dist=radius_m, network_type=network_type)
    except InsufficientResponseError as exc:
        raise MapError(
            "No streets found there. Try a larger radius or a different network type."
        ) from exc
    except ResponseStatusCodeError as exc:
        raise MapError(f"The map server returned an error: {exc}") from exc
    except requests.RequestException as exc:
        raise MapError("Could not reach the map server. Try again in a moment.") from exc
    if graph.number_of_edges() == 0:
        raise MapError(
            "No streets found there. Try a larger radius or a different network type."
        )
    return graph


def _water_features(point: tuple[float, float], radius_m: float, crs):
    print("Downloading water...", flush=True)
    try:
        features = fetch_water(point, radius_m)
    except ResponseStatusCodeError as exc:
        raise MapError(f"The map server returned an error: {exc}") from exc
    except requests.RequestException as exc:
        raise MapError("Could not reach the map server. Try again in a moment.") from exc
    if features is None:
        print("No water features in this area.", flush=True)
        return None
    return ox.projection.project_gdf(features, to_crs=crs)


def _draw_water(axes: Axes, features, water_color: str) -> None:
    if features is None:
        return
    polygons, lines = split_water(features)
    if not polygons.empty:
        polygons.plot(ax=axes, facecolor=water_color, edgecolor="none", zorder=0)
    if not lines.empty:
        lines.plot(ax=axes, color=water_color, linewidth=WATER_LINE_WIDTH, zorder=0)


def _frame_axes(axes: Axes, aspect: float) -> None:
    left, right = axes.get_xlim()
    bottom, top = axes.get_ylim()
    framed = framed_bounds(left, bottom, right, top, aspect)
    axes.set_xlim(framed[0], framed[2])
    axes.set_ylim(framed[1], framed[3])
    axes.set_aspect("equal")
    axes.set_axis_off()
    axes.set_position((0, 0, 1, 1))


def _draw_label(axes: Axes, label: str, color: str) -> None:
    axes.text(
        0.985,
        0.97,
        label,
        transform=axes.transAxes,
        ha="right",
        va="top",
        color=color,
        fontsize=12,
        zorder=3,
        path_effects=[patheffects.withStroke(linewidth=2, foreground="black")],
    )


def _save(figure: Figure, axes: Axes, output: Path, background: str) -> None:
    # Plotting can leave the axes patch transparent. Set the color first, then
    # force the patches opaque so the background fills the whole image.
    figure.set_frameon(True)
    figure.patch.set_facecolor(background)
    figure.patch.set_alpha(1)
    axes.set_facecolor(background)
    axes.patch.set_alpha(1)
    figure.subplots_adjust(left=0, right=1, bottom=0, top=1)
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix == ".png":
        figure.savefig(
            output,
            dpi=SAVE_DPI,
            facecolor=background,
            edgecolor="none",
            transparent=False,
        )
    elif suffix == ".svg":
        figure.savefig(
            output,
            format="svg",
            facecolor=background,
            edgecolor="none",
            transparent=False,
        )
    else:
        raise MapError("Output must be a .png or .svg file.")
