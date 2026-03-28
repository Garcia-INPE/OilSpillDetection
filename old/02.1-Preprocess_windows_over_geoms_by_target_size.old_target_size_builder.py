#!/home/jrmgarcia/miniconda3/envs/OIL_SPILL/bin/python

import os
import csv
import importlib
import rasterio
from tqdm import tqdm

os.chdir("/home/jrmgarcia/ProjDocs/OilSpill/src")

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

TARGET_TILE_WIDTH = 800
TARGET_TILE_HEIGHT = 600
EXPORT_IMAGES = True
CLEAN_OUTPUT_DIRS = True

DIR_OUT = os.path.join(
    "dataout",
    "02-BuildDS_target_size-DS_TARGET_SIZE",
    f"{TARGET_TILE_WIDTH}x{TARGET_TILE_HEIGHT}",
)
OUTPUT_DIRS = Fun.build_output_dirs(DIR_OUT, Cfg.BITS)

if CLEAN_OUTPUT_DIRS:
    dirs_to_clean = [
        OUTPUT_DIRS["DIR_OUT_IMG"],
        OUTPUT_DIRS["DIR_OUT_LABELS_1D"],
        OUTPUT_DIRS["DIR_OUT_LABELS_RGB"],
        OUTPUT_DIRS["DIR_OUT_TIF"],
        OUTPUT_DIRS["DIR_OUT_JSON"],
        OUTPUT_DIRS["DIR_OUT_KML"],
        OUTPUT_DIRS["DIR_OUT_SHP"],
    ]
    for directory in dirs_to_clean:
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

FNAME_OUT_CSV = os.path.join(
    OUTPUT_DIRS["DIR_OUT_CSV"],
    f"Oil_Stats_target_{Cfg.BITS}bits_{TARGET_TILE_WIDTH}x{TARGET_TILE_HEIGHT}.csv",
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
KEYS_FEAT_GEOM = ["CENTR_KM_LAT", "CENTR_KM_LON", "UTM_ZONE", "AREA_KM2", "PERIM_KM", "COMPLEX_MEAS", "SPREAD", "SHP_FACT",
                  "HU_MOM1", "HU_MOM2", "HU_MOM3", "HU_MOM4", "HU_MOM5", "HU_MOM6", "HU_MOM7", "CIRCULARITY", "PERI_AREA_RATIO"]
KEYS_FEAT_STAT = ["FG_STD", "FG_VAR", "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF",
                  "BG_STD", "BG_VAR", "BG_MIN", "BG_MAX", "BG_MEAN", "BG_MEDIAN", "BG_VAR_COEF",
                  "FG_DARK_INTENS", "FG_BG_KS_STAT", "FG_BG_KS_RES", "FG_BG_MW_STAT", "FG_BG_MW_RES",
                  "FG_BG_RAT_ARI", "FG_BG_RAT_QUA"]
KEYS_TAIL = ["AREA_KM_DS", "PERIM_KM_DS", "CLASSE"]

DICT_HEAD = dict(zip(KEYS_HEAD, [None] * len(KEYS_HEAD)))
DICT_LAYOUT = dict(zip(KEYS_LAYOUT, [None] * len(KEYS_LAYOUT)))
DICT_FEAT_GEOM = dict(zip(KEYS_FEAT_GEOM, [None] * len(KEYS_FEAT_GEOM)))
DICT_FEAT_STAT = dict(zip(KEYS_FEAT_STAT, [None] * len(KEYS_FEAT_STAT)))
DICT_TAIL = dict(zip(KEYS_TAIL, [None] * len(KEYS_TAIL)))

with open(FNAME_OUT_CSV, "w", encoding="utf-8") as f1:
    writer = csv.writer(f1, delimiter=";", lineterminator="\n")
    _ = writer.writerow(KEYS_HEAD + KEYS_LAYOUT + KEYS_FEAT_GEOM + KEYS_FEAT_STAT + KEYS_TAIL)

    print(f"[INFO] Running target-size dataset build for {Cfg.BITS}-bit images.")
    print(f"[INFO] Target tile size: {TARGET_TILE_WIDTH}x{TARGET_TILE_HEIGHT} pixels.")
    poly_count = 0
    seen_panels: set = set()

    with tqdm(
        Cfg.FNAMES_TIF,
        total=len(Cfg.FNAMES_TIF),
        desc=f"TIFF ({Cfg.BITS}-bit)",
        unit="tif",
        position=0,
        dynamic_ncols=True,
    ) as tiff_pbar:
        for tiff_fname in tiff_pbar:
            tiff_bname = os.path.basename(tiff_fname)
            tiff_name = tiff_bname[:28].ljust(28)
            tiff_pbar.set_postfix_str(f"NAME={tiff_name}", refresh=False)
            id_tiff = int(tiff_bname.split(" ")[0])

            tiff_file = rasterio.open(tiff_fname, masked=True)

            try:
                gdf_img_mpolys = Cfg.VECTORS[Cfg.VECTORS["Id"] == id_tiff].copy()
                gdf_img_mpolys.reset_index(inplace=True)

                # Build all panels for this TIFF in one call (groups nearby polygons)
                poly_to_panel = Fun.gen_images_for_DS_target_size(
                    tiff_file,
                    gdf_img_mpolys,
                    TARGET_TILE_WIDTH,
                    TARGET_TILE_HEIGHT,
                    OUTPUT_DIRS,
                )

                with tqdm(
                    range(len(gdf_img_mpolys)),
                    desc=f"POLY ({Cfg.BITS}-bit)",
                    unit="poly",
                    position=1,
                    leave=False,
                    dynamic_ncols=True,
                ) as poly_pbar:
                    for idx_poly in poly_pbar:
                        gdf_poly = gdf_img_mpolys.iloc[[idx_poly]].copy()

                        dict_head_pol = DICT_HEAD.copy()
                        dict_layout_pol = DICT_LAYOUT.copy()
                        dict_tail_pol = DICT_TAIL.copy()

                        dict_head_pol["IMG_FNAME"] = tiff_bname
                        dict_head_pol["IDX_POLY"] = int(gdf_poly.index[0])
                        dict_head_pol["ID_POLY"] = gdf_poly.ID_POLY.iloc[0]
                        dict_head_pol["SATELITE"] = gdf_poly.SATELITE.iloc[0]
                        dict_head_pol["BEAM_MODE"] = gdf_poly.BEAM_MODE.iloc[0]

                        dict_tail_pol["AREA_KM_DS"] = gdf_poly.AREA_KM.iloc[0]
                        dict_tail_pol["PERIM_KM_DS"] = gdf_poly.PERIM_KM.iloc[0]
                        dict_tail_pol["CLASSE"] = gdf_poly.CLASSE.iloc[0]

                        poly_name = str(dict_head_pol["ID_POLY"])[:28].ljust(28)
                        poly_pbar.set_postfix_str(f"NAME={poly_name}", refresh=False)

                        panel_info = poly_to_panel.get(idx_poly, {})
                        dict_head_pol["RESULT_BASENAME"] = panel_info.get("RESULT_BASENAME", "")
                        for key in KEYS_LAYOUT:
                            dict_layout_pol[key] = panel_info.get(key)

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
                        _ = writer.writerow(row)
                        seen_panels.add(panel_info.get("RESULT_BASENAME"))
                        poly_count += 1
            finally:
                tiff_file.close()

if EXPORT_IMAGES:
    Fun.save_gdf_as_shapefile(OUTPUT_DIRS["DIR_OUT_SHP"])

panel_count = len(seen_panels - {None})
print(
    f"Completed processing: {len(Cfg.FNAMES_TIF)} TIFs, {poly_count} polygons, "
    f"{panel_count} panels, target tiles {TARGET_TILE_WIDTH}x{TARGET_TILE_HEIGHT}."
)


#Now, for both 02-BuildDS* script add the continent layer over the raster and plot it on every raster crop and PNG file. For RGB label files use (0, 153, 0) and 1-D files 4.