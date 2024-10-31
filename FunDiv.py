import os
import re
import math
import logging
import numpy as np
from rasterio.mask import mask
from sklearn.preprocessing import MinMaxScaler


def get_xy_from_lonlat(tiff16):
    hei, wid = tiff16.shape
    left, bottom, right, top = tiff16.bounds

    len_lon = right-left
    step_lon = len_lon / wid
    step_pix = wid / len_lon


def scaler(ma2d, a=0, b=1):
    data = ma2d.ravel().reshape(-1, 1)
    scaler = MinMaxScaler((a, b))
    scaler.fit(data)
    return scaler.transform(data).astype(np.int16)


def get_masked_array_from_vector(raster, vectors, filled=False, crop=True, invert=False, nodata=np.nan):
    # raster=tiff16; vectors=pol_deg = gdf_pol.geometry; filled=False; crop=True; invert=False; nodata=np.nan
    """
    Do the clip operation (creates a MaskedArray with the polygon only)
    Pixels are masked or set to nodata outside the input shapes, unless
    Resources: https://atcoordinates.info/2023/05/30/clipping-rasters-and-extracting-values-with-geospatial-python/
               https://py.geocompx.org/05-raster-vector
    filled: If True, the pixels outside the features will be set to nodata. Output is np.ndarray. \
            If False, the output array will contain the original pixel data, and only the mask will \
                be based on shapes. Output is np.MaskedArray. Defaults to True.
    crop: Whether to crop the raster to the extent of the shapes. Defaults to False.
    """
    # Cria o masked array ou array
    masked_array, transform = mask(
        raster, vectors, filled=filled, crop=crop, invert=invert, nodata=nodata, pad=True)

    """
    When you operate on masked arrays, it takes the union of the masks involved in the operation.
    The package ensures that masked entries are not used in computations.
    Mask = True means data was masked (invalid)
    Mask = False means data was unmasked (valid)
    np.ma.getmask(masked).max()
    masked.min(), masked.max()
    np.min(masked), np.max(masked)
    np.ma.min(masked), np.ma.max(masked)
    raste.shape, masked_raster.shape
    """
    # masked_data = raster.read(1)  # Retorna um Numpy array
    # masked_data.shape, raster.shape
    """ 
    Attributes for MakedArray
    type(masked_array)  # Numpy MaskedArray
    masked_array.data
    masked_array.mask
    masked_array.fill_value
    masked_array.shape
    """
    # Copy the metadata from the source and update the new clipped layer
    meta = raster.meta.copy()
    meta.update({
        "driver": "GTiff",
        "height": masked_array.shape[1],  # height starts with shape[1]
        "width": masked_array.shape[2],   # width starts with shape[2]
        "transform": transform,
        "nodata": nodata,
        "crs": raster.crs.data})
    """
    masked_data.min(), masked_data.max()
    np.min(masked_data), np.max(masked_data)
    np.ma.min(masked_data), np.ma.max(masked_data)
    """
    return (masked_array, transform)


def get_centroid(pol_deg):
    # pol_deg = gdf_pol.geometry
    # https://gis.stackexchange.com/questions/372564/userwarning-when-trying-to-get-centroid-from-a-polygon-geopandas
    # CRS = 3857 (meters) | 4326 (degress, WGS84)
    # ---------------------------------------------------------------------
    # 1) METHOD default for centroid estipulation
    # A warning raises but, at the end, calculated area and perim values
    # match DS values
    # ---------------------------------------------------------------------
    logging.captureWarnings(True)
    default_centroid = float(pol_deg.geometry.centroid.y), float(
        pol_deg.geometry.centroid.x)
    logging.captureWarnings(False)

    # ---------------------------------------------------------------------
    # 2) METHOD medium point for centroid estipulation (JR)
    # ---------------------------------------------------------------------
    # minx_deg, miny_deg, maxx_deg, maxy_deg = [
    #     float(pol_deg.geometry.bounds[x]) for x in ['minx', 'miny', 'maxx', 'maxy']]
    # medium_point_centroid = (miny_deg+maxy_deg)/2, (minx_deg+maxx_deg)/2

    # ---------------------------------------------------------------------
    # 3) METHOD Projection MERCATOR for centroid estipulation
    # ---------------------------------------------------------------------
    # centroid_mercator = pol_deg.to_crs(
    #     'epsg:3785').centroid.to_crs(pol_deg.crs)
    # centroid_mercator = float(centroid_mercator.y), float(centroid_mercator.x)

    # ---------------------------------------------------------------------
    # 4) METHOD Projection equal area for centroid estipulation
    # ---------------------------------------------------------------------
    # centroid_equal_area = pol_deg.to_crs(
    #     '+proj=cea').centroid.to_crs(pol_deg.crs)
    # centroid_equal_area = float(
    #     centroid_equal_area.y), float(centroid_equal_area.x)

    # ---------------------------------------------------------------------
    # 5) METHOD Projection in meters for centroid estipulation
    # Idem MERCATOR
    # ---------------------------------------------------------------------
    # centroid_m = pol_deg.to_crs(3857).centroid.to_crs(pol_deg.crs)
    # centroid_m = float(centroid_m.y), float(centroid_m.x)

    # print(
    #     '\nDefault centroid.....:', default_centroid,
    #     '\nMedium Point centroid:', medium_point_centroid,
    #     '\nMercator centroid....:', centroid_mercator,
    #     '\nEqual Area centroid..:', centroid_equal_area,
    #     '\nIn Meters centroid...:', centroid_m)
    return (default_centroid)


def get_epsg_from_latlon(lat, lon):
    # lat=centr_deg_lat; lon=centr_deg_lon
    utm_band = str((math.floor((lon + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
    else:
        epsg_code = '327' + utm_band
    return epsg_code


def get_S1A_fname_fields(dir_raw_data, bname):
    # Finds which dir is the dir associated with the calibrated fname
    # And gets all fields from it (because the name of the calibrated TIFF is incomplete)
    # https://sentiwiki.copernicus.eu/web/s1-products#S1Products-SARNamingConventionS1-Products-SAR-Naming-Convention
    # root_name = "S1A_IW_GRDH_1SDV_20200117T001541_20200117T001606_030833_03899B_5AEE.SAFE"
    root_fname = bname.split(" ")[1][:33]  # Root pattern of the name
    dir_ori_tiff = [d for d in os.listdir(dir_raw_data) if re.match(
        root_fname, os.path.basename(d))][0]
    assert len(dir_ori_tiff) == 67

    mission = dir_ori_tiff[:3]        # S1A     S1A | S1B | S1C                                      # nopep8
    beam_mode = dir_ori_tiff[4:6]     # IW      S[1-6] | IW | EW | WV | EN | N[1-6] | Z[1-6,I,E,W]   # nopep8
    prod_type = dir_ori_tiff[7:10]    # GRD     RAW | SLC | GRD | OCN | ETA                          # nopep8
    res = dir_ori_tiff[10:11]         # H       Full | High | Medium | _ (N/A)                       # nopep8
    proc_lev = dir_ori_tiff[12:13]    # 1       0 | 1 | 2 | A                                        # nopep8
    prod_class = dir_ori_tiff[13:14]  # S       SAR | Annotation | Noise | Calibration | X (only for ETAD product)   # nopep8
    polariz = dir_ori_tiff[14:16]     # DV      SH | SV | DH | DV | HH | HV | VV | VH                # nopep8
    date_on = dir_ori_tiff[17:25]
    hour_on = dir_ori_tiff[26:32]
    date_off = dir_ori_tiff[33:41]
    hour_off = dir_ori_tiff[42:48]
    orbit = dir_ori_tiff[49:55]
    take_id = dir_ori_tiff[56:62]
    prod_id = dir_ori_tiff[63:67]
    return {'mission': mission, 'beam_mode': beam_mode, 'prod_type': prod_type, 'res': res, 'proc_lev': proc_lev,
            'prod_class': prod_class, 'polariz': polariz, 'date_on': date_on, 'hour_on': hour_on, 'date_off': date_off,
            'hour_off': hour_off, 'orbit': orbit, 'take_id': take_id, 'prod_id': prod_id}
