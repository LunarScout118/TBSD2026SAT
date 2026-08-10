from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import osmnx as ox


# Roads are drawn from smallest to largest so major roads appear on top.
ROAD_STYLES = {
    "other": {
        "colour": "#555555",
        "width": 0.20,
        "zorder": 1,
    },
    "service": {
        "colour": "#666666",
        "width": 0.25,
        "zorder": 2,
    },
    "residential": {
        "colour": "#8a8a8a",
        "width": 0.35,
        "zorder": 3,
    },
    "unclassified": {
        "colour": "#999999",
        "width": 0.40,
        "zorder": 4,
    },
    "tertiary": {
        "colour": "#f4d35e",
        "width": 0.65,
        "zorder": 5,
    },
    "secondary": {
        "colour": "#ee964b",
        "width": 0.90,
        "zorder": 6,
    },
    "primary": {
        "colour": "#f95738",
        "width": 1.20,
        "zorder": 7,
    },
    "trunk": {
        "colour": "#d7263d",
        "width": 1.60,
        "zorder": 8,
    },
    "motorway": {
        "colour": "#7b2cbf",
        "width": 2.10,
        "zorder": 9,
    },
}


def classify_highway(value: Any) -> str:
    """
    Convert an OSM highway value into one of our display classes.

    OSMnx may return a single string or a list of values for an edge.
    Link roads such as motorway_link are grouped with their parent road.
    """
    if isinstance(value, (list, tuple, set)):
        values = [str(item) for item in value]
    elif value is None:
        values = []
    else:
        values = [str(value)]

    priority = [
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "unclassified",
        "residential",
        "service",
    ]

    normalised = {
        item.removesuffix("_link")
        for item in values
    }

    for road_class in priority:
        if road_class in normalised:
            return road_class

    return "other"


def create_road_svg(
    place: str,
    output_path: Path,
    background: str = "#111111",
) -> None:
    print(f"Downloading roads for: {place}")

    # "drive" excludes footpaths and focuses on drivable roads.
    graph = ox.graph.graph_from_place(
        place,
        network_type="drive",
        simplify=True,
        retain_all=False,
    )

    # Convert latitude/longitude into a projected coordinate system.
    # This makes the map shape and road widths more sensible.
    graph = ox.projection.project_graph(graph)

    _, edges = ox.convert.graph_to_gdfs(
        graph,
        nodes=True,
        edges=True,
        fill_edge_geometry=True,
    )

    edges["road_class"] = edges["highway"].apply(classify_highway)

    fig, ax = plt.subplots(
        figsize=(12, 12),
        facecolor=background,
    )
    ax.set_facecolor(background)

    for road_class, style in ROAD_STYLES.items():
        subset = edges[edges["road_class"] == road_class]

        if subset.empty:
            continue

        subset.plot(
            ax=ax,
            color=style["colour"],
            linewidth=style["width"],
            zorder=style["zorder"],
        )

    ax.set_axis_off()
    ax.set_aspect("equal")

    # Visible OSM attribution.
    attribution = fig.text(
        0.995,
        0.005,
        "© OpenStreetMap contributors",
        horizontalalignment="right",
        verticalalignment="bottom",
        fontsize=5,
        color="#aaaaaa",
    )
    attribution.set_url("https://www.openstreetmap.org/copyright")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        output_path,
        format="svg",
        bbox_inches="tight",
        pad_inches=0,
        facecolor=background,
        metadata={
            "Title": f"Road map of {place}",
            "Creator": "road_svg.py",
            "Description": "Map data © OpenStreetMap contributors",
        },
    )

    plt.close(fig)
    print(f"Saved SVG to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a coloured SVG road map from OpenStreetMap."
    )
    parser.add_argument(
        "place",
        help='Place name, for example "Melbourne, Victoria, Australia"',
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Output SVG filename",
    )
    parser.add_argument(
        "--background",
        default="#111111",
        help="Background colour, such as #111111 or white",
    )

    args = parser.parse_args()

    try:
        create_road_svg(
            place=args.place,
            output_path=args.output,
            background=args.background,
        )
    except Exception as error:
        raise SystemExit(f"Could not create map: {error}") from error


if __name__ == "__main__":
    main()