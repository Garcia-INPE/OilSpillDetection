import os
import cv2
import math
import numpy as np
import importlib
import logging
import geopandas as gpd
from matplotlib import pyplot as plt

import FunDiv as FDiv
importlib.reload(FDiv)

area_factor = 1000000  # 1000 x 1000
len_factor = 1000


def get_huMomentun(pol_m):
    # https://learnopencv.com/shape-matching-using-hu-moments-c-python/
    fname = "pol_huMom.jpg"
    pol_m.plot()
    # plt.show()
    plt.savefig(fname)
    plt.close()

    # Read image as grayscale image
    im = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
    moments = cv2.moments(im)           # Calculate Moments
    huMoments = cv2.HuMoments(moments)  # Calculate Hu Moments
    # Hu Moments have a large range. Some hu[i] are not comparable in magnitude,
    # a log transform brings them in the same range
    i = 0
    for i in range(0, 7):
        huMoments[i] = -1 * \
            math.copysign(1.0, huMoments[i][0]) * \
            math.log10(abs(huMoments[i][0]))
    os.remove(fname)

    return {f"SHP_HU_MOM{(i+1)}": float(x[0]) for i, x in enumerate(huMoments)}


def get_shape_features(pol_deg, plot_pol=False):

    # In order to calculate area and perimeter we need to reproject the polygon in a equal-area
    # projection, like in meters, but using a fixed CRS is not correct because the projection wont't be so
    # precise is everywhare. We need to calculate the correct UTM
    # CRS = 3857 (meters) | 4326 (degress, WGS84)
    centr_deg_lat, centr_deg_lon = FDiv.get_centroid(pol_deg)
    CRS = FDiv.get_epsg_from_latlon(centr_deg_lat, centr_deg_lon)

    # polygon's geometry georrefeenced in meters (corrected position)
    pol_m = pol_deg.to_crs(CRS)

    bounds = {'LOC_POL_BBOX_X1_DEG': float(pol_deg.bounds.minx.iloc[0]),
              'LOC_POL_BBOX_X2_DEG': float(pol_deg.bounds.maxx.iloc[0]),
              'LOC_POL_BBOX_Y1_DEG': float(pol_deg.bounds.miny.iloc[0]),
              'LOC_POL_BBOX_Y2_DEG': float(pol_deg.bounds.maxy.iloc[0]),
              'LOC_POL_BBOX_X1_M': float(pol_m.bounds.minx.iloc[0]),
              'LOC_POL_BBOX_X2_M': float(pol_m.bounds.maxx.iloc[0]),
              'LOC_POL_BBOX_Y1_M': float(pol_m.bounds.miny.iloc[0]),
              'LOC_POL_BBOX_Y2_M': float(pol_m.bounds.maxy.iloc[0])}

    # m/1000 = km
    centr_m_lat = pol_m.centroid.iloc[0].y/area_factor
    # m/1000 = km
    centr_m_lon = pol_m.centroid.iloc[0].x/area_factor
    # m2/1000000 = km2
    area_km = float(pol_m.area.iloc[0]/area_factor)
    # m/1000 = in km
    perim_km = float(pol_m.length.iloc[0]/area_factor)
    complexity = float((perim_km ** 2) / area_km)
    minx, miny, maxx, maxy = pol_m.total_bounds             # bounding box
    len_km = (maxx - minx)/len_factor
    wid_km = (maxy - miny)/len_factor
    spread_km = float(wid_km / len_km)
    shp_fact_km = float(perim_km / (4 * np.sqrt(area_km)))  # TODO: verificar
    circul_km = float((perim_km ** 2) / (4 * np.pi * area_km))
    perim_area_ratio = float(perim_km / area_km)

    shp_feat = {'LOC_CENTR_KM_LAT': centr_m_lat, 'LOC_CENTR_KM_LON': centr_m_lon,
                'SHP_AREA_KM2': area_km, 'SHP_PERIM_KM': perim_km, 'SHP_COMPLEX_MEAS': complexity,
                'SHP_SPREAD': spread_km, 'SHP_FACT': shp_fact_km, 'SHP_CIRCUL': circul_km,
                'SHP_PER_AREA_RATIO': perim_area_ratio}
    hu_mom = get_huMomentun(pol_m)

    # Merges the dictionaries before returning
    return (bounds | shp_feat | hu_mom)
