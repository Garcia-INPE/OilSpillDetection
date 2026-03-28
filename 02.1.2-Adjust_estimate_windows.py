#!/usr/bin/env python3
"""02.1.2-Adjust_estimate_windows.py

Manual window editing toolbox for a single image.

This script is intentionally stateful through JSON updates:
- It reads window positions from dataout/02.1-DS_by_manual_windows/800x600_windows/1/Created_windows.json (source,
  read-only) as a starting point.
- All adjustments are saved to a separate dataout/02.1-DS_by_manual_windows/800x600_windows/2/Adjusted_windows.json so
  the 02.1.1 output is never modified.
- Every move operation can automatically re-plot the image for quick feedback.

How to use (typical flow):
1) Set IMAGE_ID, WINDOW_WIDTH, WINDOW_HEIGHT below.
2) Call move/check/plot helpers directly.
3) The script auto-registers IMAGE_ID in JSON on first use.

All window IDs in this script are 1-based (W1, W2, ...).
"""

import os
import sys
import argparse
import inspect
import json
import importlib.util
import re
import glob
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from shapely.geometry import box
from shapely.ops import unary_union


SCRIPT_DIR = (
    os.path.dirname(os.path.abspath(__file__))
    if "__file__" in globals()
    else os.path.join(os.getcwd(), "src")
    if os.path.basename(os.getcwd()) != "src"
    else os.getcwd()
)


def _parse_int_list(raw):
    """Parse a comma-separated integer list from CLI input.

    Args:
        raw (str): Comma-separated integers, for example 1,2,3.

    Returns:
        list[int]: Parsed integer values.

    Raises:
        ValueError: If the input is empty or any token is not an integer.
    """
    values = [p.strip() for p in raw.split(",") if p.strip()]
    if not values:
        raise ValueError("Expected a non-empty comma-separated integer list")
    return [int(v) for v in values]


_DIRECTION_ALIASES = {
    "l": "left",
    "r": "right",
    "t": "top",
    "b": "bottom",
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
}


def _normalize_direction_token(raw_value, allowed_values):
    """Normalize one directional token and validate accepted values.

    Supports single-letter aliases for directions while returning canonical
    full-word values used by the internal functions.

    Args:
        raw_value (str): Raw CLI token.
        allowed_values (set[str]): Canonical accepted values.

    Returns:
        str: Canonical token.

    Raises:
        argparse.ArgumentTypeError: If the token is not recognized.
    """
    token = str(raw_value).strip().lower()
    token = _DIRECTION_ALIASES.get(token, token)
    allowed = {str(v).strip().lower() for v in allowed_values}
    if token not in allowed:
        accepted = sorted(allowed)
        raise argparse.ArgumentTypeError(
            f"Invalid value '{raw_value}'. Expected one of: {', '.join(accepted)} "
            f"or aliases l/r/t/b/n/s/e/w where applicable."
        )
    return token


# -----------------------------------------------------------------------------
# User configuration (edit these values manually)
# -----------------------------------------------------------------------------
DEFAULT_IMAGE_ID = 26
DEFAULT_WINDOW_WIDTH = 800
DEFAULT_WINDOW_HEIGHT = 600
DEFAULT_FOCUS_MARGIN = 0.10

IMAGE_ID = DEFAULT_IMAGE_ID
WINDOW_WIDTH = DEFAULT_WINDOW_WIDTH
WINDOW_HEIGHT = DEFAULT_WINDOW_HEIGHT
FOCUS_MARGIN = DEFAULT_FOCUS_MARGIN

def _default_json_in_path(width, height):
    """Build the source (read-only) JSON path produced by 02.1.

    Args:
        width (int): Window width in pixels.
        height (int): Window height in pixels.

    Returns:
        str: Path to the 02.1 preprocessed windows JSON under dataout.
    """
    return os.path.join(
        "dataout",
        "02.1-DS_by_manual_windows",
        f"{width}x{height}_windows",
        "1",
        "Created_windows.json",
    )


def _default_json_path(width, height):
    """Build the output JSON path where 02.2 adjustments are saved.

    Args:
        width (int): Window width in pixels.
        height (int): Window height in pixels.

    Returns:
        str: Path to the 02.2 adjusted windows JSON under dataout.
    """
    return os.path.join(
        "dataout",
        "02.1-DS_by_manual_windows",
        f"{width}x{height}_windows",
        "2",
        "Adjusted_windows.json",
    )


def _default_out_dir(width, height):
    """Build default output directory suffixed with window size.

    Args:
        width (int): Window width in pixels.
        height (int): Window height in pixels.

    Returns:
        str: Default output directory under dataout.
    """
    return os.path.join(
        "dataout",
        "02.1-DS_by_manual_windows",
        f"{width}x{height}_windows",
        "2",
    )


JSON_IN_PATH = _default_json_in_path(WINDOW_WIDTH, WINDOW_HEIGHT)
JSON_PATH = _default_json_path(WINDOW_WIDTH, WINDOW_HEIGHT)
DIR_OUT = _default_out_dir(WINDOW_WIDTH, WINDOW_HEIGHT)
os.makedirs(DIR_OUT, exist_ok=True)

AUTO_PLOT_AFTER_MOVE = True
GLOBAL_BBOX_FILENAME = "00-GLOBAL_BBOX_ZOOM.png"
CURRENT_FOCUS_FILENAME = "00-CURRENT_FOCUS_WINDOW.png"

LAND_PATH = os.path.join(
    os.path.expanduser("~"),
    "ProjData",
    "Oil_Spill",
    "Cantarell_Beisl",
    "Vetores",
    "Coastline",
    "Land_&_Coastline.shp",
)


# -----------------------------------------------------------------------------
# Shared data loaders
# -----------------------------------------------------------------------------
os.chdir(SCRIPT_DIR)
import Config as Cfg  # noqa: E402  # nopep8


def _load_024_module():
    """Load the plotting helper module as an importable module.

    Returns:
        types.ModuleType: Loaded module exposing select_non_overlapping_windows.
    """
    spec = importlib.util.spec_from_file_location(
        "plot_windows",
        "Fun_plot_tiff_with_polygons.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MOD024 = _load_024_module()


def _build_id_to_tiff_path():
    """Build an image-id to TIFF-path dictionary from Config.

    Returns:
        dict[int, str]: Mapping of integer image ID to absolute TIFF path.
    """
    mapping = {}
    for path in Cfg.FNAMES_TIF:
        bname = os.path.basename(path)
        mapping[int(bname.split(" ")[0])] = path
    return mapping


ID_TO_TIFF = _build_id_to_tiff_path()


# -----------------------------------------------------------------------------
# JSON helpers
# -----------------------------------------------------------------------------

def _load_json():
    """Load the manual windows JSON payload.

    If the 02.2 adjusted JSON exists it is used as the source (preserving
    previous edits). Otherwise the 02.1 preprocessed JSON is loaded as the
    starting point. The 02.1 source is never written by this script.

    Returns:
        dict: JSON structure with at least an images key.
    """
    path = JSON_PATH if os.path.exists(JSON_PATH) else JSON_IN_PATH
    if not os.path.exists(path):
        return {"images": {}}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("images", {})
    return data


def _save_json(data):
    """Write the manual windows JSON payload in stable image-id order.

    Args:
        data (dict): JSON payload containing an images dictionary.

    Returns:
        None
    """
    data["images"] = {
        k: data["images"][k]
        for k in sorted(data["images"].keys(), key=lambda x: int(x))
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)
        f.write("\n")


def _get_image_entry(data, image_id, create=False):
    """Get one image entry from the JSON payload.

    Args:
        data (dict): JSON payload.
        image_id (int): Image ID to retrieve.
        create (bool): If True, create an empty entry when missing.

    Returns:
        dict | None: Image entry dictionary, or None when missing and create is False.
    """
    key = str(image_id)
    if key not in data["images"] and create:
        data["images"][key] = {
            "n_polygons": 0,
            "n_windows": 0,
            "windows": {},
        }
    return data["images"].get(key)


def _sorted_window_keys(entry):
    """Return window keys sorted by numeric value.

    Args:
        entry (dict): Image entry containing a windows dictionary.

    Returns:
        list[str]: Sorted window keys.
    """
    return sorted(entry["windows"].keys(), key=lambda x: int(x))


def _window_key_from_id(window_id):
    """Convert a 1-based window ID to its 0-based JSON key.

    Args:
        window_id (int): 1-based window label (W1, W2, ...).

    Returns:
        str: 0-based JSON key string.

    Raises:
        ValueError: If window_id cannot be converted to an integer.
    """
    return str(int(window_id) - 1)


def _next_window_key(entry):
    """Compute the next available window key for insertion.

    Args:
        entry (dict): Image entry containing windows.

    Returns:
        str: Next 0-based key as string.
    """
    if not entry["windows"]:
        return "0"
    return str(max(int(k) for k in entry["windows"].keys()) + 1)


def _ensure_src_and_gdf(image_id):
    """Open raster and load matching vectors for one image ID.

    Args:
        image_id (int): Target image ID.

    Returns:
        tuple: (rasterio.DatasetReader, geopandas.GeoDataFrame) where vectors
            are projected to the raster CRS.

    Raises:
        ValueError: If image_id is not present in Config.FNAMES_TIF.
    """
    if image_id not in ID_TO_TIFF:
        raise ValueError(f"Image ID {image_id} not found in Config.FNAMES_TIF")
    src = rasterio.open(ID_TO_TIFF[image_id])
    gdf = Cfg.VECTORS[Cfg.VECTORS["Id"] == image_id].copy().reset_index(drop=True)
    if gdf.crs != src.crs:
        gdf = gdf.to_crs(src.crs)
    return src, gdf


def _window_bounds_geo(src, row_off, col_off, width_px, height_px):
    """Convert pixel window offsets to geographic bounds.

    Args:
        src: Open rasterio dataset.
        row_off (int): Window top row offset in pixels.
        col_off (int): Window left column offset in pixels.
        width_px (int): Window width in pixels.
        height_px (int): Window height in pixels.

    Returns:
        tuple[float, float, float, float]: (left, bottom, right, top).
    """
    left, top = src.xy(row_off, col_off, offset="ul")
    right, bottom = src.xy(row_off + height_px, col_off + width_px, offset="ul")
    return left, bottom, right, top


def _clamp_window(row_off, col_off, src):
    """Clamp row/column offsets so the configured window stays inside the raster.

    Args:
        row_off (int): Proposed top row offset.
        col_off (int): Proposed left column offset.
        src: Open rasterio dataset.

    Returns:
        tuple[int, int]: Clamped (row_off, col_off).
    """
    row_off = max(0, min(int(row_off), src.height - WINDOW_HEIGHT))
    col_off = max(0, min(int(col_off), src.width - WINDOW_WIDTH))
    return row_off, col_off


def _fit_window_start_to_include_segment(current_start, window_size, seg_min, seg_max, axis_limit):
    """Adjust one window-axis start so a segment falls inside that window axis.

    This is used when one axis is constrained by snapping and the other axis must
    be adjusted so the referenced geometry-bound segment is inside the window.

    Args:
        current_start (int): Proposed window start for the axis.
        window_size (int): Window size on the axis.
        seg_min (int): Segment minimum coordinate on the same axis.
        seg_max (int): Segment maximum coordinate on the same axis.
        axis_limit (int): Maximum valid start value for this axis.

    Returns:
        int: Adjusted start value clamped to [0, axis_limit].
    """
    start = int(current_start)
    seg_a = int(seg_min)
    seg_b = int(seg_max)
    seg_min = min(seg_a, seg_b)
    seg_max = max(seg_a, seg_b)

    if seg_max - seg_min > int(window_size):
        center = int(round((seg_min + seg_max) / 2.0))
        return max(0, min(center - int(window_size // 2), int(axis_limit)))

    if start > seg_min:
        start = seg_min
    if start + int(window_size) < seg_max:
        start = seg_max - int(window_size)

    return max(0, min(start, int(axis_limit)))


def _window_start_from_geometry_edge(window_edge, seg_min, seg_max, window_size, axis_limit, margin_px=1):
    """Compute a window start so the referenced edge is always 1 pixel away from the geometry bound.

    Args:
        window_edge (str): One of left, right, top, bottom.
        seg_min (int): Minimum segment coordinate on the axis.
        seg_max (int): Maximum segment coordinate on the axis.
        window_size (int): Window size on the axis.
        axis_limit (int): Maximum valid start for the axis.
        margin_px (int): Gap in pixels between window edge and geometry bound.

    Returns:
        int: Window start on that axis.
    """
    margin_px = int(margin_px)
    if margin_px < 0:
        raise ValueError("margin_px must be >= 0")

    if window_edge in {"left", "top"}:
        # Window's left/top edge sits margin_px before the geometry's min bound.
        start = int(seg_min) - margin_px
    else:
        # Window's right/bottom edge sits margin_px after the geometry's max bound.
        start = int(seg_max) + margin_px - int(window_size)
    return max(0, min(int(start), int(axis_limit)))


def _recompute_memberships(entry, src, gdf):
    """Refresh window polygon memberships using full containment.

    For each window, this updates:
    - indices: zero-based geometry indexes
    - poly_ids: one-based geometry labels
    and refreshes n_polygons / n_windows in the image entry.

    Args:
        entry (dict): Image entry to update in-place.
        src: Open rasterio dataset.
        gdf (geopandas.GeoDataFrame): Vectors for the selected image.

    Returns:
        None
    """
    for key in _sorted_window_keys(entry):
        w = entry["windows"][key]
        row = int(w["row_off"])
        col = int(w["col_off"])
        left, bottom, right, top = _window_bounds_geo(src, row, col, WINDOW_WIDTH, WINDOW_HEIGHT)
        wgeom = box(left, bottom, right, top)
        idxs = [i for i, geom in enumerate(gdf.geometry) if wgeom.contains(geom)]
        w["indices"] = idxs
        w["poly_ids"] = [i + 1 for i in idxs]
    entry["n_polygons"] = int(len(gdf))
    entry["n_windows"] = int(len(entry["windows"]))


# -----------------------------------------------------------------------------
# Core setup and plotting
# -----------------------------------------------------------------------------

def ensure_image_entry(strategy="auto"):
    """Ensure IMAGE_ID is present in JSON, initializing windows when missing.

    Args:
        strategy (str): Initialization strategy. Currently only auto is supported,
            using the 02.4 automatic non-overlapping selector.

    Returns:
        None

    Raises:
        ValueError: If strategy is not supported.
    """
    data = _load_json()
    entry = _get_image_entry(data, IMAGE_ID, create=True)
    if entry["windows"]:
        _save_json(data)
        return

    if strategy != "auto":
        raise ValueError("Only strategy='auto' is currently supported")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        auto_windows, _, _ = _MOD024.select_non_overlapping_windows(
            src,
            gdf,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
        )

        entry["windows"] = {}
        for i, w in enumerate(auto_windows):
            entry["windows"][str(i)] = {
                "row_off": int(w["row_off"]),
                "col_off": int(w["col_off"]),
                "indices": [],
                "poly_ids": [],
            }
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)


def _get_registered_image_entry():
    """Guarantee IMAGE_ID registration and return a fresh image entry.

    Returns:
        tuple[dict, dict]: (full_json_payload, image_entry).
    """
    ensure_image_entry()
    data = _load_json()
    entry = _get_image_entry(data, IMAGE_ID, create=False)
    return data, entry


def _choose_window_label_position(left, bottom, right, top, centroid_points):
    """Choose a readable label corner for a window rectangle.

    The selected corner maximizes distance to polygon centroid labels that are
    inside the same window, reducing text overlap.

    Args:
        left (float): Window left x.
        bottom (float): Window bottom y.
        right (float): Window right x.
        top (float): Window top y.
        centroid_points (list[tuple[float, float]]): Candidate points to avoid.

    Returns:
        tuple[float, float, str, str]: (x, y, horizontal_align, vertical_align).
    """
    x_pad = (right - left) * 0.02
    y_pad = (top - bottom) * 0.03

    candidates = [
        (left + x_pad, top - y_pad, "left", "top"),
        (right - x_pad, top - y_pad, "right", "top"),
        (left + x_pad, bottom + y_pad, "left", "bottom"),
        (right - x_pad, bottom + y_pad, "right", "bottom"),
    ]

    if not centroid_points:
        return candidates[0]

    best = None
    for cand in candidates:
        cx, cy, _, _ = cand
        score = min((cx - px) ** 2 + (cy - py) ** 2 for px, py in centroid_points)
        if best is None or score > best[0]:
            best = (score, cand)
    return best[1]


def _title_two_lines_if_long(title_text, max_len=120):
    """Split a long title into at most two lines.

    Args:
        title_text (str): Full title text.
        max_len (int): Length threshold to trigger line break.

    Returns:
        str: Single-line or two-line title text.
    """
    txt = str(title_text)
    if len(txt) <= int(max_len):
        return txt

    sep = " | "
    parts = txt.split(sep)
    if len(parts) < 2:
        mid = len(txt) // 2
        return txt[:mid].rstrip() + "\n" + txt[mid:].lstrip()

    best_i = 1
    best_gap = abs(len(parts[0]) - len(sep.join(parts[1:])))
    for i in range(2, len(parts)):
        left = sep.join(parts[:i])
        right = sep.join(parts[i:])
        gap = abs(len(left) - len(right))
        if gap < best_gap:
            best_gap = gap
            best_i = i

    left = sep.join(parts[:best_i])
    right = sep.join(parts[best_i:])
    return left + "\n" + right


def _format_id_ranges(values, prefix=""):
    """Format sorted integer IDs into compact ranges.

    Examples:
        [1,2,3,7,8] -> "1-3,7-8"
        [1,2,3,7,8] with prefix="W" -> "W1-W3,W7-W8"

    Args:
        values (list[int]): ID list.
        prefix (str): Optional item prefix such as W.

    Returns:
        str: Compact range string.
    """
    if not values:
        return ""

    ids = sorted({int(v) for v in values})
    ranges = []
    start = ids[0]
    end = ids[0]

    for v in ids[1:]:
        if v == end + 1:
            end = v
            continue
        ranges.append((start, end))
        start = v
        end = v
    ranges.append((start, end))

    out = []
    for a, b in ranges:
        if a == b:
            out.append(f"{prefix}{a}")
        else:
            out.append(f"{prefix}{a}-{prefix}{b}")
    return ",".join(out)


def _geometry_plot_color(classe):
    """Return plotting color for one geometry class.

    Colors follow FunPlot.py.

    Args:
        classe (str): Geometry class label.

    Returns:
        str: Matplotlib-compatible color.
    """
    classe_txt = str(classe).strip().upper()
    if classe_txt == "OIL SPILL":
        return "#00FFFF"
    if classe_txt in {"SEEPAGE SLICK", "SEAPAGE SLICK"}:
        return "#FF0000"
    return "#000000"


def _plot_geometries_by_class(ax, gdf_subset, linewidth, zorder):
    """Plot geometries grouped by class using class-specific colors.

    Args:
        ax: Matplotlib axis.
        gdf_subset: GeoDataFrame subset to draw.
        linewidth (float): Edge line width.
        zorder (int | float): Matplotlib z-order.

    Returns:
        list[tuple[str, str]]: Unique (class_name, color) pairs drawn.
    """
    if len(gdf_subset) == 0:
        return []

    drawn = []
    if "CLASSE" not in gdf_subset.columns:
        gdf_subset.plot(
            ax=ax,
            facecolor="none",
            edgecolor="#000000",
            linewidth=linewidth,
            alpha=1.0,
            zorder=zorder,
        )
        return [("Polygons", "#000000")]

    class_order = []
    for value in gdf_subset["CLASSE"].fillna("Unknown"):
        class_name = str(value)
        if class_name not in class_order:
            class_order.append(class_name)

    for class_name in class_order:
        sub = gdf_subset[gdf_subset["CLASSE"].fillna("Unknown") == class_name]
        color = _geometry_plot_color(class_name)
        sub.plot(
            ax=ax,
            facecolor="none",
            edgecolor=color,
            linewidth=linewidth,
            alpha=1.0,
            zorder=zorder,
        )
        drawn.append((class_name, color))
    return drawn


def plot_current_image(overwrite=True):
    """(pl) Render a QA plot for the current image and window layout.

    Args:
        overwrite (bool): Reserved for future behavior; currently ignored.

    Returns:
        str: Output PNG path.
    """
    _, entry = _get_registered_image_entry()

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        gdf_land = gpd.read_file(LAND_PATH)
        if gdf_land.crs != src.crs:
            gdf_land = gdf_land.to_crs(src.crs)

        out_png = os.path.join(
            DIR_OUT,
              f"IMG_{IMAGE_ID:02d}_POLYGONS_{WINDOW_WIDTH}x{WINDOW_HEIGHT}.png",
        )

        bounds = src.bounds
        fig, ax = plt.subplots(figsize=(14, 10), dpi=140)
        ax.set_aspect("equal", adjustable="box")

        ax.add_patch(
            Rectangle(
                (bounds.left, bounds.bottom),
                bounds.right - bounds.left,
                bounds.top - bounds.bottom,
                linewidth=1.2,
                edgecolor="#4A90E2",
                facecolor="none",
            )
        )

        footprint = gpd.GeoDataFrame(
            {"geometry": [box(bounds.left, bounds.bottom, bounds.right, bounds.top)]},
            crs=src.crs,
        )
        land_in_img = gpd.overlay(gdf_land[["geometry"]].copy(), footprint, how="intersection")
        if len(land_in_img) > 0:
            land_in_img.plot(
                ax=ax,
                facecolor="#2E8B57",
                edgecolor="#006400",
                linewidth=0.8,
                alpha=0.35,
                zorder=1,
            )

        drawn_classes = _plot_geometries_by_class(ax, gdf, linewidth=1.1, zorder=4)

        for idx_local, (_, row) in enumerate(gdf.iterrows(), start=1):
            c = row.geometry.centroid
            ax.text(
                c.x,
                c.y,
                str(idx_local),
                color="black",
                fontsize=8,
                fontweight="bold",
                ha="center",
                va="center",
                zorder=7,
            )

        centroid_points = [(row.geometry.centroid.x, row.geometry.centroid.y) for _, row in gdf.iterrows()]
        for key in _sorted_window_keys(entry):
            w = entry["windows"][key]
            row_off = int(w["row_off"])
            col_off = int(w["col_off"])
            left, bottom, right, top = _window_bounds_geo(src, row_off, col_off, WINDOW_WIDTH, WINDOW_HEIGHT)
            ax.add_patch(
                Rectangle(
                    (left, bottom),
                    right - left,
                    top - bottom,
                    linewidth=1.0,
                    edgecolor="#8A2BE2",
                    facecolor="none",
                    linestyle="-.",
                    zorder=6,
                )
            )

            # label as W(1-based)
            label_x, label_y, ha, va = _choose_window_label_position(
                left,
                bottom,
                right,
                top,
                [p for p in centroid_points if left <= p[0] <= right and bottom <= p[1] <= top],
            )
            ax.text(
                label_x,
                label_y,
                f"W{int(key)+1}",
                color="#8A2BE2",
                fontsize=7,
                fontweight="bold",
                ha=ha,
                va=va,
                zorder=7,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="#8A2BE2", lw=0.8, alpha=0.9),
            )

        qa_title = f"TIFF {IMAGE_ID:02d} | Polygons: {len(gdf)} | Windows: {len(entry['windows'])}"
        ax.set_title(
            _title_two_lines_if_long(qa_title),
            fontsize=13,
            fontweight="bold",
        )
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.6)
        ax.set_xlim(bounds.left, bounds.right)
        ax.set_ylim(bounds.bottom, bounds.top)

        legend_handles = [
            Line2D([0], [0], color="#4A90E2", lw=1.2, label="Image footprint"),
        ]
        for class_name, color in drawn_classes:
            legend_handles.append(Line2D([0], [0], color=color, lw=1.1, label=class_name))
        legend_handles.append(Line2D([0], [0], color="#8A2BE2", lw=1.0, ls="-.", label="Windows"))
        if len(land_in_img) > 0:
            legend_handles.append(Line2D([0], [0], color="#006400", lw=0.8, label="Continent"))
        ax.legend(handles=legend_handles, loc="lower left", fontsize=9)

        plt.tight_layout()
        plt.savefig(out_png)
        plt.close(fig)

        return out_png
    finally:
        src.close()


def plot_command_focus(
    command_name,
    window_ids=None,
    poly_ids_1b=None,
    focus_margin=None,
    out_filename=None,
    title_prefix="CURRENT FOCUS",
    draw_all_geometries=False,
):
    """Render a focused plot for objects involved in one command.

    The output filename is static so external viewers can auto-refresh.

    Args:
        command_name (str): Command label for plot title.
        window_ids (list[int] | None): 1-based windows to highlight.
        poly_ids_1b (list[int] | None): 1-based polygons to highlight.
        focus_margin (float | None): Relative margin around focused bbox.
            When None, uses global FOCUS_MARGIN.
        out_filename (str | None): Output filename under DIR_OUT.
            When None, uses CURRENT_FOCUS_FILENAME.
        title_prefix (str): Prefix shown in the plot title.
        draw_all_geometries (bool): When True, draw all image geometries
            regardless of poly_ids_1b.

    Returns:
        str: Output PNG path.
    """
    _, entry = _get_registered_image_entry()

    focus_windows = sorted({int(w) for w in (window_ids or []) if int(w) > 0})
    focus_polys = sorted({int(p) for p in (poly_ids_1b or []) if int(p) > 0})

    # If caller does not provide focus objects, use all windows as default context.
    if not focus_windows and not focus_polys:
        focus_windows = [int(k) + 1 for k in _sorted_window_keys(entry)]

    # If exactly one window is referenced and no polygons, include all polygons that intersect (touch or are inside) the window.
    if len(focus_windows) == 1 and not focus_polys:
        key = _window_key_from_id(focus_windows[0])
        if key in entry["windows"]:
            src, gdf = _ensure_src_and_gdf(IMAGE_ID)
            w = entry["windows"][key]
            row_off = int(w["row_off"])
            col_off = int(w["col_off"])
            left, bottom, right, top = _window_bounds_geo(src, row_off, col_off, WINDOW_WIDTH, WINDOW_HEIGHT)
            wgeom = box(left, bottom, right, top)
            poly_ids = [i+1 for i, geom in enumerate(gdf.geometry) if wgeom.intersects(geom)]
            focus_polys = list(sorted(set(poly_ids)))

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        bounds = src.bounds
        fig, ax = plt.subplots(figsize=(12, 9), dpi=130)
        ax.set_aspect("equal", adjustable="box")

        # Collect focused geometries and window extents to compute zoom bounds.
        focus_poly_geoms = []
        for pid in focus_polys:
            idx = pid - 1
            if 0 <= idx < len(gdf):
                focus_poly_geoms.append((pid, gdf.geometry.iloc[idx]))

        focus_window_boxes = []
        for wid in focus_windows:
            key = _window_key_from_id(wid)
            if key not in entry["windows"]:
                continue
            w = entry["windows"][key]
            row_off = int(w["row_off"])
            col_off = int(w["col_off"])
            left, bottom, right, top = _window_bounds_geo(src, row_off, col_off, WINDOW_WIDTH, WINDOW_HEIGHT)
            focus_window_boxes.append((wid, left, bottom, right, top))

        minx_vals = []
        miny_vals = []
        maxx_vals = []
        maxy_vals = []

        for _, geom in focus_poly_geoms:
            gx0, gy0, gx1, gy1 = geom.bounds
            minx_vals.append(gx0)
            miny_vals.append(gy0)
            maxx_vals.append(gx1)
            maxy_vals.append(gy1)

        for _, left, bottom, right, top in focus_window_boxes:
            minx_vals.append(left)
            miny_vals.append(bottom)
            maxx_vals.append(right)
            maxy_vals.append(top)

        if minx_vals:
            fx0 = min(minx_vals)
            fy0 = min(miny_vals)
            fx1 = max(maxx_vals)
            fy1 = max(maxy_vals)
        else:
            fx0, fy0, fx1, fy1 = bounds.left, bounds.bottom, bounds.right, bounds.top

        margin_ratio = FOCUS_MARGIN if focus_margin is None else float(focus_margin)
        margin_ratio = max(0.0, margin_ratio)
        dx = max(fx1 - fx0, 1e-12)
        dy = max(fy1 - fy0, 1e-12)
        margin_x = max(dx * margin_ratio, (bounds.right - bounds.left) * 0.01)
        margin_y = max(dy * margin_ratio, (bounds.top - bounds.bottom) * 0.01)

        x0 = max(bounds.left, fx0 - margin_x)
        x1 = min(bounds.right, fx1 + margin_x)
        y0 = max(bounds.bottom, fy0 - margin_y)
        y1 = min(bounds.top, fy1 + margin_y)

        # Draw geometries visible in the current plotting extent.
        if draw_all_geometries:
            draw_idx = list(range(len(gdf)))
        else:
            view_box = box(x0, y0, x1, y1)
            draw_idx = [i for i, geom in enumerate(gdf.geometry) if view_box.intersects(geom)]

        if draw_idx:
            _plot_geometries_by_class(ax, gdf.iloc[draw_idx], linewidth=1.8, zorder=6)
            for idx_local in draw_idx:
                geom = gdf.geometry.iloc[idx_local]
                c = geom.centroid
                ax.text(
                    c.x,
                    c.y,
                    str(idx_local + 1),
                    color="black",
                    fontsize=8,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    zorder=7,
                )

        for wid, left, bottom, right, top in focus_window_boxes:
            ax.add_patch(
                Rectangle(
                    (left, bottom),
                    right - left,
                    top - bottom,
                    linewidth=2.0,
                    edgecolor="#8A2BE2",
                    facecolor="none",
                    linestyle="-",
                    zorder=8,
                )
            )
            # Place window label just outside the top-right corner
            label_x = right + (right - left) * 0.01
            label_y = top + (top - bottom) * 0.01
            ax.text(
                label_x,
                label_y,
                f"W{wid}",
                color="#8A2BE2",
                fontsize=8,
                fontweight="bold",
                ha="left",
                va="bottom",
                zorder=9,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="#8A2BE2", lw=0.8, alpha=0.95),
            )

            # Border on the four edges of the focused global bounding box.
            border_color = "#FF4D4F"
            border_lw = 2.2
            ax.plot([x0, x1], [y0, y0], color=border_color, lw=border_lw, zorder=10)
            ax.plot([x0, x1], [y1, y1], color=border_color, lw=border_lw, zorder=10)
            ax.plot([x0, x0], [y0, y1], color=border_color, lw=border_lw, zorder=10)
            ax.plot([x1, x1], [y0, y1], color=border_color, lw=border_lw, zorder=10)

        title_parts = [f"{title_prefix} | TIFF {IMAGE_ID:02d}", f"command: {command_name}"]
        if focus_windows:
            title_parts.append("windows: " + _format_id_ranges(focus_windows, prefix="W"))
        if focus_polys:
            title_parts.append("polygons: " + _format_id_ranges(focus_polys))
        title_text = " | ".join(title_parts)
        ax.set_title(_title_two_lines_if_long(title_text), fontsize=12, fontweight="bold")

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)

        out_png_name = CURRENT_FOCUS_FILENAME if out_filename is None else str(out_filename)
        out_png = os.path.join(DIR_OUT, out_png_name)
        plt.tight_layout()
        plt.savefig(out_png)
        plt.close(fig)
        return out_png
    finally:
        src.close()


def plot_global_bounding_box_zoom(
    window_ids=None,
    poly_ids_1b=None,
    focus_margin=None,
    also_update_current_focus=True,
):
    """(pb) Plot global bounding-box zoom for selected windows/geometries.

    This function generates a static global-bbox output file and can also
    refresh the static current-focus file in the same call.

    Args:
        window_ids (list[int] | None): 1-based windows to include in focus bbox.
        poly_ids_1b (list[int] | None): 1-based polygons to include in focus bbox.
        focus_margin (float | None): Relative margin around focused bbox.
            When None, uses global FOCUS_MARGIN.
        also_update_current_focus (bool): If True, also writes
            00-CURRENT_FOCUS_WINDOW.png.

    Returns:
        dict: Output paths with keys image_named and current_focus.
    """
    image_named_filename = GLOBAL_BBOX_FILENAME
    image_named_path = plot_command_focus(
        command_name="global-bbox",
        window_ids=window_ids,
        poly_ids_1b=poly_ids_1b,
        focus_margin=focus_margin,
        out_filename=image_named_filename,
        title_prefix="GLOBAL BBOX ZOOM",
        draw_all_geometries=True,
    )

    current_focus_path = None
    if also_update_current_focus:
        current_focus_path = plot_command_focus(
            command_name="global-bbox",
            window_ids=window_ids,
            poly_ids_1b=poly_ids_1b,
            focus_margin=focus_margin,
            out_filename=CURRENT_FOCUS_FILENAME,
            title_prefix="CURRENT FOCUS",
            draw_all_geometries=True,
        )

    return {
        "image_named": image_named_path,
        "current_focus": current_focus_path,
    }


def render_all_outputs_for_current_image(
    focus_window_ids=None,
    focus_poly_ids=None,
    focus_command_name="command",
):
    """Render the three canonical outputs for the active image.

    Outputs:
    1) QA full-image plot
    2) Image-named global bbox zoom
    3) CURRENT_FOCUS image (command-focused)

    Args:
        focus_window_ids (list[int] | None): Windows to focus CURRENT_FOCUS on.
        focus_poly_ids (list[int] | None): Polygons to focus CURRENT_FOCUS on.
        focus_command_name (str): Command label shown in CURRENT_FOCUS title.

    Returns:
        dict: Paths with keys qa, image_named, current_focus.
    """
    _cleanup_unused_plot_files()

    _, entry = _get_registered_image_entry()
    all_window_ids = [int(k) + 1 for k in _sorted_window_keys(entry)]

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        all_poly_ids = list(range(1, len(gdf) + 1))
    finally:
        src.close()

    qa_path = plot_current_image()
    bbox_outputs = plot_global_bounding_box_zoom(
        window_ids=all_window_ids,
        poly_ids_1b=all_poly_ids,
        also_update_current_focus=False,
    )

    current_focus_path = plot_command_focus(
        command_name=str(focus_command_name),
        window_ids=focus_window_ids,
        poly_ids_1b=focus_poly_ids,
        out_filename=CURRENT_FOCUS_FILENAME,
        title_prefix="CURRENT FOCUS",
        draw_all_geometries=False,
    )

    return {
        "qa": qa_path,
        "image_named": bbox_outputs["image_named"],
        "current_focus": current_focus_path,
    }


def _cleanup_unused_plot_files():
    """Delete legacy plot files that are no longer used.

    Keeps the current static files and removes obsolete dynamic global-bbox and
    old current-focus naming outputs.

    Returns:
        None
    """
    legacy_patterns = [
        os.path.join(DIR_OUT, "IMG_*_GLOBAL_BBOX_ZOOM_*.png"),
        os.path.join(DIR_OUT, "CURRENT_FOCUS_IMAGE.png"),
    ]
    keep_names = {GLOBAL_BBOX_FILENAME, CURRENT_FOCUS_FILENAME}

    for pattern in legacy_patterns:
        for path in glob.glob(pattern):
            if os.path.basename(path) in keep_names:
                continue
            if not os.path.isfile(path):
                continue
            try:
                os.remove(path)
            except OSError:
                pass


# -----------------------------------------------------------------------------
# Move functions
# -----------------------------------------------------------------------------

def center_window_on_geometries(window_id, poly_ids_1b):
    """(mc) Move an existing window to the center of selected geometries.

    The target is the center of the union bounding box of poly_ids_1b.
    Updated offsets are clamped to raster bounds, memberships are recomputed,
    and JSON is persisted.

    Args:
        window_id (int): 1-based window ID to move.
        poly_ids_1b (list[int]): 1-based geometry IDs used as positioning target.

    Returns:
        None

    Raises:
        ValueError: If the window ID does not exist or an ID cannot be cast to int.
        IndexError: If any geometry ID is outside available geometry indexes.
    """
    data, entry = _get_registered_image_entry()

    key = _window_key_from_id(window_id)
    if key not in entry["windows"]:
        raise ValueError(f"Window W{window_id} not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        ilocs = [int(p) - 1 for p in poly_ids_1b]
        sub = gdf.iloc[ilocs]
        minx, miny, maxx, maxy = sub.total_bounds
        cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        c_row, c_col = src.index(cx, cy)
        row = int(round(c_row - WINDOW_HEIGHT / 2))
        col = int(round(c_col - WINDOW_WIDTH / 2))
        row, col = _clamp_window(row, col, src)

        entry["windows"][key]["row_off"] = int(row)
        entry["windows"][key]["col_off"] = int(col)
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def align_window_x(window_id, ref_window_id, my_edge, ref_edge, shift_px=0):
    """(ax) Align one window horizontally to another by edge pairing.

    Args:
        window_id (int): 1-based ID of the window to move.
        ref_window_id (int): 1-based reference window ID.
        my_edge (str): Edge on target window, one of left or right.
        ref_edge (str): Edge on reference window, one of left or right.
        shift_px (int): Extra horizontal shift in pixels after alignment.
            Positive values move right, negative values move left.

    Returns:
        None

    Raises:
        ValueError: If edge names are invalid or window IDs are missing.
    """
    if my_edge not in {"left", "right"} or ref_edge not in {"left", "right"}:
        raise ValueError("my_edge/ref_edge must be 'left' or 'right'")

    data, entry = _get_registered_image_entry()

    my_key = _window_key_from_id(window_id)
    ref_key = _window_key_from_id(ref_window_id)
    if my_key not in entry["windows"] or ref_key not in entry["windows"]:
        raise ValueError("Window ID not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        my_w = entry["windows"][my_key]
        ref_w = entry["windows"][ref_key]

        ref_col = int(ref_w["col_off"])
        ref_edge_x = ref_col if ref_edge == "left" else ref_col + WINDOW_WIDTH

        new_col = ref_edge_x if my_edge == "left" else ref_edge_x - WINDOW_WIDTH
        new_col = int(new_col) + int(shift_px)
        _, new_col = _clamp_window(int(my_w["row_off"]), int(new_col), src)

        my_w["col_off"] = int(new_col)
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def align_window_y(window_id, ref_window_id, my_edge, ref_edge, shift_px=0):
    """(ay) Align one window vertically to another by edge pairing.

    Args:
        window_id (int): 1-based ID of the window to move.
        ref_window_id (int): 1-based reference window ID.
        my_edge (str): Edge on target window, one of top or bottom.
        ref_edge (str): Edge on reference window, one of top or bottom.
        shift_px (int): Extra vertical shift in pixels after alignment.
            Positive values move down, negative values move up.

    Returns:
        None

    Raises:
        ValueError: If edge names are invalid or window IDs are missing.
    """
    if my_edge not in {"top", "bottom"} or ref_edge not in {"top", "bottom"}:
        raise ValueError("my_edge/ref_edge must be 'top' or 'bottom'")

    data, entry = _get_registered_image_entry()

    my_key = _window_key_from_id(window_id)
    ref_key = _window_key_from_id(ref_window_id)
    if my_key not in entry["windows"] or ref_key not in entry["windows"]:
        raise ValueError("Window ID not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        my_w = entry["windows"][my_key]
        ref_w = entry["windows"][ref_key]

        ref_row = int(ref_w["row_off"])
        ref_edge_y = ref_row if ref_edge == "top" else ref_row + WINDOW_HEIGHT

        new_row = ref_edge_y if my_edge == "top" else ref_edge_y - WINDOW_HEIGHT
        new_row = int(new_row) + int(shift_px)
        new_row, _ = _clamp_window(int(new_row), int(my_w["col_off"]), src)

        my_w["row_off"] = int(new_row)
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def shift(window_id, axis, amount):
    """(sh) Shift one existing window on one axis by a pixel amount.

    Args:
        window_id (int): 1-based ID of the window to move.
        axis (str): Axis selector, one of x or y.
        amount (int): Shift amount in pixels on selected axis.
            For x: positive=right, negative=left.
            For y: positive=down, negative=up.

    Returns:
        None

    Raises:
        ValueError: If axis is not x/y or window ID is missing.
    """
    ax = str(axis).strip().lower()
    if ax not in {"x", "y"}:
        raise ValueError("axis must be 'x' or 'y'")

    data, entry = _get_registered_image_entry()
    key = _window_key_from_id(window_id)
    if key not in entry["windows"]:
        raise ValueError(f"Window W{window_id} not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        w = entry["windows"][key]
        row = int(w["row_off"])
        col = int(w["col_off"])
        if ax == "x":
            col = int(col) + int(amount)
        else:
            row = int(row) + int(amount)
        row, col = _clamp_window(row, col, src)
        w["row_off"] = int(row)
        w["col_off"] = int(col)
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def snap_window_edge_to_geometry_bound(window_id, poly_id_1b, window_edge, geometry_bound, margin_px=1):
    """(sn) Move an existing window by snapping one edge to one geometry bound.

    The snapped axis is biased to leave a one-pixel margin from the geometry
    edge when possible, and the other axis is adjusted so the full geometry is
    inside the window whenever the geometry fits in the configured window size.

    Args:
        window_id (int): 1-based window ID to move.
        poly_id_1b (int): 1-based geometry ID used as target.
        window_edge (str): Window edge in left, right, top, bottom.
        geometry_bound (str): Geometry bound in west, east, north, south.
        margin_px (int): Pixel gap between window edge and geometry bound.
            - left/top: window edge is margin_px pixels before the bound.
            - right/bottom: window edge is margin_px pixels after the bound.

    Returns:
        None

    Raises:
        ValueError: If edge/bound options are invalid or window ID is missing.
        IndexError: If poly_id_1b is outside available geometry indexes.
    """
    if window_edge not in {"left", "right", "top", "bottom"}:
        raise ValueError("window_edge must be one of: left, right, top, bottom")
    if geometry_bound not in {"west", "east", "north", "south"}:
        raise ValueError("geometry_bound must be one of: west, east, north, south")
    if int(margin_px) < 0:
        raise ValueError("margin_px must be >= 0")

    data, entry = _get_registered_image_entry()

    key = _window_key_from_id(window_id)
    if key not in entry["windows"]:
        raise ValueError(f"Window W{window_id} not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        geom = gdf.geometry.iloc[int(poly_id_1b) - 1]
        minx, miny, maxx, maxy = geom.bounds
        r0, c0 = src.index(minx, maxy)
        r1, c1 = src.index(maxx, miny)
        north = min(r0, r1)
        south = max(r0, r1)
        west = min(c0, c1)
        east = max(c0, c1)


        # Only move the requested axis; keep the other unchanged
        row = int(entry["windows"][key]["row_off"])
        col = int(entry["windows"][key]["col_off"])
        if window_edge in {"left", "right"}:
            col = _window_start_from_geometry_edge(
                window_edge=window_edge,
                seg_min=west,
                seg_max=east,
                window_size=WINDOW_WIDTH,
                axis_limit=src.width - WINDOW_WIDTH,
                margin_px=margin_px,
            )
        else:
            row = _window_start_from_geometry_edge(
                window_edge=window_edge,
                seg_min=north,
                seg_max=south,
                window_size=WINDOW_HEIGHT,
                axis_limit=src.height - WINDOW_HEIGHT,
                margin_px=margin_px,
            )

        row, col = _clamp_window(row, col, src)
        entry["windows"][key]["row_off"] = int(row)
        entry["windows"][key]["col_off"] = int(col)
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def create_window_centered_on_geometries(poly_ids_1b):
    """(crc) Create a new window centered on selected geometries.

    The target point is the center of the union bounding box of poly_ids_1b.

    Args:
        poly_ids_1b (list[int]): 1-based geometry IDs used as positioning target.

    Returns:
        int: New 1-based window ID.

    Raises:
        ValueError: If an ID cannot be cast to int.
        IndexError: If any geometry ID is outside available geometry indexes.
    """
    data, entry = _get_registered_image_entry()

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        ilocs = [int(p) - 1 for p in poly_ids_1b]
        sub = gdf.iloc[ilocs]
        minx, miny, maxx, maxy = sub.total_bounds
        cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        c_row, c_col = src.index(cx, cy)
        row = int(round(c_row - WINDOW_HEIGHT / 2))
        col = int(round(c_col - WINDOW_WIDTH / 2))
        row, col = _clamp_window(row, col, src)

        key = _next_window_key(entry)
        entry["windows"][key] = {
            "row_off": int(row),
            "col_off": int(col),
            "indices": [],
            "poly_ids": [],
        }
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()
    return int(key) + 1


def create_window_adjacent_to_window(ref_window_id, side, align="center"):
    """(cra) Create a new window adjacent to a reference window.

    Args:
        ref_window_id (int): 1-based reference window ID.
        side (str): Placement side relative to reference: east, west, north, south.
        align (str): Alignment mode. For east/west use top|center|bottom.
            For north/south use left|center|right.

    Returns:
        int: New 1-based window ID.

    Raises:
        ValueError: If side/align is invalid, reference window is missing,
            or ref_window_id cannot be cast to int.
    """
    if side not in {"east", "west", "north", "south"}:
        raise ValueError("side must be one of: east, west, north, south")

    data, entry = _get_registered_image_entry()
    ref_key = _window_key_from_id(ref_window_id)
    if ref_key not in entry["windows"]:
        raise ValueError(f"Window W{ref_window_id} not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        ref = entry["windows"][ref_key]
        r = int(ref["row_off"])
        c = int(ref["col_off"])

        if side == "east":
            col = c + WINDOW_WIDTH
            if align == "top":
                row = r
            elif align == "bottom":
                row = r
            elif align == "center":
                row = r
            else:
                raise ValueError("align must be one of: top, center, bottom")
        elif side == "west":
            col = c - WINDOW_WIDTH
            if align == "top":
                row = r
            elif align == "bottom":
                row = r
            elif align == "center":
                row = r
            else:
                raise ValueError("align must be one of: top, center, bottom")
        elif side == "north":
            row = r - WINDOW_HEIGHT
            if align == "left":
                col = c
            elif align == "right":
                col = c
            elif align == "center":
                col = c
            else:
                raise ValueError("align must be one of: left, center, right")
        else:
            row = r + WINDOW_HEIGHT
            if align == "left":
                col = c
            elif align == "right":
                col = c
            elif align == "center":
                col = c
            else:
                raise ValueError("align must be one of: left, center, right")

        row, col = _clamp_window(row, col, src)
        key = _next_window_key(entry)
        entry["windows"][key] = {
            "row_off": int(row),
            "col_off": int(col),
            "indices": [],
            "poly_ids": [],
        }
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()
    return int(key) + 1


def create_window_by_geometry_bound(poly_id_1b, window_edge, geometry_bound):
    """(crb) Create a new window by matching one edge to a geometry bound.

    The unconstrained axis is centered on the target geometry and then adjusted
    to keep the full geometry inside the window whenever it fits.

    Args:
        poly_id_1b (int): 1-based geometry ID used as target.
        window_edge (str): Window edge in left, right, top, bottom.
        geometry_bound (str): Geometry bound in west, east, north, south.

    Returns:
        int: New 1-based window ID.

    Raises:
        ValueError: If edge/bound option is invalid.
        IndexError: If poly_id_1b is outside available geometry indexes.
    """
    if window_edge not in {"left", "right", "top", "bottom"}:
        raise ValueError("window_edge must be one of: left, right, top, bottom")
    if geometry_bound not in {"west", "east", "north", "south"}:
        raise ValueError("geometry_bound must be one of: west, east, north, south")

    data, entry = _get_registered_image_entry()
    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        geom = gdf.geometry.iloc[int(poly_id_1b) - 1]
        minx, miny, maxx, maxy = geom.bounds
        r0, c0 = src.index(minx, maxy)
        r1, c1 = src.index(maxx, miny)
        north = min(r0, r1)
        south = max(r0, r1)
        west = min(c0, c1)
        east = max(c0, c1)

        row = 0
        col = 0

        # Keep the unassigned axis near the target geometry center while still
        # forcing full geometry containment.
        c_row, c_col = src.index((minx + maxx) / 2.0, (miny + maxy) / 2.0)
        if window_edge in {"left", "right"}:
            col = _window_start_from_geometry_edge(
                window_edge=window_edge,
                seg_min=west,
                seg_max=east,
                window_size=WINDOW_WIDTH,
                axis_limit=src.width - WINDOW_WIDTH,
            )
            row = int(round(c_row - WINDOW_HEIGHT / 2))
            row = _fit_window_start_to_include_segment(
                current_start=row,
                window_size=WINDOW_HEIGHT,
                seg_min=north,
                seg_max=south,
                axis_limit=src.height - WINDOW_HEIGHT,
            )
        else:
            row = _window_start_from_geometry_edge(
                window_edge=window_edge,
                seg_min=north,
                seg_max=south,
                window_size=WINDOW_HEIGHT,
                axis_limit=src.height - WINDOW_HEIGHT,
            )
            col = int(round(c_col - WINDOW_WIDTH / 2))
            col = _fit_window_start_to_include_segment(
                current_start=col,
                window_size=WINDOW_WIDTH,
                seg_min=west,
                seg_max=east,
                axis_limit=src.width - WINDOW_WIDTH,
            )

        row, col = _clamp_window(row, col, src)
        key = _next_window_key(entry)
        entry["windows"][key] = {
            "row_off": int(row),
            "col_off": int(col),
            "indices": [],
            "poly_ids": [],
        }
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()
    return int(key) + 1


# -----------------------------------------------------------------------------
# Check functions
# -----------------------------------------------------------------------------

def check_window_geometries(window_id):
    """(ckw) Check containment/intersection status for one window.

    Args:
        window_id (int): 1-based window ID to inspect.

    Returns:
        dict: Summary with full, partial, and outside geometry ID lists.

    Raises:
        ValueError: If window ID does not exist or cannot be cast to int.
    """
    _, entry = _get_registered_image_entry()

    key = _window_key_from_id(window_id)
    if key not in entry["windows"]:
        raise ValueError(f"Window W{window_id} not found.")

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        w = entry["windows"][key]
        row = int(w["row_off"])
        col = int(w["col_off"])
        left, bottom, right, top = _window_bounds_geo(src, row, col, WINDOW_WIDTH, WINDOW_HEIGHT)
        wgeom = box(left, bottom, right, top)

        full = []
        partial = []
        outside = []
        for i, geom in enumerate(gdf.geometry, start=1):
            if wgeom.contains(geom):
                full.append(i)
            elif wgeom.intersects(geom):
                partial.append(i)
            else:
                outside.append(i)

        result = {
            "window_id": int(window_id),
            "full": full,
            "partial": partial,
            "outside": outside,
        }
        print(result)
        return result
    finally:
        src.close()


def check_geometry_in_windows(poly_id_1b):
    """(ckg) Check whether one geometry is fully inside a window or window union.

    Args:
        poly_id_1b (int): 1-based geometry ID to inspect.

    Returns:
        dict: Summary with windows that fully contain the geometry, plus
            containment against the union of all windows.

    Raises:
        IndexError: If poly_id_1b is outside available geometry indexes.
        ValueError: If poly_id_1b cannot be cast to int.
    """
    _, entry = _get_registered_image_entry()

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        geom_idx = int(poly_id_1b) - 1
        geom = gdf.geometry.iloc[geom_idx]

        window_geoms = []
        containing_windows = []
        for key in _sorted_window_keys(entry):
            w = entry["windows"][key]
            row = int(w["row_off"])
            col = int(w["col_off"])
            left, bottom, right, top = _window_bounds_geo(src, row, col, WINDOW_WIDTH, WINDOW_HEIGHT)
            wgeom = box(left, bottom, right, top)
            window_geoms.append(wgeom)
            if wgeom.contains(geom):
                containing_windows.append(int(key) + 1)

        union_geom = unary_union(window_geoms) if window_geoms else None

        result = {
            "poly_id": int(poly_id_1b),
            "fully_inside_any_window": len(containing_windows) > 0,
            "fully_inside_window_union": (union_geom is not None and union_geom.contains(geom)),
            "windows": containing_windows,
        }
        print(result)
        return result
    finally:
        src.close()


def check_image_coverage_and_commit_if_ok(expected_width=800, expected_height=600, commit_if_ok=False):
    """(cki) Check global coverage and commit memberships only when valid.

    Conditions for all_ok:
    1) All geometries are fully covered by at least one window union.
    2) Configured window size matches expected size and all offsets are in bounds.

    Args:
        expected_width (int): Expected window width in pixels.
        expected_height (int): Expected window height in pixels.

    Args:
        commit_if_ok (bool): If True, persist recomputed memberships when all_ok.

    Returns:
        dict: Coverage summary including missing IDs, all_ok, and committed flag.
    """
    data, entry = _get_registered_image_entry()

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        windows = []
        all_size_ok = (WINDOW_WIDTH == expected_width and WINDOW_HEIGHT == expected_height)

        for key in _sorted_window_keys(entry):
            w = entry["windows"][key]
            row = int(w["row_off"])
            col = int(w["col_off"])
            in_bounds = (0 <= row <= src.height - WINDOW_HEIGHT) and (0 <= col <= src.width - WINDOW_WIDTH)
            all_size_ok = all_size_ok and in_bounds

            left, bottom, right, top = _window_bounds_geo(src, row, col, WINDOW_WIDTH, WINDOW_HEIGHT)
            windows.append((int(key) + 1, box(left, bottom, right, top)))

        union_geom = unary_union([wg for _, wg in windows]) if windows else None

        not_in_single = []
        not_in_union = []
        for i, geom in enumerate(gdf.geometry, start=1):
            in_single = any(wg.contains(geom) for _, wg in windows)
            if not in_single:
                not_in_single.append(i)
            if union_geom is None or not union_geom.contains(geom):
                not_in_union.append(i)

        all_ok = all_size_ok and (len(not_in_union) == 0)

        result = {
            "image_id": IMAGE_ID,
            "all_windows_expected_size_and_in_bounds": all_size_ok,
            "not_fully_in_single_window": not_in_single,
            "not_fully_in_union": not_in_union,
            "all_ok": all_ok,
            "committed": False,
        }

        if all_ok and commit_if_ok:
            _recompute_memberships(entry, src, gdf)
            _save_json(data)
            result["committed"] = True

        print(_format_check_image_report(result))
        return result
    finally:
        src.close()


def _format_check_image_report(result):
    """Build a human-readable check-image report for terminal output.

    Args:
        result (dict): Result dictionary from check_image_coverage_and_commit_if_ok.

    Returns:
        str: Multi-line human-readable report.
    """
    not_single = result.get("not_fully_in_single_window", [])
    not_union = result.get("not_fully_in_union", [])

    single_txt = ", ".join(str(v) for v in not_single) if not_single else "none"
    union_txt = ", ".join(str(v) for v in not_union) if not_union else "none"

    status = "PASS" if result.get("all_ok") else "FAIL"
    size_bounds = "OK" if result.get("all_windows_expected_size_and_in_bounds") else "ISSUES FOUND"
    committed = "YES" if result.get("committed") else "NO"

    lines = [
        "CHECK-IMAGE REPORT",
        f"- Image ID: {result.get('image_id')}",
        f"- Overall status: {status}",
        f"- Window size/bounds: {size_bounds}",
        f"- Not fully inside any single window: {single_txt}",
        f"- Not fully inside union of windows: {union_txt}",
        f"- Memberships committed: {committed}",
    ]
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Convenience helpers
# -----------------------------------------------------------------------------

def reindex_windows():
    """(rx) Reindex windows to contiguous keys while preserving key order.

    Returns:
        None
    """
    data, entry = _get_registered_image_entry()

    ordered = _sorted_window_keys(entry)
    new_windows = {}
    for new_idx, old_key in enumerate(ordered):
        new_windows[str(new_idx)] = entry["windows"][old_key]
    entry["windows"] = new_windows
    entry["n_windows"] = len(new_windows)

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def delete_window_and_reindex(window_id):
    """(dw) Delete one window by ID and reindex remaining windows contiguously.

    Args:
        window_id (int): 1-based window ID to delete.

    Returns:
        None

    Raises:
        ValueError: If the window ID does not exist.
    """
    data, entry = _get_registered_image_entry()

    key = _window_key_from_id(window_id)
    if key not in entry["windows"]:
        raise ValueError(f"Window W{window_id} not found.")

    del entry["windows"][key]

    ordered = _sorted_window_keys(entry)
    new_windows = {}
    for new_idx, old_key in enumerate(ordered):
        new_windows[str(new_idx)] = entry["windows"][old_key]
    entry["windows"] = new_windows

    src, gdf = _ensure_src_and_gdf(IMAGE_ID)
    try:
        _recompute_memberships(entry, src, gdf)
    finally:
        src.close()

    _save_json(data)
    if AUTO_PLOT_AFTER_MOVE:
        plot_current_image()


def list_toolbox_functions(print_output=True, compact=True):
    """(ls) Return available toolbox functions and optionally print them.

    Args:
        print_output (bool): If True, print formatted text and return None.
        compact (bool): If True, print shortened signatures.

    Returns:
        str | None: Full listing text when print_output is False, otherwise None.
    """
    if compact:
        lines = [
            "CLI quick use:",
            "- Help: 02.5-ManualWindowTools.py --help",
            "- Full signatures: 02.5-ManualWindowTools.py list --full",
            "- One docstring: 02.5-ManualWindowTools.py show-doc <function_name>",
            "- All docstrings: 02.5-ManualWindowTools.py show-doc --all",
            "",
            "Common global options:",
            "- --image-id N  --width W  --height H",
            "- --json-path PATH  --out-dir PATH",
            "",
            "Creation functions:",
            "- create_window_centered_on_geometries(...)",
            "- create_window_adjacent_to_window(...)",
            "- create_window_by_geometry_bound(...)",
            "",
            "Movement functions:",
            "- center_window_on_geometries(...)",
            "- align_window_x(...)",
            "- align_window_y(...)",
            "- shift(...)",
            "- snap_window_edge_to_geometry_bound(...)",
            "- delete_window_and_reindex(...)",
            "- reindex_windows()",
            "",
            "Checking functions:",
            "- check_window_geometries(...)",
            "- check_geometry_in_windows(...)",
            "- check_image_coverage_and_commit_if_ok(...)",
            "",
            "Plot function:",
            "- plot_current_image()",
        ]
    else:
        lines = [
            "Creation functions:",
            "- create_window_centered_on_geometries(poly_ids_1b)",
            "- create_window_adjacent_to_window(ref_window_id, side, align='center')",
            "- create_window_by_geometry_bound(poly_id_1b, window_edge, geometry_bound)",
            "",
            "Movement functions:",
            "- center_window_on_geometries(window_id, poly_ids_1b)",
            "- align_window_x(window_id, ref_window_id, my_edge, ref_edge)",
            "- align_window_y(window_id, ref_window_id, my_edge, ref_edge)",
            "- shift(window_id, axis, amount)",
            "- snap_window_edge_to_geometry_bound(window_id, poly_id_1b, window_edge, geometry_bound)",
            "- delete_window_and_reindex(window_id)",
            "- reindex_windows()",
            "",
            "Checking functions:",
            "- check_window_geometries(window_id)",
            "- check_geometry_in_windows(poly_id_1b)",
            "- check_image_coverage_and_commit_if_ok(expected_width=800, expected_height=600)",
            "",
            "Plot function:",
            "- plot_current_image()",
        ]
    text = "\n".join(lines)
    if print_output:
        print(text)
        return None
    return text


def _terminal_quick_guide():
    """Build concise terminal quick-start text.

    Returns:
        str: Short usage/help summary for terminal users.
    """
    return "\n".join(
        [
            "02.5 Manual Window Tools",
            "",
            "Usage:",
            "  02.5-ManualWindowTools.py [global options] <command> [command options]",
            "",
            "Help:",
            "  --help                  Show all commands and options",
            "  list (ls)               Show available toolbox functions",
            "  list (ls) --full        Show complete function signatures",
            "  show-doc (sd) NAME      Show docstring for one function",
            "  show-doc (sd) --all     Show docstrings for all public functions",
            "",
            "All commands:",
            "  list (ls)               List available toolbox functions",
            "  plot (pl)               Render current QA plot",
            "  plot-bbox (pb)          Render global bbox zoom (00-GLOBAL_BBOX_ZOOM + optional 00-CURRENT_FOCUS_WINDOW)",
            "  check-window (ckw) ID   Check one window geometry status",
            "  check-geometry (ckg) ID Check if one geometry is fully inside window(s) or their union",
            "  check-image (cki)       Check image coverage (no write by default)",
            "  create-centered (crc) IDS Create window centered on geometries",
            "  create-adjacent (cra) ... Create window adjacent to reference",
            "  create-bound (crb) ...  Create window by geometry bound",
            "  move-center (mc) ...    Center an existing window on geometries",
            "  align-x (ax) ...        Align window horizontally",
            "  align-y (ay) ...        Align window vertically",
            "  shift (sh) ...          Shift window on axis x/y",
            "  snap (sn) ...           Snap window edge to geometry bound",
            "  delete-window (dw) ID   Delete one window and reindex",
            "  reindex (rx)            Reindex window keys contiguously",
            "  show-doc (sd) NAME      Show complete docstring for one function",
            "  show-doc (sd) --all     Show all function docstrings",
            "",
            "Global options:",
            "  --image-id N            Override IMAGE_ID",
            "  --width W --height H    Override window size",
            "  --focus-margin R        Override focus zoom margin ratio (default 0.10)",
            "  --json-path PATH        Override JSON file path",
            "  --out-dir PATH          Override output directory",
            "  --confirm-before-change Ask Y/N confirmation before mutating commands",
            "  --no-confirm-before-change Disable confirmation for mutating commands (default)",
            "",
            "Example:",
            "  02.5-ManualWindowTools.py --image-id 7 --width 800 --height 600 check-image",
        ]
    )


def _public_toolbox_function_names():
    """Return sorted public function names defined in this module.

    Returns:
        list[str]: Public function names.
    """
    return sorted(
        name
        for name, obj in globals().items()
        if inspect.isfunction(obj)
        and obj.__module__ == __name__
        and not name.startswith("_")
    )


def _doc_examples_for_function(function_name):
    """Build CLI examples for a documented public function.

    Args:
        function_name (str): Public function name.

    Returns:
        list[tuple[str, str]]: (command, explanation) pairs.
    """
    script = "02.5-ManualWindowTools.py"
    examples = {
        "plot_current_image": [
            (f"{script} plot", "Render the QA image for current IMAGE_ID/window settings."),
            (f"{script} pl", "Alias: render the QA image for current IMAGE_ID/window settings."),
        ],
        "check_window_geometries": [
            (f"{script} check-window 1", "Inspect full/partial/outside polygons for W1."),
            (f"{script} ckw 1", "Alias: inspect full/partial/outside polygons for W1."),
        ],
        "check_geometry_in_windows": [
            (f"{script} check-geometry 3", "Check whether polygon 3 is fully contained in any window and in the union of all windows."),
            (f"{script} ckg 3", "Alias: check whether polygon 3 is fully contained in windows and union."),
        ],
        "check_image_coverage_and_commit_if_ok": [
            (f"{script} check-image", "Validate global coverage without writing any changes."),
            (f"{script} check-image --commit-if-ok", "Validate and persist memberships only when all checks pass."),
            (f"{script} cki", "Alias: validate global coverage without writing any changes."),
        ],
        "create_window_centered_on_geometries": [
            (f"{script} create-centered 1,2,3", "Create a new window centered on polygons 1,2,3."),
            (f"{script} crc 1,2,3", "Alias: create a new window centered on polygons 1,2,3."),
        ],
        "create_window_adjacent_to_window": [
            (f"{script} create-adjacent 1 east --align center", "Create a new window east of W1."),
            (f"{script} cra 1 east --align center", "Alias: create a new window east of W1."),
        ],
        "create_window_by_geometry_bound": [
            (f"{script} create-bound 4 left west", "Create a new window by snapping its left edge to polygon 4 west bound."),
            (f"{script} crb 4 left west", "Alias: create a new window by geometry bound."),
        ],
        "center_window_on_geometries": [
            (f"{script} move-center 2 5,6", "Move W2 to the center of polygons 5 and 6."),
            (f"{script} mc 2 5,6", "Alias: move W2 to the center of polygons 5 and 6."),
        ],
        "align_window_x": [
            (f"{script} align-x 2 1 left right", "Align W2 left edge to W1 right edge."),
            (f"{script} ax 2 1 left right", "Alias: align W2 left edge to W1 right edge."),
        ],
        "align_window_y": [
            (f"{script} align-y 2 1 top bottom", "Align W2 top edge to W1 bottom edge."),
            (f"{script} ay 2 1 top bottom", "Alias: align W2 top edge to W1 bottom edge."),
        ],
        "shift": [
            (f"{script} shift 2 x 12", "Shift W2 by +12 px on x."),
            (f"{script} shift 2 y -8", "Shift W2 by -8 px on y."),
            (f"{script} sh 2 x 12", "Alias: shift W2 by +12 px on x."),
        ],
        "snap_window_edge_to_geometry_bound": [
            (f"{script} snap 2 4 right east", "Move W2 so its right edge matches polygon 4 east bound."),
            (f"{script} sn 2 4 right east", "Alias: move W2 so its right edge matches polygon 4 east bound."),
        ],
        "delete_window_and_reindex": [
            (f"{script} delete-window 3", "Delete W3 and reindex remaining windows."),
            (f"{script} dw 3", "Alias: delete W3 and reindex remaining windows."),
        ],
        "reindex_windows": [
            (f"{script} reindex", "Renumber window keys contiguously in JSON."),
            (f"{script} rx", "Alias: renumber window keys contiguously in JSON."),
        ],
        "list_toolbox_functions": [
            (f"{script} list --full", "Show all toolbox functions with full signatures."),
            (f"{script} ls --full", "Alias: show all toolbox functions with full signatures."),
        ],
        "ensure_image_entry": [
            (f"{script} --show-settings plot", "Run a command that ensures current image entry exists before plotting."),
        ],
    }
    generic = [
        (f"{script} show-doc {function_name}", "Show this function docstring in terminal."),
        (f"{script} {function_name}", "Shortcut: using only the function name prints its docstring."),
    ]
    return examples.get(function_name, []) + generic


def _print_doc_with_examples(function_name, fn):
    """Print a function docstring plus CLI examples.

    Args:
        function_name (str): Public function name.
        fn (callable): Function object.

    Returns:
        int: Process-style return code.
    """
    doc = inspect.getdoc(fn)
    if not doc:
        print(f"No docstring found for {function_name}")
        return 0

    print(doc)
    print("\nCLI examples:")
    for cmd, desc in _doc_examples_for_function(function_name):
        print(f"- {cmd}")
        print(f"  {desc}")
    return 0


def _print_active_settings():
    """Print current active runtime settings used by the CLI.

    Returns:
        None
    """
    print("Active settings:")
    print(f"- IMAGE_ID: {IMAGE_ID}")
    print(f"- WINDOW_WIDTH: {WINDOW_WIDTH}")
    print(f"- WINDOW_HEIGHT: {WINDOW_HEIGHT}")
    print(f"- FOCUS_MARGIN: {FOCUS_MARGIN}")
    print(f"- JSON_IN_PATH: {JSON_IN_PATH}")
    print(f"- JSON_PATH: {JSON_PATH}")
    print(f"- DIR_OUT: {DIR_OUT}")


def _print_default_settings():
    """Print script default settings.

    Returns:
        None
    """
    print("Default settings:")
    print(f"- IMAGE_ID: {DEFAULT_IMAGE_ID}")
    print(f"- WINDOW_WIDTH: {DEFAULT_WINDOW_WIDTH}")
    print(f"- WINDOW_HEIGHT: {DEFAULT_WINDOW_HEIGHT}")
    print(f"- FOCUS_MARGIN: {DEFAULT_FOCUS_MARGIN}")


def _apply_global_overrides(image_id=None, width=None, height=None, focus_margin=None, json_path=None, out_dir=None):
    """Apply global CLI overrides and refresh derived paths.

    Args:
        image_id (int | None): Optional IMAGE_ID override.
        width (int | None): Optional WINDOW_WIDTH override.
        height (int | None): Optional WINDOW_HEIGHT override.
        focus_margin (float | None): Optional focus margin override.
        json_path (str | None): Optional JSON path override.
        out_dir (str | None): Optional output directory override.

    Returns:
        None

    Raises:
        ValueError: If width/height are provided and are not positive.
    """
    global IMAGE_ID, WINDOW_WIDTH, WINDOW_HEIGHT, FOCUS_MARGIN, JSON_IN_PATH, JSON_PATH, DIR_OUT

    if image_id is not None:
        IMAGE_ID = int(image_id)
    if width is not None:
        if int(width) <= 0:
            raise ValueError("--width must be > 0")
        WINDOW_WIDTH = int(width)
    if height is not None:
        if int(height) <= 0:
            raise ValueError("--height must be > 0")
        WINDOW_HEIGHT = int(height)
    if focus_margin is not None:
        if float(focus_margin) < 0:
            raise ValueError("--focus-margin must be >= 0")
        FOCUS_MARGIN = float(focus_margin)

    JSON_IN_PATH = _default_json_in_path(WINDOW_WIDTH, WINDOW_HEIGHT)
    JSON_PATH = _default_json_path(WINDOW_WIDTH, WINDOW_HEIGHT)
    DIR_OUT = _default_out_dir(WINDOW_WIDTH, WINDOW_HEIGHT)

    if json_path is not None:
        JSON_PATH = json_path
    if out_dir is not None:
        DIR_OUT = out_dir

    os.makedirs(DIR_OUT, exist_ok=True)


def _persist_default_settings_in_source(image_id=None, width=None, height=None):
    """Persist selected CLI overrides into script default constants.

    Args:
        image_id (int | None): Optional default IMAGE_ID to persist.
        width (int | None): Optional default WINDOW_WIDTH to persist.
        height (int | None): Optional default WINDOW_HEIGHT to persist.

    Returns:
        bool: True when file content was changed, otherwise False.
    """
    if image_id is None and width is None and height is None:
        return False

    if "__file__" not in globals():
        print("[WARN] Cannot persist default settings while running interactively because __file__ is unavailable.")
        return False

    script_path = os.path.abspath(__file__)
    with open(script_path, encoding="utf-8") as f:
        content = f.read()

    updated = content
    if image_id is not None:
        updated = re.sub(
            r"^DEFAULT_IMAGE_ID\s*=\s*.+$",
            f"DEFAULT_IMAGE_ID = {int(image_id)}",
            updated,
            flags=re.MULTILINE,
            count=1,
        )
    if width is not None:
        updated = re.sub(
            r"^DEFAULT_WINDOW_WIDTH\s*=\s*.+$",
            f"DEFAULT_WINDOW_WIDTH = {int(width)}",
            updated,
            flags=re.MULTILINE,
            count=1,
        )
    if height is not None:
        updated = re.sub(
            r"^DEFAULT_WINDOW_HEIGHT\s*=\s*.+$",
            f"DEFAULT_WINDOW_HEIGHT = {int(height)}",
            updated,
            flags=re.MULTILINE,
            count=1,
        )

    if updated == content:
        return False

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(updated)
    return True


def _doc_alias_to_function_name(alias):
    """Map CLI command aliases to public function names.

    Args:
        alias (str): Single-token alias typed by user.

    Returns:
        str | None: Function name when alias is recognized.
    """
    mapping = {
        "list": "list_toolbox_functions",
        "ls": "list_toolbox_functions",
        "plot": "plot_current_image",
        "pl": "plot_current_image",
        "plot-bbox": "plot_global_bounding_box_zoom",
        "pb": "plot_global_bounding_box_zoom",
        "check-window": "check_window_geometries",
        "ckw": "check_window_geometries",
        "check-geometry": "check_geometry_in_windows",
        "ckg": "check_geometry_in_windows",
        "check-image": "check_image_coverage_and_commit_if_ok",
        "cki": "check_image_coverage_and_commit_if_ok",
        "create-centered": "create_window_centered_on_geometries",
        "crc": "create_window_centered_on_geometries",
        "create-adjacent": "create_window_adjacent_to_window",
        "cra": "create_window_adjacent_to_window",
        "create-bound": "create_window_by_geometry_bound",
        "crb": "create_window_by_geometry_bound",
        "move-center": "center_window_on_geometries",
        "mc": "center_window_on_geometries",
        "align-x": "align_window_x",
        "ax": "align_window_x",
        "align-y": "align_window_y",
        "ay": "align_window_y",
        "shift": "shift",
        "sh": "shift",
        "snap": "snap_window_edge_to_geometry_bound",
        "sn": "snap_window_edge_to_geometry_bound",
        "delete-window": "delete_window_and_reindex",
        "dw": "delete_window_and_reindex",
        "reindex": "reindex_windows",
        "rx": "reindex_windows",
    }
    return mapping.get(alias)


def _normalize_cli_command(command_name):
    """Map short CLI aliases to canonical command names.

    Args:
        command_name (str): Raw command parsed from CLI.

    Returns:
        str: Canonical command name.
    """
    alias_to_command = {
        "ls": "list",
        "pl": "plot",
        "pb": "plot-bbox",
        "ckw": "check-window",
        "ckg": "check-geometry",
        "cki": "check-image",
        "crc": "create-centered",
        "cra": "create-adjacent",
        "crb": "create-bound",
        "mc": "move-center",
        "ax": "align-x",
        "ay": "align-y",
        "sh": "shift",
        "sn": "snap",
        "dw": "delete-window",
        "rx": "reindex",
        "sd": "show-doc",
    }
    return alias_to_command.get(command_name, command_name)


def _handle_show_settings_only(argv):
    """Handle the no-command settings flow for CLI users.

    This allows calls like:
    - 02.5-ManualWindowTools.py --show-settings
    - 02.5-ManualWindowTools.py --image-id 7 --show-settings

    Args:
        argv (list[str]): CLI args excluding program name.

    Returns:
        bool: True when settings were printed and CLI should exit early.
    """
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--image-id", type=int)
    pre.add_argument("--width", type=int)
    pre.add_argument("--height", type=int)
    pre.add_argument("--focus-margin", type=float)
    pre.add_argument("--json-path", type=str)
    pre.add_argument("--out-dir", type=str)
    pre.add_argument("--show-settings", action="store_true")
    ns, remaining = pre.parse_known_args(argv)

    if not ns.show_settings:
        return False
    if remaining:
        return False

    _apply_global_overrides(
        image_id=ns.image_id,
        width=ns.width,
        height=ns.height,
        focus_margin=ns.focus_margin,
        json_path=ns.json_path,
        out_dir=ns.out_dir,
    )
    _print_active_settings()
    return True


def _confirm_continue_for_change(command_name):
    """Ask user confirmation before executing a mutating command.

    Args:
        command_name (str): CLI command that is about to run.

    Returns:
        bool: True to continue, False to cancel.
    """
    _print_default_settings()
    _print_active_settings()
    answer = input(f"Proceed with '{command_name}'? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _build_cli_parser():
    """Build CLI parser for command-line toolbox usage.

    Returns:
        argparse.ArgumentParser: Configured parser with subcommands.
    """
    parser = argparse.ArgumentParser(
        description="02.5 manual window toolbox CLI",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  02.5-ManualWindowTools.py list --full\n"
            "  02.5-ManualWindowTools.py show-doc create_window_centered_on_geometries\n"
            "  02.5-ManualWindowTools.py --image-id 7 --width 800 --height 600 check-image\n"
            "  02.5-ManualWindowTools.py --image-id 7 plot"
        ),
    )
    parser.add_argument(
        "--image-id",
        type=int,
        help="Override IMAGE_ID for this command run",
    )
    parser.add_argument(
        "--width",
        type=int,
        help="Override WINDOW_WIDTH for this command run",
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Override WINDOW_HEIGHT for this command run",
    )
    parser.add_argument(
        "--focus-margin",
        type=float,
        help="Override focus zoom margin ratio (default: 0.10)",
    )
    parser.add_argument(
        "--json-path",
        type=str,
        help="Override manual windows JSON path for this command run",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        help="Override QA output directory for this command run",
    )
    confirm_group = parser.add_mutually_exclusive_group()
    confirm_group.add_argument(
        "--confirm-before-change",
        dest="confirm_before_change",
        action="store_true",
        help="Ask Y/N confirmation before commands that may change image windows/JSON",
    )
    confirm_group.add_argument(
        "--no-confirm-before-change",
        dest="confirm_before_change",
        action="store_false",
        help="Run mutating commands without Y/N confirmation (default)",
    )
    parser.set_defaults(confirm_before_change=False)
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Show active IMAGE_ID/window size/paths and continue (or exit when used alone)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", aliases=["ls"], help="(ls) Return available toolbox functions and optionally print them.")
    p_list.add_argument("--full", action="store_true", help="Show full signatures")

    sub.add_parser("plot", aliases=["pl"], help="(pl) Render a QA plot for the current image and window layout.")

    p_plot_bbox = sub.add_parser(
        "plot-bbox",
        aliases=["pb"],
        help="(pb) Plot global bounding-box zoom for selected windows/geometries.",
    )
    p_plot_bbox.add_argument(
        "--window-ids",
        type=str,
        help="Optional comma-separated window IDs (1-based), e.g. 1,2,3",
    )
    p_plot_bbox.add_argument(
        "--poly-ids",
        type=str,
        help="Optional comma-separated polygon IDs (1-based), e.g. 4,5",
    )
    p_plot_bbox.add_argument(
        "--no-current-focus",
        action="store_true",
        help="Do not refresh 00-CURRENT_FOCUS_WINDOW.png",
    )

    p_check_w = sub.add_parser("check-window", aliases=["ckw"], help="(ckw) Check containment/intersection status for one window.")
    p_check_w.add_argument("window_id", type=int)

    p_check_g = sub.add_parser(
        "check-geometry",
        aliases=["ckg"],
        help="(ckg) Check whether one geometry is fully inside a window or window union.",
    )
    p_check_g.add_argument("poly_id", type=int)

    p_check_i = sub.add_parser("check-image", aliases=["cki"], help="(cki) Check global coverage and commit memberships only when valid.")
    p_check_i.add_argument("--expected-width", type=int, default=800)
    p_check_i.add_argument("--expected-height", type=int, default=600)
    p_check_i.add_argument(
        "--commit-if-ok",
        action="store_true",
        help="Persist memberships only when all checks pass",
    )

    p_create_center = sub.add_parser("create-centered", aliases=["crc"], help="(crc) Create a new window centered on selected geometries.")
    p_create_center.add_argument("poly_ids", help="Comma-separated poly IDs, e.g. 1,2,3")

    p_create_adj = sub.add_parser("create-adjacent", aliases=["cra"], help="(cra) Create a new window adjacent to a reference window.")
    p_create_adj.add_argument("ref_window_id", type=int)
    p_create_adj.add_argument(
        "side",
        type=lambda v: _normalize_direction_token(v, {"east", "west", "north", "south"}),
        help="Reference side: east|west|north|south (aliases: e|w|n|s)",
    )
    p_create_adj.add_argument(
        "--align",
        default="center",
        help=(
            "Alignment for side: east/west -> top|center|bottom (aliases: t|b); "
            "north/south -> left|center|right (aliases: l|r)"
        ),
    )

    p_create_bound = sub.add_parser("create-bound", aliases=["crb"], help="(crb) Create a new window by matching one edge to a geometry bound.")
    p_create_bound.add_argument("poly_id", type=int)
    p_create_bound.add_argument(
        "window_edge",
        type=lambda v: _normalize_direction_token(v, {"left", "right", "top", "bottom"}),
        help="Window edge: left|right|top|bottom (aliases: l|r|t|b)",
    )
    p_create_bound.add_argument(
        "geometry_bound",
        type=lambda v: _normalize_direction_token(v, {"west", "east", "north", "south"}),
        help="Geometry bound: west|east|north|south (aliases: w|e|n|s)",
    )

    p_move_center = sub.add_parser("move-center", aliases=["mc"], help="(mc) Move an existing window to the center of selected geometries.")
    p_move_center.add_argument("window_id", type=int)
    p_move_center.add_argument("poly_ids", help="Comma-separated poly IDs, e.g. 1,2,3")

    p_align_x = sub.add_parser("align-x", aliases=["ax"], help="(ax) Align one window horizontally to another by edge pairing.")
    p_align_x.add_argument("window_id", type=int)
    p_align_x.add_argument("ref_window_id", type=int)
    p_align_x.add_argument(
        "my_edge",
        type=lambda v: _normalize_direction_token(v, {"left", "right"}),
        help="My edge: left|right (aliases: l|r)",
    )
    p_align_x.add_argument(
        "ref_edge",
        type=lambda v: _normalize_direction_token(v, {"left", "right"}),
        help="Reference edge: left|right (aliases: l|r)",
    )
    p_align_x.add_argument(
        "--shift",
        type=int,
        default=0,
        help="Optional extra horizontal shift in pixels after alignment",
    )

    p_align_y = sub.add_parser("align-y", aliases=["ay"], help="(ay) Align one window vertically to another by edge pairing.")
    p_align_y.add_argument("window_id", type=int)
    p_align_y.add_argument("ref_window_id", type=int)
    p_align_y.add_argument(
        "my_edge",
        type=lambda v: _normalize_direction_token(v, {"top", "bottom"}),
        help="My edge: top|bottom (aliases: t|b)",
    )
    p_align_y.add_argument(
        "ref_edge",
        type=lambda v: _normalize_direction_token(v, {"top", "bottom"}),
        help="Reference edge: top|bottom (aliases: t|b)",
    )
    p_align_y.add_argument(
        "--shift",
        type=int,
        default=0,
        help="Optional extra vertical shift in pixels after alignment",
    )

    p_shift = sub.add_parser("shift", aliases=["sh"], help="(sh) Shift one existing window on one axis by a pixel amount.")
    p_shift.add_argument("window_id", type=int)
    p_shift.add_argument("axis", choices=["x", "y"])
    p_shift.add_argument("amount", type=int, help="Shift amount in pixels on selected axis")

    p_snap = sub.add_parser("snap", aliases=["sn"], help="(sn) Move an existing window by snapping one edge to one geometry bound.")
    p_snap.add_argument("window_id", type=int)
    p_snap.add_argument("poly_id", type=int)
    p_snap.add_argument(
        "window_edge",
        type=lambda v: _normalize_direction_token(v, {"left", "right", "top", "bottom"}),
        help="Window edge: left|right|top|bottom (aliases: l|r|t|b)",
    )
    p_snap.add_argument(
        "geometry_bound",
        type=lambda v: _normalize_direction_token(v, {"west", "east", "north", "south"}),
        help="Geometry bound: west|east|north|south (aliases: w|e|n|s)",
    )
    p_snap.add_argument(
        "--margin",
        type=int,
        default=1,
        help="Pixel gap between window edge and geometry bound (default: 1)",
    )

    p_delete_window = sub.add_parser("delete-window", aliases=["dw"], help="(dw) Delete one window by ID and reindex remaining windows contiguously.")
    p_delete_window.add_argument("window_id", type=int)

    sub.add_parser("reindex", aliases=["rx"], help="(rx) Reindex windows to contiguous keys while preserving key order.")

    p_show_doc = sub.add_parser("show-doc", aliases=["sd"], help="(sd) Show complete docstring for one function.")
    p_show_doc.add_argument(
        "function_name",
        type=str,
        nargs="?",
        help="Function name, for example create_window_centered_on_geometries",
    )
    p_show_doc.add_argument(
        "--all",
        action="store_true",
        help="Print docstrings for all public toolbox functions",
    )

    return parser


def _run_cli(argv):
    """Execute toolbox command-line actions.

    Args:
        argv (list[str]): CLI arguments excluding program name.

    Returns:
        int: Process exit code.
    """
    if _handle_show_settings_only(argv):
        return 0

    if len(argv) == 1 and not argv[0].startswith("-"):
        token = argv[0]

        # Keep no-argument CLI aliases executable as commands.
        no_arg_alias_commands = {"list", "ls", "plot", "pl", "check-image", "cki", "reindex", "rx"}
        if token in no_arg_alias_commands:
            token = None

        if token is None:
            pass
        else:
            fn_name = _doc_alias_to_function_name(token) or token
            fn = globals().get(fn_name)
            if inspect.isfunction(fn) and fn.__module__ == __name__ and not argv[0].startswith("_"):
                return _print_doc_with_examples(fn_name, fn)

    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    args.command = _normalize_cli_command(args.command)

    _apply_global_overrides(
        image_id=args.image_id,
        width=args.width,
        height=args.height,
        focus_margin=args.focus_margin,
        json_path=args.json_path,
        out_dir=args.out_dir,
    )

    if _persist_default_settings_in_source(
        image_id=args.image_id,
        width=args.width,
        height=args.height,
    ):
        print("Updated source defaults: IMAGE_ID/WINDOW_WIDTH/WINDOW_HEIGHT")

    if args.show_settings:
        _print_active_settings()

    mutating_commands = {
        "create-centered",
        "create-adjacent",
        "create-bound",
        "move-center",
        "align-x",
        "align-y",
        "shift",
        "snap",
        "delete-window",
        "reindex",
    }
    if args.confirm_before_change and args.command in mutating_commands:
        if not _confirm_continue_for_change(args.command):
            print("Cancelled by user.")
            return 0

    if args.command == "list":
        list_toolbox_functions(print_output=True, compact=not args.full)
        return 0
    if args.command == "plot":
        outputs = render_all_outputs_for_current_image(
            focus_command_name="plot",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "plot-bbox":
        outputs = render_all_outputs_for_current_image(
            focus_command_name="plot-bbox",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "check-window":
        check_window_geometries(args.window_id)
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.window_id],
            focus_command_name="check-window",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "check-geometry":
        check_geometry_in_windows(args.poly_id)
        outputs = render_all_outputs_for_current_image(
            focus_poly_ids=[args.poly_id],
            focus_command_name="check-geometry",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "check-image":
        result = check_image_coverage_and_commit_if_ok(
            expected_width=args.expected_width,
            expected_height=args.expected_height,
            commit_if_ok=args.commit_if_ok,
        )
        outputs = render_all_outputs_for_current_image(
            focus_poly_ids=result.get("not_fully_in_union", []),
            focus_command_name="check-image",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "create-centered":
        poly_ids = _parse_int_list(args.poly_ids)
        new_id = create_window_centered_on_geometries(poly_ids)
        print(new_id)
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[new_id],
            focus_poly_ids=poly_ids,
            focus_command_name="create-centered",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "create-adjacent":
        align_raw = str(args.align).strip().lower()
        if args.side in {"east", "west"}:
            align = _normalize_direction_token(align_raw, {"top", "center", "bottom"})
        else:
            align = _normalize_direction_token(align_raw, {"left", "center", "right"})

        new_id = create_window_adjacent_to_window(args.ref_window_id, args.side, align=align)
        print(new_id)
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.ref_window_id, new_id],
            focus_command_name="create-adjacent",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "create-bound":
        new_id = create_window_by_geometry_bound(args.poly_id, args.window_edge, args.geometry_bound)
        print(new_id)
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[new_id],
            focus_poly_ids=[args.poly_id],
            focus_command_name="create-bound",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "move-center":
        poly_ids = _parse_int_list(args.poly_ids)
        center_window_on_geometries(args.window_id, poly_ids)
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.window_id],
            focus_poly_ids=poly_ids,
            focus_command_name="move-center",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "align-x":
        align_window_x(
            args.window_id,
            args.ref_window_id,
            args.my_edge,
            args.ref_edge,
            shift_px=args.shift,
        )
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.window_id, args.ref_window_id],
            focus_command_name="align-x",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "align-y":
        align_window_y(
            args.window_id,
            args.ref_window_id,
            args.my_edge,
            args.ref_edge,
            shift_px=args.shift,
        )
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.window_id, args.ref_window_id],
            focus_command_name="align-y",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "shift":
        shift(
            args.window_id,
            args.axis,
            args.amount,
        )
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.window_id],
            focus_command_name="shift",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "snap":
        snap_window_edge_to_geometry_bound(
            args.window_id,
            args.poly_id,
            args.window_edge,
            args.geometry_bound,
            margin_px=args.margin,
        )
        outputs = render_all_outputs_for_current_image(
            focus_window_ids=[args.window_id],
            focus_poly_ids=[args.poly_id],
            focus_command_name="snap",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "delete-window":
        delete_window_and_reindex(args.window_id)
        outputs = render_all_outputs_for_current_image(
            focus_command_name="delete-window",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "reindex":
        reindex_windows()
        outputs = render_all_outputs_for_current_image(
            focus_command_name="reindex",
        )
        print(outputs["qa"])
        print(outputs["image_named"])
        if outputs["current_focus"]:
            print(outputs["current_focus"])
        return 0
    if args.command == "show-doc":
        if args.all:
            names = _public_toolbox_function_names()
            for i, name in enumerate(names):
                if i > 0:
                    print("\n" + "=" * 80)
                print(f"{name}\n{'-' * len(name)}")
                _print_doc_with_examples(name, globals()[name])
            return 0
        if not args.function_name:
            raise ValueError("Provide function_name or use --all")
        fn = globals().get(args.function_name)
        if fn is None or not callable(fn):
            raise ValueError(f"Function not found or not callable: {args.function_name}")
        return _print_doc_with_examples(args.function_name, fn)

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(_run_cli(sys.argv[1:]))

    print(_terminal_quick_guide())
