import numpy as np
import math
import rasterio
from rasterio.mask import mask

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


def to_8_bits(a):
    # Passa para 8-bit (0-255)
    a8 = (((a-a.min()) /
           (a.max()-a.min())) * ((255-0)+0)).astype(rasterio.uint8)
    return (a8)


def get_masked_array_from_vector(raster, vectors, filled=False, crop=True, invert=False):
    # raster=tiff16; vectors=gdf_pol_deg.geometry; filled=False; crop=True; invert=False
    """
    Do the clip operation (creates a MaskedArray)
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
        raster, vectors, filled=filled, crop=crop, invert=invert, nodata=np.nan)
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
        "transform": transform})
    """
    masked_data.min(), masked_data.max()
    np.min(masked_data), np.max(masked_data)
    np.ma.min(masked_data), np.ma.max(masked_data)
    """
    return (masked_array, transform)


def CheckTIFF(tiff):
    # OPERAÇÕES NO DADO GEORREFERENCIADO DO TIFF -------------
    print(tiff.bounds)
    print(tiff.dataset_mask().min(), tiff.dataset_mask().max())
    print(tiff.dataset_mask)
    print(tiff.statistics(1))
    print(tiff.dtypes)
    print(tiff.res)
    print(tiff.shape)
    print(tiff.crs)
    return


def CRS_test(pol_deg, CRS_to_add=None, area_factor=1000000, len_factor=1000):
    # Testa alguns EPSGs no calculo da area e perimetro
    # O que está dando certo é o calculado a partir da UTM específico
    #    passado em CRS_to_add.

    CRSs_to_test = ["4326", "3857", "31983", "3395", "32663", "4087"]
    if CRS_to_add is not None:
        CRSs_to_test += [CRS_to_add]
    out_area = [None] * len(CRSs_to_test)
    out_perim = [None] * len(CRSs_to_test)
    idx_CRS = 0
    CRS = CRSs_to_test[idx_CRS]
    for idx_CRS, CRS in enumerate(CRSs_to_test):
        if CRS is None:
            continue
        pol_m = pol_deg.to_crs(CRS)
        out_area[idx_CRS] = pol_m.area.iloc[0]/area_factor
        out_perim[idx_CRS] = pol_m.length.iloc[0]/len_factor
    print("AREA_KM_DS =", pol_deg.AREA_KM, "   AREAS CALCULADAS=", out_area)
    print("PERIM_KM_DS=", pol_deg.PERIM_KM, "   PERIM CALCULADOS=", out_perim)
    return

# lat=centr_deg_lat; lon=centr_deg_lon


def get_epsg_from_latlon(lat, lon):
    utm_band = str((math.floor((lon + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
    else:
        epsg_code = '327' + utm_band
    return epsg_code
