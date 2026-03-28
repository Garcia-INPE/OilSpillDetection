#!/usr/bin/env python3
"""Build the dataset from manually validated fixed-size windows.

This script reads window positions from
dataout/02.1-DS_by_manual_windows/800x600_windows/2/Adjusted_windows.json (produced by
02.1.2-Adjust_estimate_windows.py) and uses them to generate the cropped
imagery, labels, vectors and CSV rows.
"""

import csv
import json
import os
import zipfile
import importlib

import numpy as np
import rasterio
from PIL import Image
from rasterio.features import rasterize
from rasterio.windows import Window
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
from tqdm import tqdm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
os.chdir(SCRIPT_DIR)

import FunGetFeat_Stat as Stat  # nopep8
import FunGetFeat_Geom as Geom  # nopep8
import Functions as Fun  # nopep8
import FunPlot as FPlot  # nopep8
import Config as Cfg  # nopep8

importlib.reload(Fun)
importlib.reload(Geom)
importlib.reload(Stat)
importlib.reload(FPlot)
importlib.reload(Cfg)

TARGET_W = 800
TARGET_H = 600
SIZE_WINDOWS_DIR = os.path.join(
    SCRIPT_DIR,
    "dataout",
    "02.1-DS_by_manual_windows",
    f"{TARGET_W}x{TARGET_H}_windows",
)
MANUAL_WINDOWS_JSON = os.path.join(
    SIZE_WINDOWS_DIR,
    "2",
    "Adjusted_windows.json",
)
_MANUAL_WINDOWS_JSON_FALLBACK = os.path.join(
    SIZE_WINDOWS_DIR,
    "1",
    "Created_windows.json",
)

_json_source = MANUAL_WINDOWS_JSON if os.path.exists(MANUAL_WINDOWS_JSON) else _MANUAL_WINDOWS_JSON_FALLBACK
if _json_source == _MANUAL_WINDOWS_JSON_FALLBACK:
    print(f"[INFO] 02.1.2 adjusted JSON not found; falling back to 02.1.1 preprocessed JSON.")
with open(_json_source, encoding="utf-8") as handle:
    manual_windows_payload = json.load(handle)

MANUAL_WINDOWS = {
    int(image_id): [
        {
            "json_window_id": int(window_id),
            "panel_index": int(window_id) + 1,
            "row_off": int(window_cfg["row_off"]),
            "col_off": int(window_cfg["col_off"]),
        }
        for window_id, window_cfg in sorted(
            image_cfg.get("windows", {}).items(),
            key=lambda item: int(item[0]),
        )
    ]
    for image_id, image_cfg in manual_windows_payload.get("images", {}).items()
}

EXPORT_IMAGES = True
CLEAN_OUTPUT_DIRS = True

DIR_OUT = os.path.join(
    "dataout",
    "02.1-DS_by_manual_windows",
    f"{TARGET_W}x{TARGET_H}_windows",
    "3",
)
OUTPUT_DIRS = Fun.build_output_dirs(DIR_OUT, Cfg.BITS)

if CLEAN_OUTPUT_DIRS:
    for directory in [
        OUTPUT_DIRS["DIR_OUT_IMG"],
        OUTPUT_DIRS["DIR_OUT_LABELS_1D"],
        OUTPUT_DIRS["DIR_OUT_LABELS_RGB"],
        OUTPUT_DIRS["DIR_OUT_TIF"],
        OUTPUT_DIRS["DIR_OUT_JSON"],
        OUTPUT_DIRS["DIR_OUT_KML"],
        OUTPUT_DIRS["DIR_OUT_SHP"],
        OUTPUT_DIRS["DIR_OUT_CSV"],
    ]:
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

FNAME_OUT_CSV = os.path.join(
    OUTPUT_DIRS["DIR_OUT_CSV"],
    f"Oil_Stats_manual_windows_{Cfg.BITS}bits_{TARGET_W}x{TARGET_H}.csv",
)

KEYS_HEAD = ["IMG_FNAME", "IDX_POLY", "ID_POLY", "SATELITE", "BEAM_MODE", "RESULT_BASENAME"]
KEYS_LAYOUT = [
    "COMPOSITE_BASENAME",
    "TARGET_TILE_WIDTH",
    "TARGET_TILE_HEIGHT",
    "CLIPPED_WIDTH",
    "CLIPPED_HEIGHT",
    "GRID_COLS",
    "GRID_ROWS",
    "COMPOSITE_WIDTH",
    "COMPOSITE_HEIGHT",
    "PAD_LEFT",
    "PAD_RIGHT",
    "PAD_TOP",
    "PAD_BOTTOM",
    "IS_COMPOSITE",
    "PANEL_INDEX",
    "PANEL_ROW",
    "PANEL_COL",
    "PANEL_COUNT",
    "POLYS_IN_PANEL",
    "POLYS_IN_GROUP",
]
KEYS_FEAT_GEOM = [
    "CENTR_KM_LAT", "CENTR_KM_LON", "UTM_ZONE", "AREA_KM2", "PERIM_KM",
    "COMPLEX_MEAS", "SPREAD", "SHP_FACT",
    "HU_MOM1", "HU_MOM2", "HU_MOM3", "HU_MOM4", "HU_MOM5", "HU_MOM6", "HU_MOM7",
    "CIRCULARITY", "PERI_AREA_RATIO",
]
KEYS_FEAT_STAT = [
    "FG_STD", "FG_VAR", "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF",
    "BG_STD", "BG_VAR", "BG_MIN", "BG_MAX", "BG_MEAN", "BG_MEDIAN", "BG_VAR_COEF",
    "FG_DARK_INTENS", "FG_BG_KS_STAT", "FG_BG_KS_RES", "FG_BG_MW_STAT", "FG_BG_MW_RES",
    "FG_BG_RAT_ARI", "FG_BG_RAT_QUA",
]
KEYS_TAIL = ["AREA_KM_DS", "PERIM_KM_DS", "CLASSE"]

DICT_FEAT_GEOM = dict.fromkeys(KEYS_FEAT_GEOM)
DICT_FEAT_STAT = dict.fromkeys(KEYS_FEAT_STAT)

SHP_SIDECARS = [
    ".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj",
    ".sbn", ".sbx", ".shp.xml", ".aih", ".ain", ".atx",
    ".ixs", ".mxs", ".qix", ".fix",
]

id_to_tiff = {}
for path in Cfg.FNAMES_TIF:
    bname = os.path.basename(path)
    id_to_tiff[int(bname.split(" ")[0])] = path

print(f"[INFO] Running manual-windows dataset build for {Cfg.BITS}-bit images.")
print(f"[INFO] Target tile size: {TARGET_W}x{TARGET_H} pixels.")
print(f"[INFO] Images to process: {sorted(MANUAL_WINDOWS.keys())}")

poly_count = 0
seen_panels = set()

with open(FNAME_OUT_CSV, "w", encoding="utf-8") as handle:
    writer = csv.writer(handle, delimiter=";", lineterminator="\n")
    writer.writerow(KEYS_HEAD + KEYS_LAYOUT + KEYS_FEAT_GEOM + KEYS_FEAT_STAT + KEYS_TAIL)

    with tqdm(
        sorted(MANUAL_WINDOWS),
        total=len(MANUAL_WINDOWS),
        desc="TIFF",
        unit="tif",
        position=0,
        dynamic_ncols=True,
    ) as tiff_pbar:
        for image_id in tiff_pbar:
            if image_id not in id_to_tiff:
                print(f"\n[WARN] Image ID {image_id} not found in FNAMES_TIF; skipping.")
                continue

            tiff_path = id_to_tiff[image_id]
            tiff_bname = os.path.basename(tiff_path)
            tiff_pbar.set_postfix_str(f"IMG={tiff_bname[:22]}", refresh=False)
            windows = MANUAL_WINDOWS[image_id]
            windows_by_panel = {w["panel_index"]: w for w in windows}
            image_id_str = str(image_id).zfill(2)

            tiff_file = rasterio.open(tiff_path, masked=True)
            try:
                gdf_img_mpolys = Cfg.VECTORS[Cfg.VECTORS["Id"] == image_id].copy()
                gdf_img_mpolys.reset_index(inplace=True)

                gdf_local = gdf_img_mpolys.copy()
                if gdf_local.crs != tiff_file.crs:
                    gdf_local = gdf_local.to_crs(tiff_file.crs)

                nodata_value = tiff_file.nodata if tiff_file.nodata is not None else 0
                out_meta = tiff_file.meta.copy()
                out_meta.update({"driver": "GTiff", "height": TARGET_H, "width": TARGET_W})

                px_bboxes = []
                for idx in range(len(gdf_local)):
                    minx, miny, maxx, maxy = gdf_local.geometry.iloc[idx].bounds
                    row_ul, col_ul = tiff_file.index(minx, maxy)
                    row_lr, col_lr = tiff_file.index(maxx, miny)
                    r0 = max(0, min(row_ul, row_lr))
                    r1 = min(tiff_file.height - 1, max(row_ul, row_lr))
                    c0 = max(0, min(col_ul, col_lr))
                    c1 = min(tiff_file.width - 1, max(col_ul, col_lr))
                    px_bboxes.append((r0, c0, r1, c1))

                poly_best_window = {}
                win_effective_ilocs = {}

                for window in windows:
                    win_idx = int(window["panel_index"])
                    row_off = int(window["row_off"])
                    col_off = int(window["col_off"])
                    read_height = min(TARGET_H, tiff_file.height - row_off)
                    read_width = min(TARGET_W, tiff_file.width - col_off)
                    if read_height <= 0 or read_width <= 0:
                        continue

                    tile_r0 = row_off
                    tile_c0 = col_off
                    tile_r1 = tile_r0 + read_height - 1
                    tile_c1 = tile_c0 + read_width - 1

                    candidate_ilocs = [
                        idx for idx, (r0, c0, r1, c1) in enumerate(px_bboxes)
                        if not (r1 < tile_r0 or r0 > tile_r1 or c1 < tile_c0 or c0 > tile_c1)
                    ]
                    if not candidate_ilocs:
                        continue

                    panel_basename = f"IMG_{image_id_str}_WIN_{win_idx:03d}"
                    read_window = Window(col_off, row_off, read_width, read_height)
                    tile_window = Window(col_off, row_off, TARGET_W, TARGET_H)
                    tile_transform = tiff_file.window_transform(tile_window)
                    tile_bounds = tiff_file.window_bounds(tile_window)

                    mask1_tile = np.zeros((TARGET_H, TARGET_W), dtype=np.uint8)
                    effective_ilocs = []
                    iloc_overlaps = {}

                    for iloc_i in candidate_ilocs:
                        class_id = 2 if gdf_img_mpolys.CLASSE.iloc[iloc_i] == "SEEPAGE SLICK" else 1
                        poly_mask = rasterize(
                            [(gdf_local.geometry.iloc[iloc_i], class_id)],
                            out_shape=(TARGET_H, TARGET_W),
                            transform=tile_transform,
                            fill=0,
                            dtype=np.uint8,
                        )
                        overlap = int(np.count_nonzero(poly_mask))
                        if overlap == 0:
                            continue
                        effective_ilocs.append(iloc_i)
                        iloc_overlaps[iloc_i] = overlap
                        mask1_tile = np.maximum(mask1_tile, poly_mask)

                    if not effective_ilocs:
                        continue

                    win_effective_ilocs[win_idx] = effective_ilocs

                    if EXPORT_IMAGES:
                        src_data = tiff_file.read(
                            window=read_window,
                            boundless=False,
                        )
                        valid_pixels = np.zeros((TARGET_H, TARGET_W), dtype=bool)
                        valid_pixels[:read_height, :read_width] = True

                        tile_data = np.full(
                            (src_data.shape[0], TARGET_H, TARGET_W),
                            nodata_value,
                            dtype=src_data.dtype,
                        )
                        tile_data[:, :read_height, :read_width] = src_data

                        rgb_src = (
                            tile_data[:3]
                            if tile_data.shape[0] >= 3
                            else np.repeat(tile_data[:1], 3, axis=0)
                        )
                        rgb_tile = np.zeros((3, TARGET_H, TARGET_W), dtype=np.uint8)
                        for ch_idx in range(3):
                            band = rgb_src[ch_idx].astype(np.float32)
                            vmask = valid_pixels.copy()
                            if np.isfinite(float(nodata_value)):
                                vmask &= band != float(nodata_value)
                            if np.any(vmask):
                                bmin = np.nanmin(band[vmask])
                                bmax = np.nanmax(band[vmask])
                                if np.isfinite(bmin) and np.isfinite(bmax) and bmax > bmin:
                                    rgb_tile[ch_idx] = (
                                        (band - bmin) / (bmax - bmin) * 255
                                    ).astype(np.uint8)

                        mask3_tile = np.zeros((3, TARGET_H, TARGET_W), dtype=np.uint8)
                        mask3_tile[0] = np.where(mask1_tile == 2, 255, 0)
                        mask3_tile[1] = np.where(mask1_tile == 1, 255, 0)
                        mask3_tile[2] = np.where(mask1_tile == 1, 255, 0)

                        Image.fromarray(
                            np.transpose(rgb_tile, (1, 2, 0)),
                            mode="RGB",
                        ).save(os.path.join(OUTPUT_DIRS["DIR_OUT_IMG"], panel_basename + ".png"))
                        Image.fromarray(
                            np.transpose(mask3_tile, (1, 2, 0)),
                            mode="RGB",
                        ).save(os.path.join(OUTPUT_DIRS["DIR_OUT_LABELS_RGB"], panel_basename + "_RGB.png"))
                        Image.fromarray(mask1_tile, mode="L").save(
                            os.path.join(OUTPUT_DIRS["DIR_OUT_LABELS_1D"], panel_basename + "_1D.png")
                        )

                        with rasterio.open(
                            os.path.join(OUTPUT_DIRS["DIR_OUT_TIF"], panel_basename + ".tiff"),
                            "w",
                            **{**out_meta, "transform": tile_transform},
                        ) as dst:
                            dst.write(tile_data)

                        gdf_tile = gdf_local.iloc[sorted(effective_ilocs)].copy()
                        tile_geom = box(*tile_bounds)
                        gdf_tile.geometry = gdf_tile.geometry.intersection(tile_geom)
                        gdf_tile = gdf_tile[~gdf_tile.geometry.is_empty].copy()
                        
                        # Filter out invalid geometry types (GeometryCollection, etc.)
                        # Keep only Polygon and MultiPolygon types for shapefile compatibility
                        def extract_polygon(geom):
                            """Extract polygon geometry from any geometry type."""
                            if isinstance(geom, (Polygon, MultiPolygon)):
                                return geom
                            elif isinstance(geom, GeometryCollection):
                                # Extract polygon parts from collection
                                polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
                                if not polys:
                                    return None
                                if len(polys) == 1 and isinstance(polys[0], Polygon):
                                    return polys[0]
                                return MultiPolygon([p for p in polys if isinstance(p, Polygon)] + 
                                                   [g for p in polys if isinstance(p, MultiPolygon) for g in p.geoms])
                            return None
                        
                        gdf_tile.geometry = gdf_tile.geometry.apply(extract_polygon)
                        gdf_tile = gdf_tile[gdf_tile.geometry.notna() & ~gdf_tile.geometry.is_empty].copy()
                        
                        if len(gdf_tile) == 0:
                            continue
                        
                        for column in list(gdf_tile.columns):
                            if column == "geometry":
                                continue
                            if "datetime" in str(gdf_tile[column].dtype).lower():
                                gdf_tile[column] = gdf_tile[column].dt.strftime("%Y-%m-%d")
                        if "DATE" in gdf_tile.columns:
                            gdf_tile["DATE"] = gdf_tile["DATE"].astype(str)

                        kml_path = os.path.join(OUTPUT_DIRS["DIR_OUT_KML"], panel_basename + ".kml")
                        if os.path.exists(kml_path):
                            os.remove(kml_path)
                        gdf_tile.to_file(kml_path, driver="KML")

                        geojson_path = os.path.join(OUTPUT_DIRS["DIR_OUT_JSON"], panel_basename + ".geojson")
                        if os.path.exists(geojson_path):
                            os.remove(geojson_path)
                        gdf_tile.to_file(geojson_path, driver="GeoJSON")

                        shp_base = os.path.join(OUTPUT_DIRS["DIR_OUT_SHP"], panel_basename)
                        for ext in SHP_SIDECARS:
                            if os.path.exists(shp_base + ext):
                                os.remove(shp_base + ext)
                        gdf_tile.to_file(shp_base + ".shp", driver="ESRI Shapefile")
                        with zipfile.ZipFile(shp_base + ".zip", "w") as zipf:
                            for ext in SHP_SIDECARS:
                                file_path = shp_base + ext
                                if os.path.exists(file_path):
                                    zipf.write(file_path, arcname=os.path.basename(file_path))
                        for ext in SHP_SIDECARS:
                            file_path = shp_base + ext
                            if os.path.exists(file_path):
                                os.remove(file_path)

                    for iloc_i in effective_ilocs:
                        overlap = iloc_overlaps[iloc_i]
                        if iloc_i not in poly_best_window or overlap > poly_best_window[iloc_i][2]:
                            poly_best_window[iloc_i] = (win_idx, panel_basename, overlap)

                    seen_panels.add(panel_basename)

                win_poly_counts = {
                    win_idx: len(ilocs)
                    for win_idx, ilocs in win_effective_ilocs.items()
                }

                with tqdm(
                    range(len(gdf_img_mpolys)),
                    desc=f"POLY IMG{image_id_str}",
                    unit="poly",
                    position=1,
                    leave=False,
                    dynamic_ncols=True,
                ) as poly_pbar:
                    for idx_poly in poly_pbar:
                        if idx_poly not in poly_best_window:
                            continue

                        gdf_poly = gdf_img_mpolys.iloc[[idx_poly]].copy()
                        win_idx, panel_basename, _ = poly_best_window[idx_poly]

                        poly_name = str(gdf_poly.ID_POLY.iloc[0])[:28].ljust(28)
                        poly_pbar.set_postfix_str(f"NAME={poly_name}", refresh=False)

                        dict_head_pol = {
                            "IMG_FNAME": tiff_bname,
                            "IDX_POLY": int(gdf_poly.index[0]),
                            "ID_POLY": gdf_poly.ID_POLY.iloc[0],
                            "SATELITE": gdf_poly.SATELITE.iloc[0],
                            "BEAM_MODE": gdf_poly.BEAM_MODE.iloc[0],
                            "RESULT_BASENAME": panel_basename,
                        }
                        selected_window = windows_by_panel[win_idx]
                        read_width = min(TARGET_W, tiff_file.width - int(selected_window["col_off"]))
                        read_height = min(TARGET_H, tiff_file.height - int(selected_window["row_off"]))
                        dict_layout_pol = {
                            "COMPOSITE_BASENAME": panel_basename,
                            "TARGET_TILE_WIDTH": TARGET_W,
                            "TARGET_TILE_HEIGHT": TARGET_H,
                            "CLIPPED_WIDTH": read_width,
                            "CLIPPED_HEIGHT": read_height,
                            "GRID_COLS": 1,
                            "GRID_ROWS": 1,
                            "COMPOSITE_WIDTH": TARGET_W,
                            "COMPOSITE_HEIGHT": TARGET_H,
                            "PAD_LEFT": 0,
                            "PAD_RIGHT": TARGET_W - read_width,
                            "PAD_TOP": 0,
                            "PAD_BOTTOM": TARGET_H - read_height,
                            "IS_COMPOSITE": 0,
                            "PANEL_INDEX": win_idx,
                            "PANEL_ROW": 1,
                            "PANEL_COL": 1,
                            "PANEL_COUNT": len(windows),
                            "POLYS_IN_PANEL": win_poly_counts.get(win_idx, 0),
                            "POLYS_IN_GROUP": win_poly_counts.get(win_idx, 0),
                        }
                        dict_tail_pol = {
                            "AREA_KM_DS": gdf_poly.AREA_KM.iloc[0],
                            "PERIM_KM_DS": gdf_poly.PERIM_KM.iloc[0],
                            "CLASSE": gdf_poly.CLASSE.iloc[0],
                        }

                        dict_feat_geom_pol = Geom.get_feat_geom(gdf_poly, DICT_FEAT_GEOM.copy())
                        dict_feat_stat_pol = Stat.get_feat_stat(
                            gdf_img_mpolys,
                            gdf_poly,
                            DICT_FEAT_STAT.copy(),
                            tiff_file,
                            EXPORT_IMAGES,
                            OUTPUT_DIRS["DIR_OUT_IMG"],
                        )

                        row = (
                            list(dict_head_pol.values())
                            + list(dict_layout_pol.values())
                            + list(dict_feat_geom_pol.values())
                            + list(dict_feat_stat_pol.values())
                            + list(dict_tail_pol.values())
                        )
                        writer.writerow(row)
                        poly_count += 1

            finally:
                tiff_file.close()

if EXPORT_IMAGES:
    Fun.save_gdf_as_shapefile(OUTPUT_DIRS["DIR_OUT_SHP"])

panel_count = len(seen_panels)
print(
    f"Completed processing: {len(MANUAL_WINDOWS)} images, "
    f"{poly_count} polygons, {panel_count} panels, "
    f"windows {TARGET_W}x{TARGET_H}."
)
