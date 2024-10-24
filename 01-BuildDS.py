from rasterio.plot import show
from rasterio.windows import Window
from rasterio.mask import mask as rioMask
from os.path import expanduser
from matplotlib import pyplot as plt
from rasterio import plot as rasterplot
from shapely.geometry import MultiPolygon, Polygon
import rasterio.mask
import rasterio
import geopandas as gpd
import pandas as pd
import glob
import csv
import os
import re

import importlib
import FunDiv as FunDiv
import FunFeatShape as FunShape
import FunFeatStat as FunStat
importlib.reload(FunDiv)
importlib.reload(FunShape)
importlib.reload(FunStat)

# A cross-platform way to get the home directory
home = expanduser("~")

pd.set_option("display.max_columns", 1000)

dir_img = "./img"
os.makedirs(dir_img, exist_ok=True)
dir_ds = f"{home}/ProjData/Oil-Datasets/Cantarell"
dir_raw_data = dir_ds                 # Root dir where .SAFE dir is
dir_tif8 = f"{dir_ds}/8bits"          # To print
dir_tif16 = f"{dir_ds}/Calibrada"     # To extract features
fname_vetores = f"{
    dir_ds}/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp"
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

# Open output CSV for writing (DS-OIL)
with open('stats.csv', 'w') as f1:
    writer = csv.writer(f1, delimiter=";", lineterminator='\n')

    idx_img = 0
    fname_img = fnames_img16[idx_img]
    # Loop pelas imagens TIF encontradas no diretório
    for idx_img in range(len(fnames_img16)):
        fname_img = fnames_img16[idx_img]
        # Basename (nome do arquivo somente, sem o path)
        bname = os.path.basename(fname_img)
        # Pega o ID da imagem do nome, para poder pegar seus vetores
        id_img = int(bname.split(" ")[0])
        flds = FunDiv.get_S1A_fname_fields(dir_raw_data, bname)

        # 1st prefix for each row of the CSV (related to the image)
        dict_tiff = {'ID_IMG': id_img,
                     'IMG_NAME': bname,
                     'YEAR': flds['date_on'][:4],
                     'MONTH': flds['date_on'][4:6],
                     'DAY': flds['date_on'][6:]}

        # Abre o raster (o TIFF)
        # tiff = rioxarray.open_rasterio(fname_img, masked=True, chunks=True)
        tiff16 = rasterio.open(fname_img, masked=True, chunks=True)

        # Captura todas as geometrias (polígonos) referentes à imagem
        gdf_img_mpolys = vetores[vetores['Id'] == id_img]
        gdf_img_mpolys.reset_index(inplace=True)

        # Converte todos os mutipolígonos da imagem em polígonos individuais
        # Os polígonos permanecem polígonos
        # index_parts=True cria um índice composto (entrada original + partes explodidas)
        gdf_img_polys = gdf_img_mpolys.explode(index_parts=True)

        # Percorre a lista dos polígonos individuais da imagem
        idx_pol = 0
        for idx_pol in range(len(gdf_img_polys)):
            gdf_pol = gdf_img_polys.iloc[[idx_pol]]

            # If 1st pol in the multipol
            if gdf_pol.index[0][1] == 0:
                # 2nd prefix for each row of the CSV (wrt to the main multipol and child pol)
                dict_head_vect = {'IDX_VECT': int(gdf_pol.index[0][0]),  # Multipol idx
                                  # Multipolygon id (custom)
                                  'ID_VECT': gdf_pol.ID_POLY.iloc[0]}

                # Suffix for each row of the CSV
                dict_tail_vect = {"AREA_KM_DS": float(gdf_pol.AREA_KM.iloc[0]),
                                  "PERIM_KM_DS": float(gdf_pol.PERIM_KM.iloc[0]),
                                  "CLASSE": gdf_pol.CLASSE.iloc[0],
                                  "SUBCLASSE": gdf_pol.SUBCLASSE.iloc[0]}

            # Pol idx in multipol
            dict_head_pol = {'IDX_POLYG': int(gdf_pol.index[0][1])}

            print(dict_tiff["IMG_NAME"], dict_head_vect['IDX_VECT'],
                  dict_head_pol['IDX_POLYG'])

            dict_shape_feat = FunShape.get_shape_features(gdf_pol.geometry)
            importlib.reload(FunStat)
            dict_stat_feat = FunStat.get_stat_features(
                gdf_img_polys, gdf_pol.geometry, tiff16)

            # Contatenates dicts
            line = dict_tiff | dict_head_vect | dict_head_pol | dict_shape_feat | dict_tail_vect

            # Writes the CSV header if is the 1st polygon
            if idx_img == 0 and gdf_pol.index[0] == (0, 0):
                _ = writer.writerow(line.keys())

            # Escreve a linha
            _ = writer.writerow(line.values())

    #     # Plotting
    #     pol_deg.geometry.plot(facecolor='w', edgecolor='red')
    #     # pol_deg.plot()
    #     # plt.savefig(f"{dir_img}{os.sep}{bname.replace(".tif", "")}_Vet{str(idx_vet).rjust(3, '0')}_Pol{str(idx_pol).rjust(3, '0')}.png");
    #     # plt.close();
    #     plt.show()

    #     print(pol_deg.bounds)
    #     f, ax = plt.subplots()
    #     # rasterplot.show(tiff,  # use tiff.read(1) with your data
    #     #                 # minx, maxx, miny, maxy
    #     #                 extent=[pol_deg.bounds.minx, pol_deg.bounds.maxx,
    #     #                         pol_deg.bounds.miny, pol_deg.bounds.maxy],
    #     #                 ax=ax,
    #     #                 )

    #     data, _ = rasterio.mask.mask(tiff16, shapes=seg, crop=True)
    #     rasterplot.show(data, ax=ax)
    #     # rasterplot.show(pol_deg, ax=ax)
    #     # plot shapefiles
    #     # pol_deg.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
    #     # plt.savefig('test.jpg')
    #     plt.show()

    #     with rasterio.open(fname_img) as src:
    # data, _ = rasterio.mask.mask(src, shapes=bbox, crop=True)

    # fig = plt.figure(figsize=[12, 8])
    # # Plot the raster data using matplotlib
    # ax = fig.add_axes([0, 0, 1, 1])
    # raster_image = ax.imshow(
    #     data[0, :, :], cmap="terrain", vmax=5000, vmin=-4000)
    # fig.colorbar(raster_image, ax=ax, label="Elevation (in m) ",
    #              orientation='vertical', extend='both', shrink=0.5)
    # plt.show()

    # # ================================================================
    # # Open the raster data using rasterio
    # data, _ = rasterio.mask.mask(
    #     tiff16, shapes=pol_deg.geometry, crop=True)

    # fig = plt.figure(figsize=[12, 8])
    # # Plot the raster data using matplotlib
    # ax = fig.add_axes([0, 0, 1, 1])
    # raster_image = ax.imshow(
    #     data[0, :, :], cmap="terrain", vmax=5000, vmin=-3000)
    # fig.colorbar(raster_image, ax=ax, label="Elevation (in m) ",
    #              orientation='vertical', extend='both', shrink=0.5)
    # plt.show()

    # xmin, xmax, ymin, ymax = float(pol_deg.bounds.minx), float(
    #     pol_deg.bounds.maxx), float(pol_deg.bounds.miny), float(pol_deg.bounds.maxy)
    # bbox = MultiPolygon(
    #     [Polygon([[xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin]])])
    # tiff2 = rasterio.open(fname_img, masked=False, chunks=True)
    # tiff2.shape
    # out_img, out_transform = rioMask(tiff2, shapes=bbox, crop=False)
    # ax = rasterplot.show(out_img, cmap="gray", shapes=bbox)
    # # pol_deg.boundary.plot(ax=ax) # ax=ax)
    # plt.show()

    # # Check your coordinate ordering,
    # # I wasn't sure which was X and which was Y
    # ulx, uly = 5773695.0, 601200.0
    # width, height = 700, 500

    # with rasterio.open('/path/to/someraster') as ds:
    #     # Note - index takes coordinates in X,Y order
    #     #        and returns row, col (Y,X order)
    # row, col = ds.index(ulx, uly)
    # window = Window(row, col, width, height)
    # data = ds.read(window)
