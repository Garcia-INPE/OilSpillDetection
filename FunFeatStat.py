from shapely import geometry
from rasterio import plot as rasterplot
from rasterio.mask import mask
# from rasterio.plot import show
from matplotlib import pyplot as plt
from shapely.geometry import Polygon, box

import os
import json
import warnings
import rasterio
import geopandas as gpd
import importlib
import numpy as np

import FunDiv
from Config import *
marg_exp = 0.0005

importlib.reload(FunDiv)


def get_stat_features(gdf_img_polys, pol_deg, tiff16, plot=False):
    # pol_deg = gdf_pol.geometry
    warnings.filterwarnings('error')

    # -----------------------------------------------------------------------
    # Part 1) Statistics from inside of the polygon
    # -----------------------------------------------------------------------
    # Gets only the polygon
    masked_pol, _ = FunDiv.get_masked_array_from_vector(
        tiff16, pol_deg.geometry, filled=False, crop=True, invert=False)

    # Check it by plotting it
    # plt.imshow(masked_pol[0, :, :]); plt.show()
    # pol_deg.plot(); plt.show()

    # Checa se todos os valores da máscara são True
    # Que significa que todos estão escondidos (mascarado)
    # if not masked_bg.mask.all():
    dict_in = {"IN_STD": float(np.ma.std(masked_pol)),
               "IN_VAR": float(np.ma.var(masked_pol)),
               "IN_MIN": float(np.ma.min(masked_pol)),
               "IN_MAX": float(np.ma.max(masked_pol)),
               "IN_MEAN": float(np.ma.mean(masked_pol)),
               "IN_MEDIAN": float(np.ma.median(masked_pol)),
               "IN_VAR_COEF": float(np.ma.std(masked_pol) / np.ma.mean(masked_pol)),
               "IN_NUM_PIXELS ": int(np.sum(~masked_pol.mask))}
    # Soma os Falses, valores não mascarados

    # -----------------------------------------------------------------------
    # Part 2) Statistics of the ocean outside the polygon being analysed
    # Consider the expanded bbox of the polygon and don't consider the
    # polygon and all other possible polygons inside the expandex bbox
    # Intuition: save the expanded bbox as tiff and clip it with the
    # gdf of all polygons
    # -----------------------------------------------------------------------
    # pol_deg = gdf_pol.geometry
    minx, maxx, miny, maxy = float(pol_deg.bounds.minx.iloc[0]), float(
        pol_deg.bounds.maxx.iloc[0]), float(pol_deg.bounds.miny.iloc[0]), float(pol_deg.bounds.maxy.iloc[0])
    minx -= marg_exp
    maxx += marg_exp
    miny -= marg_exp
    maxy += marg_exp

    gdf_coords = gpd.GeoDataFrame(
        {'geometry':
            Polygon([(minx, maxy), (maxx, maxy), (maxx, miny), (minx, miny), (minx, maxy)])},
        index=[0], crs=tiff16.crs)
    # https://automating-gis-processes.github.io/CSC/notebooks/L5/clipping-raster.html
    coords = [json.loads(gdf_coords.to_json())
              ['features'][0]['geometry']]

    # Clipping the bbox area
    nodata = np.nan
    out_img, out_transform = mask(
        dataset=tiff16, shapes=coords, crop=True, nodata=nodata)

    out_meta = tiff16.meta.copy()
    # epsg_code = int(tiff.crs.data['init'][5:])
    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                     "width": out_img.shape[2],
                     "transform": out_transform,
                     # pycrs.parse.from_epsg_code(epsg_code).to_proj4()}
                     "crs": tiff16.crs.data}
                    )
    with rasterio.open("Clipped16.tiff", "w", **out_meta) as dest:
        dest.write(out_img)

    clipped = rasterio.open("Clipped16.tiff")
    assert clipped.shape == out_img[0].shape
    # rasterplot.show(clipped, cmap="gray")

    # Gets only the ocean
    masked_pol, _ = FunDiv.get_masked_array_from_vector(
        clipped, gdf_img_polys.geometry, filled=False, crop=False, invert=True)

    dict_out = {}
    try:
        dict_out["OUT_STD"] = float(np.ma.std(masked_pol))
    except:
        dict_out["OUT_STD"] = None
    try:
        dict_out["OUT_MIN"] = float(np.ma.min(masked_pol))
    except:
        dict_out["OUT_MIN"] = None
    try:
        dict_out["OUT_MAX"] = float(np.ma.max(masked_pol))
    except:
        dict_out["OUT_MAX"] = None
    try:
        dict_out["OUT_MEAN"] = float(np.ma.mean(masked_pol))
    except:
        dict_out["OUT_MEAN"] = None
    try:
        dict_out["OUT_MEDIAN"] = float(np.ma.median(masked_pol))
    except:
        dict_out["OUT_MEDIAN"] = None
    try:
        dict_out["OUT_VAR_COEF"] = float(
            np.ma.std(masked_pol) / np.ma.mean(masked_pol))
    except:
        dict_out["OUT_VAR_COEF"] = None

    warnings.filterwarnings('error')
    return (dict_in | dict_out)
