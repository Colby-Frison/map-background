# Map Background

Create a dark street map from OpenStreetMap. Streets are drawn in grey on a black background, and water is drawn in a muted blue. The image is saved at the pixel size you ask for, 1920x1080 by default.

## Install

Python 3.11 or newer.

```bash
pip install -r requirements.txt
pip install -e .
```

To run the tests as well:

```bash
pip install -e ".[dev]"
```

## Usage

```bash
map-background --location "Athens, Greece"
```

The same command works as `python -m map_background --location "Athens, Greece"`.

Coordinates are accepted too. Without `--label`, they are reverse-geocoded to a `City, Country` name:

```bash
map-background --location "37.9838, 23.7275" --label "Athens, Greece"
```

A smaller, faster map:

```bash
map-background --location "Athens, Greece" --radius-km 3 --network-type drive --output athens.png
```

### Options

- `--location` is a place name or `lat, lon`. It is required.
- `--radius-km` is the radius in kilometers. The default is 10, which is 10,000 meters. The previous prompt treated a typed number as meters even though it asked for kilometers.
- `--network-type` is one of `drive`, `drive_service`, `walk`, `bike`, `all`, or `all_private`. The default is `all`, which includes footpaths and service roads. That option is the slowest. `drive` is much faster.
- `--aspect` accepts `16:9`, `4:3`, `1:1`, or a positive number such as `1.5`. The default is `16:9`.
- `--width` is the image width in pixels. The default is 1920. Height is the width divided by the aspect ratio, so the default image is 1920x1080.
- `--background`, `--street-color`, `--water-color`, and `--label-color` take any color Matplotlib accepts. Defaults are `#000000`, `#262626`, `#1b3a4b`, and `#6f6f6f`.
- `--street-width` is the street line width. The default is 0.4.
- `--no-water` skips lakes, coastlines, rivers, canals, and streams. Water is included by default.
- `--label` replaces the corner text. `--no-label` removes it.
- `--output` is the file to write. The extension chooses the format: `.png` or `.svg`. The default is `map.png`.

Example with custom colors:

```bash
map-background --location "Venice, Italy" --street-color "#3a3a3a" --water-color "#163044"
```

OSMnx keeps downloaded data in your user cache directory, so generating the same area again is faster.

![map](https://github.com/user-attachments/assets/3edd3adb-c42b-4dca-962a-c862ab57d572)
