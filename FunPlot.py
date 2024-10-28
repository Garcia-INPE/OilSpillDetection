from matplotlib import pyplot as plt
from rasterio.mask import mask
from rasterio import plot as rasterplot
from shapely.geometry import Polygon

import json
import rasterio
import numpy as np
import geopandas as gpd
import matplotlib.image as mpimg

from Config import *

np.set_printoptions(suppress=True)

# dict = dict_tiff | dict_head_vect | dict_head_pol | dict_shape_feat | dict_tail_vect


def plot_pol(gdf_pol, pol_info):
    # Plot the filled polygon in lightblue (individually)
    dir_img_pol = f"{dir_img}/png_filled-bbox_white-bg/"
    if not os.path.exists(dir_img_pol):
        os.makedirs(dir_img_pol)

    fname_img_pol = f"{
        dir_img_pol}/{pol_info["ID_IMG"]}_{pol_info['ID_VECT']}_{pol_info['IDX_POLYG']}.png"
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


def plot_bbox_png(gdf_pol, tiff8, pol_info, marg_exp=0.0005):
    # Plot the polygon's bbox (and eventually other nearby polygons) and its contour
    # marg_exp = Margin expansion for each slick, in deg (CARE!)

    # Always replace content
    fname_img_tiff = f"{dir_img}/Clipped_pol_bbox.tiff"
    segs = ["+PolSeg", "-PolSeg"]
    v = "ori8bits"
    dir_img_bbox = f"{dir_img}/png_8b_bbox_m{marg_exp}d_{v}/"
    if not os.path.exists(dir_img_bbox):
        os.makedirs(dir_img_bbox)

    # ===================================================================
    # Defining the clipping area based on the polygon
    # ===================================================================
    # gdf_pol = gdf_img_polys.iloc[[0]]
    minx, maxx, miny, maxy = float(gdf_pol.bounds.minx.iloc[0]), float(
        gdf_pol.bounds.maxx.iloc[0]), float(gdf_pol.bounds.miny.iloc[0]), float(gdf_pol.bounds.maxy.iloc[0])
    minx -= marg_exp
    maxx += marg_exp
    miny -= marg_exp
    maxy += marg_exp

    # BBox in diff types of object
    # bbox_tuple = (minx, maxx, miny, maxy)    # BBox as tuple
    # bbox_polyg = box(minx, miny, maxx, maxy)   # BBox as Polygon
    gdf_coords = gpd.GeoDataFrame(
        {'geometry':
            Polygon([(minx, maxy), (maxx, maxy), (maxx, miny), (minx, miny), (minx, maxy)])},
        index=[0], crs=tiff8.crs)

    # https://automating-gis-processes.github.io/CSC/notebooks/L5/clipping-raster.html
    coords = [json.loads(gdf_coords.to_json())
              ['features'][0]['geometry']]
    # coords = gdf_pol.geometry

    # Prepare the clipped area
    nodata = 256.0
    out_img, out_transform = mask(
        dataset=tiff8, shapes=coords, crop=True, nodata=nodata)

    # Removing rows and cols with all values = <nodata>
    out_img2d = out_img[0].copy()
    out_img2d = out_img2d[:, ~(out_img2d == nodata).all(axis=0)]
    out_img2d = out_img2d[~(out_img2d == nodata).all(axis=1), :]
    out_img = np.expand_dims(out_img2d, axis=0)  # Replace raster array
    # out_img.shape

    out_meta = tiff8.meta.copy()
    # epsg_code = int(tiff.crs.data['init'][5:])
    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                     "width": out_img.shape[2],
                     "transform": out_transform,
                     # pycrs.parse.from_epsg_code(epsg_code).to_proj4()}
                     "crs": tiff8.crs.data}
                    )
    with rasterio.open(fname_img_tiff, "w", **out_meta) as dest:
        dest.write(out_img)

    clipped = rasterio.open(fname_img_tiff)
    assert clipped.shape == out_img[0].shape
    seg = segs[0]
    for seg in segs:
        dir_img_bbox = f"{dir_img}/png_8b_bbox_m{marg_exp}d_{v}/"
        fname_img_png = f"{
            dir_img_bbox}/{pol_info["ID_IMG"]}_{pol_info['ID_VECT']}_{pol_info['IDX_POLYG']}_{seg}.png"
        _, ax = plt.subplots()
        rasterplot.show(clipped, cmap='gray', ax=ax)
        if seg == "+PolSeg":
            gdf_pol.plot(ax=ax, edgecolor="red", facecolor="none", lw=3)
        ax.set_axis_off()
        plt.axis('off')
        plt.tight_layout()
        # plt.show()
        plt.savefig(fname_img_png, bbox_inches='tight', pad_inches=0)
        plt.close()

    # image = mpimg.imread("clip+seg.png")
    # plt.imshow(image)
    # plt.show()


# ----

    # nodata = np.nan
    # out_raster, out_transform = mask(
    #     tiff16, gdf_coords.geometry, filled=True, crop=True, nodata=nodata)
    # # out_raster.shape
    # # [np.where(np.isnan(out_raster))]
    # # rasterplot.show(out_raster, cmap="gray")

    # # Removing rows and cols with all values 0
    # out_raster2d = out_raster[0]
    # out_raster2d = out_raster2d[:, ~np.isnan(out_raster2d).all(axis=0)]
    # out_raster2d = out_raster2d[~np.isnan(out_raster2d).all(axis=1), :]

    # # out_raster2d.shape

    # _, ax = plt.subplots()
    # rasterplot.show(tiff16, cmap="gray", ax=ax, extent=extent)
    # # rasterplot.show(tiff16, cmap="gray", ax=ax2, with_bounds=True)
    # plt.show()

    # # from rasterio.plot import plotting_extent
    # # extend = plotting_extent(tiff16)
    # extent = (minx, maxx, miny, maxy)
    # data = tiff16.read(1)

    # # ------
    # from shapely.geometry import mapping
    # geoms = gdf_pol.geometry.values
    # # Get the first and only geometry in the ESRI Shapefile. Your box boundaries.
    # geometry = geoms[0]
    # feature = [mapping(geometry)]  # Required conversion

    # clipped_dataset, out_transform = mask(tiff16, feature, crop=True)
    # clipped_dataset.shape

    # # -------
    # _, ax = plt.subplots()
    # plt.show(clipped_dataset.shape[0], cmap="gray", ax=ax, extent=extent)
    # # gdf_pol.plot(ax=ax, edgecolor="red", facecolor="none", lw=5)
    # plt.tight_layout()
    # plt.show()

    # plt.imshow(data, extent=extent)
    # plt.show()

    # _, ax = plt.subplots()
    # rasterplot.show(tiff16, cmap='gray', ax=ax, with_bounds=True,
    #                 extent=[gdf_pol.bounds.minx, gdf_pol.bounds.maxx, gdf_pol.bounds.miny, gdf_pol.bounds.maxy])
    # plt.show()
    # gdf_pol.plot(facecolor='none', edgecolor='red', linewidth=3, ax=ax)
    # # plt.axis('off')

    # plt.savefig(fname_img_tiff, bbox_inches='tight', pad_inches=0)
    # return


# EXAMPLE: https://stackoverflow.com/questions/61980063/how-to-place-a-shapefile-on-top-of-raster-file-in-one-plot-and-then-save-the-pl
# f, ax = plt.subplots()
# # plot DEM
# rasterplot.show(
#     tiff_band_1,  # use tiff.read(1) with your data
#     extent=tiff_extent,
#     ax=ax,
# )
# # plot shapefiles
# shapefile.plot(ax=ax, facecolor='w', edgecolor='k')
# plt.savefig('test.jpg')
# plt.show()
