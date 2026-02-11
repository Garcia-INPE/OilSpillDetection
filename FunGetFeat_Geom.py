import warnings
import cv2
import math
import logging
import importlib
import numpy as np
from shapely import Polygon
import rasterio
from rasterio.mask import mask
from rasterio import plot as rasterplot
import geopandas as gpd
from matplotlib import pyplot as plt
import Functions as Fun
importlib.reload(Fun)

area_factor = 1000000
len_factor = 1000

# https://learnopencv.com/shape-matching-using-hu-moments-c-python/
# https://stackoverflow.com/questions/40132542/get-a-cartesian-projection-accurate-around-a-lat-lng-pair/40140326#40140326
# https://epsg.io/4087

# EPSG:4326 (LATLON Projection, degress)
# EPSG:3857 (Cylindrical, meters), match only at the equator
# EPSG:31983 (SIRGAS 2000 / UTM zone 23S).
# EPSG:3395  (World Mercator)
# EPSG:32663 (WGS84 Equidistance Cylindrical)
# EPSG:4087  (Cylindrical projection)
# https://proj.org/en/9.4/operations/projections/


def get_feat_geom(gdf_poly, dict_ret):
    # dict_ret = dict_feat_geom
    #
    # Geométricas (Melissa): area (a), perim (p), complexity_measure (c),  spreading (s), shape_factor, hu_moment, circularity, ratio
    #
    # METHOD 1 for centroid estipulation --> CRS = 32615 (CORRECT) -------------------------------
    # ABOUT THE WARNING MSG:
    #   The association between degrees and true distance varies over the surface of the earth and we cannot assume it works for everywhere.
    #   But, it will be incorrect only when the locations is at high distortion area of the projection in use.
    #   https://stackoverflow.com/questions/66296214/python-covert-geopandas-centroid-to-latitude-longitude-coordinates

    # Capture UserWarnig in order to make the program do not stop
    warnings.filterwarnings("ignore", category=UserWarning)
    # logging.captureWarnings(True)
    centr_deg_lat = gdf_poly.centroid.y.iloc[0]
    centr_deg_lon = gdf_poly.centroid.x.iloc[0]
    # logging.captureWarnings(False)
    # Disable capture of warnings
    warnings.filterwarnings("default", category=UserWarning)

    # Find UTM Zone from (Latitude, Longitude)
    utm_zone = Fun.get_utm_zone(centr_deg_lat, centr_deg_lon)

    # METHOD 2 for centroid estipulation --> CRS = 32634 (WRONG) ---------------------------------
    # Polygon's bbox in degrees: minx, miny, maxx, maxy
    # minx_deg, miny_deg, maxx_deg, maxy_deg = pol_deg.total_bounds
    # Centroid of the polygons's bbox in degrees
    # centr_deg_lat = (miny_deg+maxy_deg)/2
    # centr_deg_lon = (miny_deg+maxy_deg)/2

    # Calcula o EPSG correto para o centroide do bbox do polígono
    # Para poder calcular estatísticas em metros
    utm_zone2, CRS = Fun.get_epsg_from_latlon(centr_deg_lat, centr_deg_lon)

    # Polygon's geometry georrefeenced in meters
    pol_m = gdf_poly.to_crs(CRS)
    # meter/area_factor = in km2
    area_km2 = pol_m.area.iloc[0]/area_factor
    # m/len_factor = in km
    perim_km = pol_m.length.iloc[0]/len_factor

    complexity = (perim_km ** 2) / area_km2
    minx, miny, maxx, maxy = pol_m.total_bounds / \
        len_factor                       # Polygon's bbox in meters
    len_km = (maxx - minx)
    wid_km = (maxy - miny)
    spread_km = (wid_km / len_km)

    shp_fact_km = (perim_km ** 2) / (4 * np.pi * area_km2)
    circularity = (4 * np.pi * area_km2) / (perim_km ** 2)

    hu_moms = get_huMomentun(pol_m)      # Hu Momentuns

    perim_area_ratio = perim_km / area_km2

    dict_ret["CENTR_KM_LAT"] = centr_deg_lat
    dict_ret["CENTR_KM_LON"] = centr_deg_lon
    dict_ret["UTM_ZONE"] = utm_zone
    dict_ret["AREA_KM2"] = area_km2
    dict_ret["PERIM_KM"] = perim_km
    dict_ret["COMPLEX_MEAS"] = complexity
    dict_ret["SPREAD"] = spread_km
    dict_ret["SHP_FACT"] = shp_fact_km
    dict_ret["HU_MOM1"] = hu_moms[0]
    dict_ret["HU_MOM2"] = hu_moms[1]
    dict_ret["HU_MOM3"] = hu_moms[2]
    dict_ret["HU_MOM4"] = hu_moms[3]
    dict_ret["HU_MOM5"] = hu_moms[4]
    dict_ret["HU_MOM6"] = hu_moms[5]
    dict_ret["HU_MOM7"] = hu_moms[6]
    dict_ret["CIRCULARITY"] = circularity
    dict_ret["PERI_AREA_RATIO"] = perim_area_ratio
    return (dict_ret)


def get_huMomentun(pol):
    fname = "pol.jpg"
    pol.plot()
    # plt.show()
    plt.savefig(fname)
    plt.close()

    # Read image as grayscale image
    im = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
    moments = cv2.moments(im)                           # Calculate Moments
    # Calculate Hu Moments
    huMoments = cv2.HuMoments(moments)
    # Hu Moments have a large range. Some hu[i] are not comparable in magnitude, a log transform brings them in the same range
    i = 0
    for i in range(0, 7):
        huMoments[i] = -1 * \
            math.copysign(1.0, huMoments[i][0]) * \
            math.log10(abs(huMoments[i][0]))
    return ([x.tolist()[0] for x in huMoments])
