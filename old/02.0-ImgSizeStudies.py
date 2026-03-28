"""
   Do studies about the target size of images
"""

import os
import importlib

os.chdir("/home/jrmgarcia/ProjDocs/OilSpill/src")

import rasterio
import Config as Cfg  # nopep8

# Set directories and load data based on the specified bit depth (8 or 16)
importlib.reload(Cfg)


bboxes = []

# Iterate among geometries in Cfg.VECTORS (shapefile) and create a list of the dimension of the bounding boxes
for idx, row in Cfg.VECTORS.iterrows():
    geom = row.geometry
    minx, miny, maxx, maxy = geom.bounds
    width = maxx - minx
    height = maxy - miny
    bboxes.append((width, height))

bboxes = sorted(bboxes, key=lambda x: x[0] * x[1], reverse=True)

# List all dimension of images in /home/jrmgarcia/ProjDocs/OilSpill/src/dataout/DS/IMAGES/IMG-RGB
img_files = os.listdir(Cfg.DIR_OUT_IMG)
img_dims = []
for img_file in img_files:
    img_path = os.path.join(Cfg.DIR_OUT_IMG, img_file)
    with rasterio.open(img_path) as src:
        width = src.width
        height = src.height
        img_dims.append((width, height))
img_dims = sorted(img_dims, key=lambda x: x[0] * x[1], reverse=True)

# show the top 10 widths of img_dims
print("Top 10 widths of img_dims:")
wid = sorted([img_dims[i][0] for i in range(len(img_dims))], reverse=True)
print(wid[:10])

print("Top 10 heights of img_dims:")
hei = sorted([img_dims[i][1] for i in range(len(img_dims))], reverse=True)
print(hei[:10])
