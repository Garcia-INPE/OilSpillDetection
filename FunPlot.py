import matplotlib.image as mpimg
from Config import *
from matplotlib import pyplot as plt
from rasterio.mask import mask
from shapely.geometry import Polygon
import numpy as np
import geopandas as gpd

# dict = dict_tiff | dict_head_vect | dict_head_pol | dict_shape_feat | dict_tail_vect


def plot_pol(gdf_pol, pol_info):
    # Plot the polygon filled shape (individually)
    dir_img_pol = f"{dir_img}/filled-pol_white-bg_png/"
    if not os.path.exists(dir_img_pol):
        os.makedirs(dir_img_pol)

    fname_img_pol = f"{
        dir_img_pol}/{pol_info["IMG_NAME"].replace(".tif", "")}_ID-VECT={pol_info['ID_VECT']}_IDX-POLYG={pol_info['IDX_POLYG']}.jpg"
    gdf_pol.plot()
    plt.axis('off')
    # plt.show()
    plt.savefig(fname_img_pol, bbox_inches='tight', pad_inches=0)
    plt.close()
    return


def read_png(fname_img):
    image = mpimg.imread(fname_img)
    plt.imshow(image, cmap="gray")
    plt.show()
    return


def plot_bbox_png(gdf_pol, tiff16, pol_info):
    # Plot the polygon's bbox (and eventually other nearby polygons)
    dir_img_pol = f"{dir_img}/value-8bit_pol_bbox_png/"
    if not os.path.exists(dir_img_pol):
        os.makedirs(dir_img_pol)
    fname_img_pol = f"{
        dir_img_pol}/{pol_info["IMG_NAME"].replace(".tif", "")}_ID-VECT={pol_info['ID_VECT']}_IDX-POLYG={pol_info['IDX_POLYG']}.jpg"

    # gdf_pol = gdf_img_polys.iloc[[0]]
    minx, maxx, miny, maxy = float(gdf_pol.bounds.minx.iloc[0]), float(
        gdf_pol.bounds.maxx.iloc[0]), float(gdf_pol.bounds.miny.iloc[0]), float(gdf_pol.bounds.maxy.iloc[0])

    areabbox = gpd.GeoDataFrame(
        {'geometry':
            Polygon([(minx, maxy), (maxx, maxy), (maxx, miny), (minx, miny), (minx, maxy)])},
        index=[0], crs=tiff16.crs)

    nodata = np.nan
    out_raster, _ = mask(
        tiff16, areabbox.geometry, filled=True, crop=True, nodata=nodata)
    out_raster.shape
    # [np.where(np.isnan(out_raster))]
    # rasterplot.show(out_raster, cmap="gray")

    # Removing rows and cols with all values 0
    out_raster2d = out_raster[0]
    out_raster2d = out_raster2d[:, ~np.isnan(out_raster2d).all(axis=0)]
    out_raster2d = out_raster2d[~np.isnan(out_raster2d).all(axis=1), :]
    out_raster2d.shape
    # rasterplot.show(out_raster2d, cmap="gray")
    plt.imshow(out_raster2d, cmap='gray')
    plt.axis('off')
    # plt.show()
    plt.savefig(fname_img_pol, bbox_inches='tight', pad_inches=0)
    return
