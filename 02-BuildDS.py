from os.path import expanduser
import os
import csv
import glob
import importlib
import geopandas as gpd
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

# import pandas as pd
# from rasterio.plot import show|
# from rasterio import plot as rasterplot

# A cross-platform way to get the home directory
BITS = 16  # 8 or 16
HOME = expanduser("~")
PLOT = False
DIR_OUT = "dataout"
DIR_IMG = os.path.join(DIR_OUT, "img")
DIR_IN = os.path.join(HOME, "ProjData", "Oil_Spill", "Cantarell_Beisl")
DIR_TIF = os.path.join(DIR_IN, "Calibrada" if BITS == 16 else f"{DIR_IN}/8bits/")
FNAME_CSV = os.path.join(DIR_OUT, "DS", "CSV", f"Oil_Stats_{BITS}bits.csv")
FNAME_VETORES = os.path.join(DIR_IN, "Vetores", "Oil_slick", "OilSlicks_Cantarell_GEOG_18052022_01.shp")  # nopep8

os.makedirs(DIR_IMG, exist_ok=True)
VETORES = gpd.read_file(FNAME_VETORES)

# TIF names
FNAMES_TIF = sorted(glob.glob(
    f"{DIR_TIF}/*_NR_Orb_Cal_TC.tif" if BITS == 16 else f"{DIR_TIF}*_8b.tif"))

# List of features (geometrics, statistics, texturals, etc) to compose the resulting CSV file
# AREA_KM_DS e PERIM_KM_DS are feed by shapefile metadata iot comparison to our calculus.
KEYS_HEAD = ["IMG_FNAME", "IDX_POLY", "ID_POLY", "SATELITE", "BEAM_MODE"]
KEYS_FEAT_GEOM = ["CENTR_KM_LAT", "CENTR_KM_LON", "UTM_ZONE", "AREA_KM2", "PERIM_KM", "COMPLEX_MEAS", "SPREAD", "SHP_FACT",
                  "HU_MOM1", "HU_MOM2", "HU_MOM3", "HU_MOM4", "HU_MOM5", "HU_MOM6", "HU_MOM7", "CIRCULARITY", "PERI_AREA_RATIO"]
KEYS_FEAT_STAT = ["FG_STD", "FG_VAR", "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF",
                  "BG_STD", "BG_VAR", "BG_MIN", "BG_MAX", "BG_MEAN", "BG_MEDIAN", "BG_VAR_COEF",
                  "FG_DARK_INTENS", "FG_BG_KS_STAT", "FG_BG_KS_RES", "FG_BG_MW_STAT", "FG_BG_MW_RES",
                  "FG_BG_RAT_ARI", "FG_BG_RAT_QUA"]
KEYS_TAIL = ["AREA_KM_DS", "PERIM_KM_DS", "CLASSE", "SUBCLASSE"]

# TODO: New stats
# "FG_BG_RAT_HAR", "FG_BG_RAT_GEO"]
# "THRES", "FG_BG_MAX_CONTRAST", "FG_BG_MEAN_CONTRAST_RATIO",
# "BORDER_GRAD_STD", "BORDER_GRAD_MEAN", "BORDER_GRAD_MAX"]

DICT_HEAD = dict(zip(KEYS_HEAD, [None] * len(KEYS_HEAD)))  # nopep8
DICT_FEAT_GEOM = dict(zip(KEYS_FEAT_GEOM, [None] * len(KEYS_FEAT_GEOM)))  # nopep8
DICT_FEAT_STAT = dict(zip(KEYS_FEAT_STAT, [None] * len(KEYS_FEAT_STAT)))  # nopep8
DICT_TAIL = dict(zip(KEYS_TAIL, [None] * len(KEYS_TAIL)))  # nopep8
DICT = {**DICT_HEAD, **DICT_FEAT_GEOM, **DICT_FEAT_STAT, **DICT_TAIL}  # nopep8  # Une os DICTs

with open(FNAME_CSV, 'w', encoding='utf-8') as f1:
    writer = csv.writer(f1, delimiter=";", lineterminator='\n')
    _ = writer.writerow(KEYS_HEAD + KEYS_FEAT_GEOM +
                        KEYS_FEAT_STAT + KEYS_TAIL)

    # Loop in TIF with progress bar
    poly_count = 1
    with tqdm(
        FNAMES_TIF,
        total=len(FNAMES_TIF),
        desc="TIFF",
        unit="tif",
        position=0,
        dynamic_ncols=True
    ) as tiff_pbar:
        for tiff_idx, tiff_fname in enumerate(tiff_pbar):
            tiff_bname = os.path.basename(tiff_fname)
            tiff_name = tiff_bname[:28].ljust(28)
            tiff_pbar.set_postfix_str(f"NAME={tiff_name}", refresh=False)
            # Extract tiff ID from tiff fname
            id_tiff = int(tiff_bname.split(" ")[0])

            # tiff = rioxarray.open_rasterio(fname_img, masked=True, chunks=True)
            # Abre o raster (o TIFF)
            # IMG_ID=21, IDX_POLY=66
            # vetores[vetores["ID_POLY"] == "SP00369GXS1"]
            tiff_file = rasterio.open(tiff_fname, masked=True, chunks=True)
            # show(tiff_file)
            # tiff_file = rasterio.open("SP00369GXS1_66.tif", masked=True, chunks=True)
            # tiff_file_data = tiff_file.read(1)
            # tiff_file_extent = [tiff_file.bounds[0], tiff_file.bounds[2],
            #                 tiff_file.bounds[1], tiff_file.bounds[3]]

            # Inicia preenchimento do dict Head (que vai no início do CSV)
            dict_head_pol = DICT_HEAD
            dict_tail_pol = DICT_TAIL
            dict_head_pol["IMG_FNAME"] = tiff_bname

            # Captura todos os polígonos (vetores) referentes à imagem
            gdf_img_mpolys = VETORES[VETORES['Id'] == id_tiff]
            gdf_img_mpolys.reset_index(inplace=True)
            # gdf_img_mpolys.iloc[0]
            # gdf_img_mpolys.crs == tiff_file.crs

            # Cria uma mascara para todos os polígonos da imagem
            # masked_fg, transf_fg = Fun.get_masked_array_from_vector(
            #   tiff16, gdf_img_mpolys.geometry, filled=False, crop=False, invert=True)
            # masked_fg.shape, tiff16.shape
            # plt.imshow(masked_fg[0, :, :]); plt.show()

            # THIS VERSION DOES NOT EXPLODE MULTIPOLYGONS
            # Percorre a lista dos multi polígonos da imagem
            with tqdm(
                range(len(gdf_img_mpolys)),
                desc="POLY",
                unit="poly",
                position=1,
                leave=False,
                dynamic_ncols=True
            ) as poly_pbar:
                for idx_poly in poly_pbar:
                    gdf_poly = gdf_img_mpolys.iloc[[idx_poly]]
                    # Finaliza preenchimento do dict Head (que vai no início do CSV)
                    dict_head_pol["IDX_POLY"] = gdf_poly.index[0]
                    dict_head_pol["ID_POLY"] = gdf_poly.ID_POLY.iloc[0]
                    dict_head_pol["SATELITE"] = gdf_poly.SATELITE.iloc[0]
                    dict_head_pol["BEAM_MODE"] = gdf_poly.BEAM_MODE.iloc[0]
                    poly_name = str(dict_head_pol["ID_POLY"])[:28].ljust(28)
                    poly_pbar.set_postfix_str(f"NAME={poly_name}", refresh=False)

                    dict_tail_pol["AREA_KM_DS"] = gdf_poly.AREA_KM.iloc[0]
                    dict_tail_pol["PERIM_KM_DS"] = gdf_poly.PERIM_KM.iloc[0]
                    dict_tail_pol["CLASSE"] = gdf_poly.CLASSE.iloc[0]
                    dict_tail_pol["SUBCLASSE"] = gdf_poly.SUBCLASSE.iloc[0]

                    # Captura features geométricas ---------------------------------------------------
                    dict_feat_geom_pol = Geom.get_feat_geom(gdf_poly, DICT_FEAT_GEOM)

                    # Captura features estatísticas --------------------------------------------------
                    dict_feat_stat_pol = Stat.get_feat_stat(
                        gdf_img_mpolys, gdf_poly, DICT_FEAT_STAT, tiff_file, PLOT, DIR_IMG)

                    # with open(fname_csv, 'w') as f1:
                    #    writer = csv.writer(f1, delimiter=";", lineterminator='\n')
                    row = list(dict_head_pol.values()) + list(dict_feat_geom_pol.values()) + \
                        list(dict_feat_stat_pol.values()) + \
                        list(dict_tail_pol.values())

                    _ = writer.writerow(row)
                    poly_count += 1

                    # Plota os polígonos
                    # gdf_pol_deg.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
                    # gdf_pol_deg.plot()
                    # plt.show()
                    # plt.savefig(f"{dir_img}{os.sep}{bname.replace(".tif", "")}_Vet{
                    #            str(idx_vet).rjust(3, '0')}_Pol{str(idx_pol).rjust(3, '0')}.png")
                    # plt.close()

        # FIM DO: for idx_poly in range(len(gdf_img_mpolys))
    # FIM DO: for tiff_idx, tiff_fname in enumerate(FNAMES_TIF):

print(f"Completed processing: {len(FNAMES_TIF)} TIFs, {poly_count - 1} polygons.")
# FIM DO: with open(fname_csv, 'w') as f1:

if PLOT:
    VETORES_TO_SAVE = VETORES[['Id', 'ID_POLY',
                               'SATELITE', 'CLASSE', 'SUBCLASSE', 'geometry']]
    # Save VETORES as Shapefile
    fname_shp = f"{Cfg.DIR_SHP}{os.sep}All_Vectors_Oil_Spill_{BITS}bits.shp"
    if os.path.exists(fname_shp):
        os.remove(fname_shp)
    VETORES_TO_SAVE.to_file(fname_shp, driver='ESRI Shapefile')


# f, ax = plt.subplots()
# rasterplot.show(tiff,  # use tiff.read(1) with your data
#     extent=tiff_extent,
#     ax=ax,
# )
# # plot shapefiles
# row.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
# #plt.savefig('test.jpg')
# plt.show()
