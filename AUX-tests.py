import math
import numpy as np
import importlib

import FunDiv
np.set_printoptions(suppress=True)

importlib.reload(FunDiv)


# Testing my algo
lon = float(gdf_pol.bounds.minx.iloc[0])
lat = float(gdf_pol.bounds.miny.iloc[0])
x1, y1 = FunDiv.get_x_from_lon(
    tiff16, lon, 1), FunDiv.get_y_from_lat(tiff16, lat, 1)
lon = float(gdf_pol.bounds.maxx.iloc[0])
lat = float(gdf_pol.bounds.maxy.iloc[0])
x2, y2 = FunDiv.get_x_from_lon(
    tiff16, lon, 1), FunDiv.get_y_from_lat(tiff16, lat, 1)


# testing other algo
lon = float(gdf_pol.bounds.minx.iloc[0])
lat = float(gdf_pol.bounds.miny.iloc[0])
x1, y1 = FunDiv.get_img_xy_from_latlon(tiff16, lat, lon)
x1, y1 = int(x1), int(y1)

lon = float(gdf_pol.bounds.maxx.iloc[0])
lat = float(gdf_pol.bounds.maxy.iloc[0])
x2, y2 = FunDiv.get_img_xy_from_latlon(tiff16, lat, lon)
x2, y2 = math.ceil(x2), math.ceil(y2)
tiff16.read()[0, x1:(x2+1), y1:(y2+1)]


# gdf_pol.bounds
# get_xy_from_lonlat(tiff16,
#                    float(gdf_pol.bounds.minx.iloc[0]), float(
#                        gdf_pol.bounds.miny.iloc[0]),
#                    float(gdf_pol.bounds.maxx.iloc[0]), float(gdf_pol.bounds.maxy.iloc[0]))
# resx = abs(float(pol_deg.bounds.maxx.iloc[0]-pol_deg.bounds.minx.iloc[0]))
# f'{resx:.20f}'
# resy = abs(float(pol_deg.bounds.maxy.iloc[0]-pol_deg.bounds.miny.iloc[0]))
# f'{resy:.20f}'
