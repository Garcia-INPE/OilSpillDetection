#!/usr/bin/env python3
"""02.1.1-Estimate_windows_over_geoms_by_target_size.py

Estimate fixed-size windows over polygons and export preview PNGs.

This script does two things only:
1. Estimate non-overlapping 800x600 windows for each TIFF image.
2. Save one PNG preview per TIFF showing polygons and the estimated windows.

The estimated windows are written to
dataout/02.1-DS_by_manual_windows/800x600_windows/1 - Preprocessed/Created_windows.json and are consumed later by
02.1.3-Build_DS_from_manual_windows.py.
"""

import json
import os
import importlib
import importlib.util

import geopandas as gpd
import rasterio
from tqdm import tqdm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
os.chdir(SCRIPT_DIR)

import Config as Cfg  # nopep8

importlib.reload(Cfg)

TARGET_W = 800
TARGET_H = 600
SIZE_WINDOWS_DIR = os.path.join(
    "dataout",
    "02.1-DS_by_manual_windows",
    f"{TARGET_W}x{TARGET_H}_windows",
)
JSON_PATH = os.path.join(SIZE_WINDOWS_DIR, "1 - Preprocessed", "Created_windows.json")
DIR_OUT = os.path.join(SIZE_WINDOWS_DIR, "1 - Preprocessed")
CLEAN_OUTPUT_DIR = True

os.makedirs(DIR_OUT, exist_ok=True)


def _load_plot_module():
    """Load the plotting helpers as an importable module."""
    spec = importlib.util.spec_from_file_location(
        "plot_polygons",
        "Fun_plot_tiff_with_polygons.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLOT024 = _load_plot_module()


def build_id_to_tiff_path(tiff_paths):
    """Return a mapping from numeric image ID to TIFF path."""
    mapping = {}
    for path in tiff_paths:
        bname = os.path.basename(path)
        image_id = int(bname.split(" ")[0])
        mapping[image_id] = path
    return mapping


def save_windows_json(payload):
    """Persist the estimated windows JSON in stable image-id order."""
    payload["images"] = {
        image_id: payload["images"][image_id]
        for image_id in sorted(payload["images"], key=lambda value: int(value))
    }
    with open(JSON_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def clean_output_dir():
    """Remove previously generated PNG previews from the output directory."""
    if not CLEAN_OUTPUT_DIR:
        return
    for file_name in os.listdir(DIR_OUT):
        file_path = os.path.join(DIR_OUT, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def estimate_windows():
    """Estimate windows for every TIFF image and write the JSON payload."""
    id_to_tiff = build_id_to_tiff_path(Cfg.FNAMES_TIF)
    payload = {"images": {}}
    windows_by_image = {}

    print(f"[INFO] Estimating windows for {len(id_to_tiff)} TIFF images.")
    print(f"[INFO] Window size: {TARGET_W}x{TARGET_H} pixels.")
    print(f"[INFO] JSON output: {JSON_PATH}")

    for image_id, tiff_path in tqdm(
        sorted(id_to_tiff.items()),
        total=len(id_to_tiff),
        desc="WINDOWS",
        unit="tif",
        dynamic_ncols=True,
    ):
        gdf_img = Cfg.VECTORS[Cfg.VECTORS["Id"] == image_id].copy().reset_index(drop=True)

        with rasterio.open(tiff_path) as src:
            gdf_plot = gdf_img.copy()
            if len(gdf_plot) > 0 and gdf_plot.crs != src.crs:
                gdf_plot = gdf_plot.to_crs(src.crs)

            windows, _, _ = PLOT024.select_non_overlapping_windows(
                src,
                gdf_plot,
                TARGET_W,
                TARGET_H,
            )

        windows_by_image[image_id] = windows
        payload["images"][str(image_id)] = {
            "n_polygons": int(len(gdf_img)),
            "n_windows": int(len(windows)),
            "windows": {
                str(window_idx): {
                    "row_off": int(window_cfg["row_off"]),
                    "col_off": int(window_cfg["col_off"]),
                    "indices": sorted(int(index) for index in window_cfg["covered"]),
                    "poly_ids": sorted(int(index) + 1 for index in window_cfg["covered"]),
                }
                for window_idx, window_cfg in enumerate(windows)
            },
        }

    save_windows_json(payload)
    return windows_by_image, id_to_tiff


def render_previews(windows_by_image, id_to_tiff):
    """Render one polygons preview PNG per TIFF using the estimated windows."""
    gdf_land = gpd.read_file(PLOT024.LAND_PATH)
    PLOT024.MANUAL_WINDOWS_BY_IMAGE = {
        image_id: [
            {
                "window_id": idx + 1,
                "row_off": int(window_cfg["row_off"]),
                "col_off": int(window_cfg["col_off"]),
                "covered": set(int(index) for index in window_cfg["covered"]),
            }
            for idx, window_cfg in enumerate(windows)
        ]
        for image_id, windows in windows_by_image.items()
    }

    print(f"[INFO] Generating one polygons preview PNG per TIFF in: {DIR_OUT}")
    for image_id, tiff_path in tqdm(
        sorted(id_to_tiff.items()),
        total=len(id_to_tiff),
        desc="PNG",
        unit="tif",
        dynamic_ncols=True,
    ):
        gdf_img = Cfg.VECTORS[Cfg.VECTORS["Id"] == image_id].copy().reset_index(drop=True)
        out_png = os.path.join(
            DIR_OUT,
            f"IMG_{image_id:02d}_POLYGONS_{TARGET_W}x{TARGET_H}.png",
        )
        PLOT024.plot_tiff_with_polygons(
            tiff_path=tiff_path,
            gdf_img=gdf_img,
            out_png=out_png,
            gdf_land=gdf_land,
            target_w=TARGET_W,
            target_h=TARGET_H,
            manual_windows_by_image=PLOT024.MANUAL_WINDOWS_BY_IMAGE,
        )


def main():
    clean_output_dir()
    windows_by_image, id_to_tiff = estimate_windows()
    render_previews(windows_by_image, id_to_tiff)
    print(f"[INFO] Done. Wrote windows JSON to: {JSON_PATH}")
    print(f"[INFO] Done. Wrote preview PNGs to: {DIR_OUT}")


if __name__ == "__main__":
    main()
