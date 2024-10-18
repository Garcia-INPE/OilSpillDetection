from matplotlib import pyplot as plt
from os.path import expanduser
import numpy as np
import rasterio
import geopandas as gpd
import cv2
import pandas as pd
import math
import glob
import csv
import os
import re
import importlib

import FunStat as FStat
importlib.reload(FStat)

# A cross-platform way to get the home directory
home = expanduser("~")

# from rasterio import plot as rasterplot

pd.set_option("display.max_columns", 1000)
CRS = 3857  # TODO: Check!

dir_img = "./img"
os.makedirs(dir_img, exist_ok=True)
dir_data = f"{home}/ProjData/Oil-Datasets/Cantarell"
dir_tif8 = f"{dir_data}/8bits"          # To print
dir_tif16 = f"{dir_data}/Calibrada"     # To extract features
fname_vetores = f"{
    dir_data}/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp"
vetores = gpd.read_file(fname_vetores)
# Nomes das imagens TIF do diretório

# Captura todas as imagens dos diretórios
fnames_img8 = sorted(glob.glob(f"{dir_tif8}/*_8b.tif"))
fnames_img16 = sorted(glob.glob(f"{dir_tif16}/*_NR_Orb_Cal_TC.tif"))

# Filtra somente Sentinel-1
# Lista devem ter mesmo tamanho, relação 1:1 (8bits:16bits)
fnames_img8 = [f for f in fnames_img8 if re.search(
    "[0-9]{2} S1A_IW_GRDH_1SDV_", os.path.basename(f))]
fnames_img16 = [f for f in fnames_img16 if re.search(
    "[0-9]{2} S1A_IW_GRDH_1SDV_", os.path.basename(f))]
assert len(fnames_img8) == len(fnames_img16)

# https://learnopencv.com/shape-matching-using-hu-moments-c-python/
# pol=pol_deg


# Geométricas (Melissa): area (a), perim (p), complexity_measure (c),  spreading (s), shape_factor, hu_moment, circularity, ratio
with open('stats.csv', 'w') as f1:
    writer = csv.writer(f1, delimiter=";", lineterminator='\n')
    _ = writer.writerow(['FNAME', 'VET_ID', 'POLY_ID', 'CENTR_KM_LAT', 'CENTR_KM_LON', 'AREA_KM2', 'PERIM_KM', 'COMPLEX_MEAS', 'SPREAD', 'SHP_FACT',
                         'HU_MOM1', 'HU_MOM2', 'HU_MOM3', 'HU_MOM4', 'HU_MOM5', 'HU_MOM6', 'HU_MOM7', 'CIRCUL', 'RATIO'])

    idx_img = 0
    fname_img = fnames_img16[idx_img]
    # Loop pelas imagens TIF encontradas no diretório
    for idx_img in range(len(fnames_img16)):
        fname_img = fnames_img8[idx_img]
        # Basename (nome do arquivo somente, sem o path)
        bname = os.path.basename(fname_img)
        # Pega o ID da imagem do nome, para poder pegar seus vetores
        id_img = int(bname.split(" ")[0])

        # Captura todas as geometrias referentes à imagem
        # Vetores registrados na imagem sendo analisada
        vets_img = vetores[vetores['Id'] == id_img]
        vets_img.reset_index(inplace=True)

        # tiff = rioxarray.open_rasterio(fname_img, masked=True, chunks=True)
        # Abre o raster (o TIFF)
        tiff = rasterio.open(fname_img, masked=True, chunks=True)
        # tiff.crs - TODO: Check!
        tiff_extent = [tiff.bounds[0], tiff.bounds[2],
                       tiff.bounds[1], tiff.bounds[3]]

        # Plota uma imagem com todos os polígono da imagem e uma imagem para cada polígono da imagem
        # vets_img.plot();
        idx_vet = 0
        for idx_vet in range(len(vets_img)):
            # Captura polígono (pode ser multipolígonomesmo sendo polígono único)
            multipol_df = vets_img.iloc[[idx_vet]]
            # Transforma cada multipolígono lista de polígonos
            pol_df = multipol_df.explode(index_parts=True)
            idx_pol = 0
            pol = pol_df.iloc[idx_pol]
            for idx_pol in range(len(pol_df)):
                # row = [bname, str(idx_vet).rjust(3, '0'), str(idx_pol).rjust(3, '0')]
                row = [bname, idx_vet, idx_pol]
                print(row)
                # CRS=z   # 3857 (meters) | 4336 (degress)
                # polygon's geometry georrefeenced in degrees
                pol_deg = pol_df.iloc[[idx_pol]]
                # polygon's geometry georrefeenced in meters
                pol_m = pol_df.iloc[[idx_pol]].to_crs(CRS)
                # 'AREA_KM','PERIM_KM','COMPLEX_MEAS','SPREAD','SHP_FACT','HU_MOM','CIRCUL','RATIO'])
                # meter/1000 = in km
                centr_m_lat = pol_m.centroid.iloc[0].y/1000
                # meter/1000 = in km
                centr_m_lon = pol_m.centroid.iloc[0].x/1000
                # meter/1000 = in km2
                area_km = pol_m.area.iloc[0]/1000
                # m/1000 = in km
                perim_km = pol_m.length.iloc[0]/1000
                complexity = (perim_km ** 2) / area_km
                minx, miny, maxx, maxy = pol_m.total_bounds             # bounding box
                len_km = (maxx - minx)/1000
                wid_km = (maxy - miny)/1000
                spread_km = (wid_km / len_km)
                shp_fact_km = perim_km / \
                    (4 * np.sqrt(area_km))         # TODO: verificar
                hu_mom = FStat.get_huMomentun(pol_m)
                circul_km = (perim_km ** 2) / (4 * np.pi * area_km)
                perim_area_ratio = perim_km / area_km
                _ = writer.writerow(row + [area_km, centr_m_lat, centr_m_lon, perim_km,
                                    complexity, spread_km, shp_fact_km] + hu_mom + [circul_km, perim_area_ratio])

            # pol.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
            # pol.plot();
            # plt.savefig(f"{dir_img}{os.sep}{bname.replace(".tif", "")}_Vet{str(idx_vet).rjust(3, '0')}_Pol{str(idx_pol).rjust(3, '0')}.png");
            # plt.close();
            # plt.show()


# f, ax = plt.subplots()
# rasterplot.show(tiff,  # use tiff.read(1) with your data
#     extent=tiff_extent,
#     ax=ax,
# )
# # plot shapefiles
# row.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
# #plt.savefig('test.jpg')
# plt.show()
