"""Command-line interface for map-background."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from map_background.parse import kilometers_to_meters, parse_aspect

NETWORK_TYPES = ("drive", "drive_service", "walk", "bike", "all", "all_private")
DEFAULT_ASPECT = 16 / 9


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser used by the console script."""
    parser = argparse.ArgumentParser(
        prog="map-background",
        description="Create a dark street-map image from OpenStreetMap.",
    )
    parser.add_argument(
        "--location",
        required=True,
        help='Place name, or latitude and longitude as "lat, lon".',
    )
    parser.add_argument(
        "--label",
        help="Corner text. Defaults to the place name, or City, Country for coordinates.",
    )
    parser.add_argument(
        "--radius-km",
        type=_positive_float,
        default=10.0,
        help="Radius around the location, in kilometers (default: 10).",
    )
    parser.add_argument(
        "--network-type",
        choices=NETWORK_TYPES,
        default="all",
        help="Which streets to include. 'all' is the densest and slowest (default: all).",
    )
    parser.add_argument(
        "--width",
        type=_positive_int,
        default=1920,
        help="Image width in pixels. Height is width divided by the aspect ratio (default: 1920).",
    )
    parser.add_argument(
        "--aspect",
        type=parse_aspect,
        default=DEFAULT_ASPECT,
        help="Aspect ratio as 16:9, 4:3, 1:1, or a decimal (default: 16:9).",
    )
    parser.add_argument("--background", type=_color, default="#000000", help="Background color.")
    parser.add_argument("--street-color", type=_color, default="#262626", help="Street color.")
    parser.add_argument("--water-color", type=_color, default="#1b3a4b", help="Water color.")
    parser.add_argument("--label-color", type=_color, default="#6f6f6f", help="Label color.")
    parser.add_argument(
        "--street-width",
        type=_positive_float,
        default=0.4,
        help="Street line width (default: 0.4).",
    )
    parser.add_argument("--no-water", action="store_true", help="Skip water features.")
    parser.add_argument("--no-label", action="store_true", help="Skip the corner label.")
    parser.add_argument(
        "--output",
        type=_output_path,
        default="map.png",
        help="Output file. Use a .png or .svg extension (default: map.png).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, resolve the location, and render the map."""
    args = build_parser().parse_args(argv)

    from map_background.geocode import LocationError, resolve_location
    from map_background.render import MapError, render_map

    need_label = not args.no_label
    try:
        point, label = resolve_location(args.location, label=args.label, need_label=need_label)
    except LocationError as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        render_map(
            point,
            kilometers_to_meters(args.radius_km),
            args.network_type,
            args.width,
            args.aspect,
            Path(args.output),
            background=args.background,
            street_color=args.street_color,
            water_color=args.water_color,
            label_color=args.label_color,
            street_width=args.street_width,
            show_water=not args.no_water,
            label=label,
        )
    except MapError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be a number greater than 0.") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0.")
    return number


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer greater than 0.") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0.")
    return number


def _color(value: str) -> str:
    from matplotlib.colors import is_color_like

    if not is_color_like(value):
        raise argparse.ArgumentTypeError(f"Invalid color: {value}")
    return value


def _output_path(value: str) -> str:
    if Path(value).suffix.lower() not in {".png", ".svg"}:
        raise argparse.ArgumentTypeError("Output must be a .png or .svg file.")
    return value
