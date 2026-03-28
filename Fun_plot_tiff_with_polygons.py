#!/usr/bin/env python3

import os
import json
import importlib
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from shapely.geometry import box

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
os.chdir(SCRIPT_DIR)

import Config as Cfg  # nopep8

importlib.reload(Cfg)

DEFAULT_TARGET_W = 800
DEFAULT_TARGET_H = 600


def _pipeline_size_dir(target_w, target_h):
    return os.path.join(
        'dataout',
        '02.1-DS_by_manual_windows',
        f'{int(target_w)}x{int(target_h)}_windows',
    )


def _default_out_dir(target_w, target_h):
    return os.path.join(_pipeline_size_dir(target_w, target_h), '1')


def _default_windows_json_path(target_w, target_h):
    return os.path.join(_pipeline_size_dir(target_w, target_h), '1', 'Created_windows.json')


DIR_OUT = _default_out_dir(DEFAULT_TARGET_W, DEFAULT_TARGET_H)
os.makedirs(DIR_OUT, exist_ok=True)

LAND_PATH = os.path.join(
    os.path.expanduser('~'),
    'ProjData',
    'Oil_Spill',
    'Cantarell_Beisl',
    'Vetores',
    'Coastline',
    'Land_&_Coastline.shp',
)

MANUAL_WINDOWS_JSON = _default_windows_json_path(DEFAULT_TARGET_W, DEFAULT_TARGET_H)


def load_manual_windows(json_path):
    """Load manual window placements from JSON indexed by image ID."""
    if not os.path.exists(json_path):
        return {}

    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for image_id, image_cfg in data.get('images', {}).items():
        windows = []
        for window_key, window_cfg in sorted(
            image_cfg.get('windows', {}).items(),
            key=lambda kv: int(kv[0]),
        ):
            windows.append(
                {
                    'window_id': int(window_key) + 1,
                    'row_off': int(window_cfg['row_off']),
                    'col_off': int(window_cfg['col_off']),
                    'covered': set(window_cfg.get('indices', [])),
                }
            )
        result[int(image_id)] = windows

    return result


MANUAL_WINDOWS_BY_IMAGE = load_manual_windows(MANUAL_WINDOWS_JSON)


def build_id_to_tiff_path(tiff_paths):
    """Return a mapping from numeric image ID to TIFF path."""
    mapping = {}
    for path in tiff_paths:
        bname = os.path.basename(path)
        id_tiff = int(bname.split(' ')[0])
        mapping[id_tiff] = path
    return mapping


def clamped_window_from_center(src, center_x, center_y, width_px, height_px):
    """Create a window centered at a point and clamp it to raster bounds."""
    c_row, c_col = src.index(center_x, center_y)
    col_off = int(round(c_col - width_px / 2))
    row_off = int(round(c_row - height_px / 2))
    col_off = max(0, min(col_off, src.width - width_px))
    row_off = max(0, min(row_off, src.height - height_px))
    return row_off, col_off


def window_bounds_geo(src, row_off, col_off, width_px, height_px):
    """Convert pixel window offsets and size to geographic bounds."""
    left, top = src.xy(row_off, col_off, offset='ul')
    right, bottom = src.xy(row_off + height_px, col_off + width_px, offset='ul')
    return left, bottom, right, top


def choose_window_label_position(left, bottom, right, top, centroid_points, used_positions):
    """Pick a window-label corner far from polygon labels and prior window labels."""
    width = right - left
    height = top - bottom
    x_pad = width * 0.02
    y_pad = height * 0.03

    candidates = [
        (left + x_pad, top - y_pad, 'left', 'top'),
        (right - x_pad, top - y_pad, 'right', 'top'),
        (left + x_pad, bottom + y_pad, 'left', 'bottom'),
        (right - x_pad, bottom + y_pad, 'right', 'bottom'),
    ]

    if not centroid_points:
        return candidates[0]

    best = None
    for cand_x, cand_y, ha, va in candidates:
        min_centroid_dist2 = min(
            (cand_x - cx) ** 2 + (cand_y - cy) ** 2
            for cx, cy in centroid_points
        )
        if used_positions:
            min_used_dist2 = min(
                (cand_x - ux) ** 2 + (cand_y - uy) ** 2
                for ux, uy in used_positions
            )
        else:
            min_used_dist2 = float('inf')

        score = (min_centroid_dist2, min_used_dist2)
        if best is None or score > best[0]:
            best = (score, (cand_x, cand_y, ha, va))

    return best[1]


def polygon_intersects_window(src, geom, row_off, col_off, width_px, height_px):
    """Check whether a geometry intersects a raster window footprint."""
    left, bottom, right, top = window_bounds_geo(src, row_off, col_off, width_px, height_px)
    return geom.intersects(box(left, bottom, right, top))


def select_non_overlapping_windows(src, gdf_plot, width_px, height_px):
    """
    Build one window per polygon centered on centroid, then resolve overlaps
    with minimal displacement while keeping windows inside image bounds.

    Returns (windows, covered_indices, uncovered_indices).
    """
    n_polys = len(gdf_plot)
    if n_polys == 0:
        return [], set(), set()

    cent_px = []
    desired = []
    for i in range(n_polys):
        cent = gdf_plot.geometry.iloc[i].centroid
        c_row, c_col = src.index(cent.x, cent.y)
        row_off, col_off = clamped_window_from_center(src, cent.x, cent.y, width_px, height_px)
        cent_px.append((c_row, c_col))
        desired.append((row_off, col_off))

    def overlaps(a_row, a_col, b_row, b_col):
        a_bottom = a_row + height_px
        a_right = a_col + width_px
        b_bottom = b_row + height_px
        b_right = b_col + width_px
        inter_h = min(a_bottom, b_bottom) - max(a_row, b_row)
        inter_w = min(a_right, b_right) - max(a_col, b_col)
        return inter_h > 0 and inter_w > 0

    def centroid_inside(row_off, col_off, c_row, c_col):
        return (row_off <= c_row < row_off + height_px) and (col_off <= c_col < col_off + width_px)

    def in_bounds(row_off, col_off):
        ok_row = 0 <= row_off <= (src.height - height_px)
        ok_col = 0 <= col_off <= (src.width - width_px)
        return ok_row and ok_col

    placed = []
    order = list(range(n_polys))

    for i in order:
        d_row, d_col = desired[i]
        c_row, c_col = cent_px[i]
        cur_row, cur_col = d_row, d_col

        # Iterative minimal-separation adjustment.
        for _ in range(120):
            overlap_with = None
            for p in placed:
                if overlaps(cur_row, cur_col, p["row_off"], p["col_off"]):
                    overlap_with = p
                    break

            if overlap_with is None:
                break

            orow = overlap_with["row_off"]
            ocol = overlap_with["col_off"]

            # Candidate displacements to separate from overlapping window.
            cand_positions = [
                (cur_row, ocol - width_px),
                (cur_row, ocol + width_px),
                (orow - height_px, cur_col),
                (orow + height_px, cur_col),
            ]

            valid = []
            for rr, cc in cand_positions:
                rr = max(0, min(rr, src.height - height_px))
                cc = max(0, min(cc, src.width - width_px))
                if not in_bounds(rr, cc):
                    continue
                if not centroid_inside(rr, cc, c_row, c_col):
                    continue
                if any(overlaps(rr, cc, p2["row_off"], p2["col_off"]) for p2 in placed if p2 is not overlap_with):
                    continue
                dist = (rr - d_row) ** 2 + (cc - d_col) ** 2
                valid.append((dist, rr, cc))

            if not valid:
                # Local spiral-like search around desired center to keep it close.
                found = None
                for rad in range(10, 2001, 10):
                    ring = [
                        (d_row - rad, d_col),
                        (d_row + rad, d_col),
                        (d_row, d_col - rad),
                        (d_row, d_col + rad),
                        (d_row - rad, d_col - rad),
                        (d_row - rad, d_col + rad),
                        (d_row + rad, d_col - rad),
                        (d_row + rad, d_col + rad),
                    ]
                    for rr, cc in ring:
                        rr = max(0, min(rr, src.height - height_px))
                        cc = max(0, min(cc, src.width - width_px))
                        if not centroid_inside(rr, cc, c_row, c_col):
                            continue
                        if any(overlaps(rr, cc, p2["row_off"], p2["col_off"]) for p2 in placed):
                            continue
                        found = (rr, cc)
                        break
                    if found is not None:
                        break

                if found is None:
                    # Last resort: keep desired (may still overlap in pathological cases).
                    cur_row, cur_col = d_row, d_col
                    break

                cur_row, cur_col = found
                break

            valid.sort(key=lambda t: t[0])
            _, cur_row, cur_col = valid[0]

        placed.append({"poly_idx": i, "row_off": cur_row, "col_off": cur_col})

    # Group polygons sharing the same final window.
    by_window = {}
    for p in placed:
        key = (p["row_off"], p["col_off"])
        by_window.setdefault(key, set()).add(p["poly_idx"])

    windows = []
    for (row_off, col_off), covered_set in sorted(by_window.items()):
        windows.append({"row_off": row_off, "col_off": col_off, "covered": covered_set})

    # Greedy merge pass: combine windows when one in-bounds non-overlapping
    # 800x600 window can cover all centroids from both windows.
    def feasible_merged_window(poly_set, row_target, col_target):
        rows = [cent_px[k][0] for k in poly_set]
        cols = [cent_px[k][1] for k in poly_set]
        min_r, max_r = min(rows), max(rows)
        min_c, max_c = min(cols), max(cols)

        # Required feasibility intervals to keep all centroids inside.
        row_low = max(0, max_r - height_px + 1)
        row_high = min(src.height - height_px, min_r)
        col_low = max(0, max_c - width_px + 1)
        col_high = min(src.width - width_px, min_c)
        if row_low > row_high or col_low > col_high:
            return None

        # Candidate positions near current windows first.
        cand_row = int(max(row_low, min(row_target, row_high)))
        cand_col = int(max(col_low, min(col_target, col_high)))
        candidates = [
            (cand_row, cand_col),
            (row_low, col_low),
            (row_low, col_high),
            (row_high, col_low),
            (row_high, col_high),
            (row_low, cand_col),
            (row_high, cand_col),
            (cand_row, col_low),
            (cand_row, col_high),
        ]

        # Return best unique candidate by distance to target.
        seen = set()
        unique = []
        for rr, cc in candidates:
            key = (int(rr), int(cc))
            if key in seen:
                continue
            seen.add(key)
            unique.append(key)

        unique.sort(key=lambda rc: (rc[0] - row_target) ** 2 + (rc[1] - col_target) ** 2)
        return unique

    merged = True
    while merged and len(windows) > 1:
        merged = False
        i = 0
        while i < len(windows) and not merged:
            j = i + 1
            while j < len(windows) and not merged:
                # Only try to merge windows that currently overlap.
                if not overlaps(
                    windows[i]["row_off"], windows[i]["col_off"],
                    windows[j]["row_off"], windows[j]["col_off"],
                ):
                    j += 1
                    continue

                union_set = windows[i]["covered"] | windows[j]["covered"]
                row_target = int(round((windows[i]["row_off"] + windows[j]["row_off"]) / 2.0))
                col_target = int(round((windows[i]["col_off"] + windows[j]["col_off"]) / 2.0))
                candidates = feasible_merged_window(union_set, row_target, col_target)

                if candidates is None:
                    j += 1
                    continue

                placed_merge = None
                for rr, cc in candidates:
                    if not in_bounds(rr, cc):
                        continue
                    placed_merge = (rr, cc)
                    break

                if placed_merge is None:
                    j += 1
                    continue

                rr, cc = placed_merge
                windows[i] = {"row_off": rr, "col_off": cc, "covered": union_set}
                del windows[j]
                merged = True

            i += 1

    covered = set(range(n_polys))
    uncovered = set()
    return windows, covered, uncovered


def plot_tiff_with_polygons(
    tiff_path,
    gdf_img,
    out_png,
    gdf_land,
    target_w=DEFAULT_TARGET_W,
    target_h=DEFAULT_TARGET_H,
    manual_windows_by_image=None,
):
    """Render a PNG with polygons, optional land overlay, and configurable windows."""
    width_px = int(target_w)
    height_px = int(target_h)
    manual_windows = MANUAL_WINDOWS_BY_IMAGE if manual_windows_by_image is None else manual_windows_by_image

    with rasterio.open(tiff_path) as src:
        image_id = int(os.path.basename(tiff_path).split(' ')[0])
        bounds = src.bounds
        gdf_plot = gdf_img.copy()
        if gdf_plot.crs != src.crs:
            gdf_plot = gdf_plot.to_crs(src.crs)

        fig, ax = plt.subplots(figsize=(14, 10), dpi=140)
        ax.set_aspect('equal', adjustable='box')

        # Image footprint
        ax.add_patch(
            Rectangle(
                (bounds.left, bounds.bottom),
                bounds.right - bounds.left,
                bounds.top - bounds.bottom,
                linewidth=1.2,
                edgecolor='#4A90E2',
                facecolor='none',
                linestyle='-',
            )
        )

        # Continent overlay (if intersects)
        footprint = gpd.GeoDataFrame({'geometry': [box(bounds.left, bounds.bottom, bounds.right, bounds.top)]}, crs=src.crs)
        land_plot = gdf_land
        if land_plot.crs != src.crs:
            land_plot = land_plot.to_crs(src.crs)
        land_in_img = gpd.overlay(land_plot[['geometry']].copy(), footprint, how='intersection')
        if len(land_in_img) > 0:
            land_in_img.plot(
                ax=ax,
                facecolor='#2E8B57',
                edgecolor='#006400',
                linewidth=0.8,
                alpha=0.35,
                zorder=1,
            )
            land_proj = land_in_img.to_crs(3857)
            largest_idx = land_proj.area.idxmax()
            p = land_in_img.loc[largest_idx, 'geometry'].representative_point()
            ax.text(
                p.x,
                p.y,
                'CONTINENT',
                color='#006400',
                fontsize=12,
                fontweight='bold',
                ha='center',
                va='center',
                zorder=2,
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#006400', lw=1.0, alpha=0.9),
            )

        if len(gdf_plot) > 0:
            # Polygons
            gdf_plot.plot(
                ax=ax,
                facecolor='none',
                edgecolor='#FFD400',
                linewidth=1.1,
                alpha=1.0,
                zorder=4,
            )

            # Keep polygon numbering visible with compact labels.
            for idx_local, (_, row) in enumerate(gdf_plot.iterrows(), start=1):
                c = row.geometry.centroid
                ax.text(
                    c.x,
                    c.y,
                    str(idx_local),
                    color='white',
                    fontsize=8,
                    fontweight='bold',
                    ha='center',
                    va='center',
                    zorder=7,
                    bbox=dict(boxstyle='round,pad=0.12', fc='black', ec='white', lw=0.5, alpha=0.75),
                )

            # Global bbox of polygons
            minx, miny, maxx, maxy = gdf_plot.total_bounds
            ax.add_patch(
                Rectangle(
                    (minx, miny),
                    maxx - minx,
                    maxy - miny,
                    linewidth=1.2,
                    edgecolor='#FF2D55',
                    facecolor='none',
                    linestyle='--',
                    zorder=5,
                )
            )

            # Use manual windows when present; otherwise fall back to automatic placement.
            if image_id in manual_windows:
                windows = manual_windows[image_id]
                covered_idx = set()
                for window in windows:
                    covered_idx |= window['covered']
                uncovered_idx = set(range(len(gdf_plot))) - covered_idx
            else:
                windows, covered_idx, uncovered_idx = select_non_overlapping_windows(src, gdf_plot, width_px, height_px)
            win_color = '#8A2BE2'
            centroid_points = [
                (row.geometry.centroid.x, row.geometry.centroid.y)
                for _, row in gdf_plot.iterrows()
            ]
            used_window_label_positions = []
            for i, w in enumerate(windows, start=1):
                left, bottom, right, top = window_bounds_geo(src, w['row_off'], w['col_off'], width_px, height_px)
                ax.add_patch(
                    Rectangle(
                        (left, bottom),
                        right - left,
                        top - bottom,
                        linewidth=1.0,
                        edgecolor=win_color,
                        facecolor='none',
                        linestyle='-.',
                        zorder=6,
                    )
                )
                window_centroids = [
                    (cx, cy)
                    for cx, cy in centroid_points
                    if left <= cx <= right and bottom <= cy <= top
                ]
                label_x, label_y, label_ha, label_va = choose_window_label_position(
                    left,
                    bottom,
                    right,
                    top,
                    window_centroids,
                    used_window_label_positions,
                )
                used_window_label_positions.append((label_x, label_y))
                ax.text(
                    label_x,
                    label_y,
                    f"W{w.get('window_id', i)}",
                    color=win_color,
                    fontsize=7,
                    fontweight='bold',
                    ha=label_ha,
                    va=label_va,
                    zorder=7,
                    bbox=dict(boxstyle='round,pad=0.12', fc='white', ec=win_color, lw=0.8, alpha=0.9),
                )

            continent_note = 'YES' if len(land_in_img) > 0 else 'NO'
            ax.set_title(
                f'TIFF {image_id:02d} | Polygons: {len(gdf_plot)} | '
                f'Windows: {len(windows)} | Covered: {len(covered_idx)} | Uncovered: {len(uncovered_idx)} | '
                f'Continent: {continent_note}',
                fontsize=13,
                fontweight='bold',
            )
        else:
            ax.set_title(
                f'TIFF {image_id:02d} | Polygons: 0',
                fontsize=13,
                fontweight='bold',
            )

        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.grid(True, linestyle=':', linewidth=0.6, alpha=0.6)
        ax.set_xlim(bounds.left, bounds.right)
        ax.set_ylim(bounds.bottom, bounds.top)

        # Explicit legend entries to keep labels readable and stable.
        legend_handles = [
            Line2D([0], [0], color='#4A90E2', lw=1.2, label='Image footprint'),
            Line2D([0], [0], color='#FFD400', lw=1.1, label='Polygons'),
            Line2D([0], [0], color='#FF2D55', lw=1.2, ls='--', label='Global polygon bbox'),
            Line2D([0], [0], color='#8A2BE2', lw=1.0, ls='-.', label='Panels'),
        ]
        if len(land_in_img) > 0:
            legend_handles.append(Line2D([0], [0], color='#006400', lw=0.8, label='Continent'))
        ax.legend(handles=legend_handles, loc='lower left', fontsize=9)

        plt.tight_layout()
        plt.savefig(out_png)
        plt.close(fig)


def plot_image_polygons_800x600(tiff_path, gdf_img, out_png, gdf_land):
    """Backward-compatible wrapper using default 800x600 settings."""
    return plot_tiff_with_polygons(
        tiff_path=tiff_path,
        gdf_img=gdf_img,
        out_png=out_png,
        gdf_land=gdf_land,
        target_w=DEFAULT_TARGET_W,
        target_h=DEFAULT_TARGET_H,
        manual_windows_by_image=MANUAL_WINDOWS_BY_IMAGE,
    )


def main(target_w=DEFAULT_TARGET_W, target_h=DEFAULT_TARGET_H):
    """Generate polygon plots for all configured TIFF images for a target window size."""
    target_w = int(target_w)
    target_h = int(target_h)
    dir_out = _default_out_dir(target_w, target_h)
    os.makedirs(dir_out, exist_ok=True)
    manual_windows = load_manual_windows(_default_windows_json_path(target_w, target_h))

    id_to_tiff = build_id_to_tiff_path(Cfg.FNAMES_TIF)
    gdf_land = gpd.read_file(LAND_PATH)

    print(f'[INFO] Creating *POLYGONS_{target_w}x{target_h}.png files in: {dir_out}')
    print(f'[INFO] TIFF files found: {len(Cfg.FNAMES_TIF)}')

    generated = 0
    for id_tiff, tiff_path in sorted(id_to_tiff.items()):
        gdf_img = Cfg.VECTORS[Cfg.VECTORS['Id'] == id_tiff].copy().reset_index(drop=True)
        out_png = os.path.join(dir_out, f'IMG_{id_tiff:02d}_POLYGONS_{target_w}x{target_h}.png')
        plot_tiff_with_polygons(
            tiff_path=tiff_path,
            gdf_img=gdf_img,
            out_png=out_png,
            gdf_land=gdf_land,
            target_w=target_w,
            target_h=target_h,
            manual_windows_by_image=manual_windows,
        )
        generated += 1

    print(f'[INFO] Done. Generated {generated} files.')


if __name__ == '__main__':
    main()
