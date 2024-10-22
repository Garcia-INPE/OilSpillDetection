from rasterio.windows import Window
from rasterio.mask import mask as rioMask
import json
import rasterio.mask
from os.path import expanduser
import rasterio
import geopandas as gpd
import pandas as pd
import glob
import csv
import os
import re
import importlib
from matplotlib import pyplot as plt
from rasterio import plot as rasterplot
from shapely.geometry import MultiPolygon, Polygon

import FunFeatShape as FeatShp
importlib.reload(FeatShp)

# A cross-platform way to get the home directory
home = expanduser("~")

pd.set_option("display.max_columns", 1000)
CRS = 3857  # TODO: Check!   # 3857 (meters) | 4326 (degress, WGS84)

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


# Geométricas: area, perim, complexity_measure, spreading, shape_factor, hu_moment, circularity, ratio
with open('stats.csv', 'w') as f1:
    writer = csv.writer(f1, delimiter=";", lineterminator='\n')
    # _ = writer.writerow(['IMG_NAME', 'ID_VECT', 'ID_POLYG', 'CENTR_KM_LAT', 'CENTR_KM_LON',
    #                      'SHP_AREA_KM2', 'SHP_PERIM_KM', 'SHP_COMPLEX_MEAS', 'SHP_SPREAD', 'SHP_FACT',
    #                      'SHP_HU_MOM1', 'SHP_HU_MOM2', 'SHP_HU_MOM3', 'SHP_HU_MOM4', 'SHP_HU_MOM5', 'SHP_HU_MOM6', 'SHP_HU_MOM7',
    #                      'SHP_CIRCUL', 'SHP_PER_AREA_RATIO'])

    idx_img = 0
    fname_img = fnames_img16[idx_img]
    # Loop pelas imagens TIF encontradas no diretório
    for idx_img in range(len(fnames_img16)):
        fname_img = fnames_img16[idx_img]
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

        # Plota uma imagem com todos os polígonos da imagem e uma imagem para cada polígono da imagem
        # vets_img.plot();
        idx_vet = 0
        for idx_vet in range(len(vets_img)):
            # Captura polígono (pode ser multipolígono mesmo sendo polígono único)
            multipol_df = vets_img.iloc[[idx_vet]]
            # Transforma cada multipolígono lista de polígonos
            pol_df = multipol_df.explode(index_parts=True)
            idx_pol = 0
            pol = pol_df.iloc[idx_pol]
            for idx_pol in range(len(pol_df)):
                # row = [bname, str(idx_vet).rjust(3, '0'), str(idx_pol).rjust(3, '0')]
                row = {'IMG_NAME': bname,
                       'ID_VECT': idx_vet, 'ID_POLYG': idx_pol}

                print(row)
                # polygon's geometry georrefeenced in degrees
                pol_deg = pol_df.iloc[[idx_pol]]
                # importlib.reload(FeatShp)
                shape_features = FeatShp.get_shape_features(pol_deg)

                line = row | shape_features  # Contatena os dicts
                # Escreve o header do CSV se for o primeiro polog analisado
                if idx_img == 0 and idx_vet == 0 and idx_pol == 0:
                    _ = writer.writerow(line.keys())
                # Escreve a linha
                _ = writer.writerow(line.values())


# Plotting
pol_deg.geometry.plot(facecolor='w', edgecolor='red')
# pol_deg.plot()
# plt.savefig(f"{dir_img}{os.sep}{bname.replace(".tif", "")}_Vet{str(idx_vet).rjust(3, '0')}_Pol{str(idx_pol).rjust(3, '0')}.png");
# plt.close();
plt.show()

print(pol_deg.bounds)
f, ax = plt.subplots()
# rasterplot.show(tiff,  # use tiff.read(1) with your data
#                 # minx, maxx, miny, maxy
#                 extent=[pol_deg.bounds.minx, pol_deg.bounds.maxx,
#                         pol_deg.bounds.miny, pol_deg.bounds.maxy],
#                 ax=ax,
#                 )

data, _ = rasterio.mask.mask(tiff, shapes=seg, crop=True)
rasterplot.show(data, ax=ax)
# rasterplot.show(pol_deg, ax=ax)
# plot shapefiles
# pol_deg.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
# plt.savefig('test.jpg')
plt.show()

with rasterio.open(fname_img) as src:
    data, _ = rasterio.mask.mask(src, shapes=bbox, crop=True)


fig = plt.figure(figsize=[12, 8])
# Plot the raster data using matplotlib
ax = fig.add_axes([0, 0, 1, 1])
raster_image = ax.imshow(data[0, :, :], cmap="terrain", vmax=5000, vmin=-4000)
fig.colorbar(raster_image, ax=ax, label="Elevation (in m) ",
             orientation='vertical', extend='both', shrink=0.5)
plt.show()


# ================================================================
# Open the raster data using rasterio
data, _ = rasterio.mask.mask(tiff, shapes=pol_deg.geometry, crop=True)

fig = plt.figure(figsize=[12, 8])
# Plot the raster data using matplotlib
ax = fig.add_axes([0, 0, 1, 1])
raster_image = ax.imshow(data[0, :, :], cmap="terrain", vmax=5000, vmin=-3000)
fig.colorbar(raster_image, ax=ax, label="Elevation (in m) ",
             orientation='vertical', extend='both', shrink=0.5)
plt.show()


xmin, xmax, ymin, ymax = float(pol_deg.bounds.minx), float(
    pol_deg.bounds.maxx), float(pol_deg.bounds.miny), float(pol_deg.bounds.maxy)
bbox = MultiPolygon(
    [Polygon([[xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin]])])
tiff2 = rasterio.open(fname_img, masked=False, chunks=True)
tiff2.shape
out_img, out_transform = rioMask(tiff2, shapes=bbox, crop=False)
ax = rasterplot.show(out_img, cmap="gray", shapes=bbox)
# pol_deg.boundary.plot(ax=ax) # ax=ax)
plt.show()


# Check your coordinate ordering,
# I wasn't sure which was X and which was Y
ulx, uly = 5773695.0, 601200.0
width, height = 700, 500

with rasterio.open('/path/to/someraster') as ds:
    # Note - index takes coordinates in X,Y order
    #        and returns row, col (Y,X order)
    row, col = ds.index(ulx, uly)
    window = Window(row, col, width, height)
    data = ds.read(window)
