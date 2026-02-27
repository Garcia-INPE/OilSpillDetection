import os
import json
import math
import importlib
import rasterio
import utm
import numpy as np
import geopandas as gpd
from rasterio.mask import mask
from shapely.geometry import mapping, box

os.chdir("/home/jrmgarcia/ProjDocs/OilSpill/src")

import Config as Cfg  # nopep8
importlib.reload(Cfg)


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
    """ Passa para 8-bit (0-255) """
    a8 = (((a-a.min()) /
           (a.max()-a.min())) * ((255-0)+0)).astype(rasterio.uint8)
    return (a8)


def get_utm_zone(latitude, longitude):
    """
    Finds the UTM zone number and letter from a given latitude and longitude.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        tuple: (zone_number, zone_letter)
    """
    # The utm.from_latlon function returns Easting, Northing, Zone Number, and Zone Letter
    easting, northing, zone_number, zone_letter = utm.from_latlon(
        latitude, longitude)

    return (f"{zone_number}{zone_letter.upper()}")


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
    # Cria o masked array ou array
    masked_array, transform = mask(
        raster, vectors, filled=filled, crop=crop, invert=invert, nodata=np.nan)
    # masked_data = raster.read(1)  # Retorna um Numpy array
    # masked_data.shape, raster.shape
    # Attributes for MakedArray
    # type(masked_array)  # Numpy MaskedArray
    # masked_array.data
    # masked_array.mask
    # masked_array.fill_value
    # masked_array.shape

    # Copy the metadata from the source and update the new clipped layer
    meta = raster.meta.copy()
    meta.update({
        "driver": "GTiff",
        "height": masked_array.shape[1],  # height starts with shape[1]
        "width": masked_array.shape[2],   # width starts with shape[2]
        "transform": transform})

    # masked_data.min(), masked_data.max()
    # np.min(masked_data), np.max(masked_data)
    # np.ma.min(masked_data), np.ma.max(masked_data)

    return (masked_array, transform)


def CheckTIFF(tiff):
    """ OPERAÇÕES NO DADO GEORREFERENCIADO DO TIFF ------------- """
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
    """
    Testa alguns EPSGs no calculo da area e perimetro. 
    O que está dando certo é o calculado a partir da UTM específico passado em CRS_to_add.

    :param pol_deg: Description
    :param CRS_to_add: Description
    :param area_factor: Description
    :param len_factor: Description
    """

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
    """ 
    Get UTM band and EPSG code from latitude and longitude.

    : param lat: Latitude in decimal degrees.
    : param lon: Longitude in decimal degrees.
    : return: Tuple (utm_band, epsg_code)
    """
    utm_band = str((math.floor((lon + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
    else:
        epsg_code = '327' + utm_band
    return utm_band, epsg_code


def clip_raster_with_gdf_v1(tiff_file, gdf_poly):
    """
    Clips a raster TIFF file with a GeoPandas DF using rasterio and shapely.
    This method provides fine-grained control and is widely used for general polygon masking.

    : param tiff_file: An opened raster TIFF file.
    : param gdf: GeoPandas DataFrame containing the bounding box for clipping.

    : return: A saved clipped TIFF file.
    """

    # Assuming your GeoDataFrame `gdf` is already loaded or defined
    # Example: create a simple GeoDataFrame with a bounding box
    minx, miny, maxx, maxy = (
        gdf_poly.total_bounds
    )
    # Get the overall bounds of the GeoDataFrame
    clip_box = box(minx, miny, maxx, maxy)

    # Convert the box to a GeoDataFrame to handle CRS operations easily
    clip_gdf = gpd.GeoDataFrame({"geometry": [clip_box]}, crs=gdf_poly.crs)

    # Ensure CRS alignment: The GeoDataFrame's CRS must match the raster's CRS.
    if clip_gdf.crs != tiff_file.crs:
        clip_gdf = clip_gdf.to_crs(tiff_file.crs)

    # Clip the raster: The rasterio.mask.mask function expects a list of geometries in GeoJSON format.
    # Get the geometries in the required format
    geometries = [mapping(geom) for geom in clip_gdf.geometry]

    # Clip the raster using the geometries
    out_img, out_transform = mask(
        dataset=tiff_file, shapes=geometries, crop=True
    )  # `crop=True` clips the raster to the extent of the bounding box

    # Update metadata and save the clipped file:
    out_meta = tiff_file.meta.copy()
    out_meta.update(
        {
            "driver": "GTiff",
            "height": out_img.shape[1],
            "width": out_img.shape[2],
            "transform": out_transform,
        }
    )

    # Check bits of tiff file
    bits = out_meta.get("dtype", None)
    # print(f"Bits of TIFF file: {bits}")

    root_str = f"IMG_{str(gdf_poly.Id.iloc[0]).zfill(2)}_MPOLY_{gdf_poly.ID_POLY.iloc[0]}"

    if bits == "uint16":
        fname_tiff = f"{Cfg.DIR_TIFF8}{os.sep}{root_str}.tiff"
    else:
        fname_tiff = f"{Cfg.DIR_TIFF16}{os.sep}{root_str}.tiff"

    with rasterio.open(fname_tiff, "w", **out_meta) as dst:
        dst.write(out_img)

    # Convert gdf (GeoPandas) to KML
    kml_path = f'{Cfg.DIR_KML}{os.sep}{root_str}.kml'
    # delete file if it exists
    if os.path.exists(kml_path):
        os.remove(kml_path)
    gdf_poly.to_file(kml_path, driver='KML')

    # Convert gdf (GeoPandas) to GeoJSON
    geojson_path = f'{Cfg.DIR_GEOJSON}{os.sep}{root_str}.geojson'
    # delete file if it exists
    if os.path.exists(geojson_path):
        os.remove(geojson_path)
    gdf_poly.to_file(geojson_path, driver='GeoJSON')

    return


# def clip_raster_with_gdf_v2(tiff_path, gdf_poly):
#     """
#     Clips a raster TIFF file with a GeoPandas DF using rioxarray, which offers a more direct
#     and concise method with the .rio.clip_box accessor.

#     :param tiff_file: An opened raster TIFF file.
#     :param gdf: GeoPandas DataFrame containing the bounding box for clipping.
#     :return: A saved clipped TIFF file.
#     """

#     # Open the raster with rioxarray
#     raster = rioxarray.open_rasterio(tiff_path)

#     # Load or define your GeoDataFrame
#     # Assuming `gdf` is your GeoDataFrame
#     # Ensure CRS alignment:
#     if raster.rio.crs != gdf_poly.crs:
#         gdf_poly = gdf_poly.to_crs(raster.rio.crs)

#     # Clip using the total bounds: The clip_box method takes the xmin, ymin, xmax, ymax coordinates as arguments.
#     # Unpack the total bounds of the GeoDataFrame
#     clipped_raster = raster.rio.clip_box(*gdf_poly.total_bounds)

#     # Save the clipped file:
#     fname_img = f".{os.sep}datain{os.sep}IMG_{gdf_poly.Id.iloc[0]}_MPOLY_{gdf_poly.index[0]}_v2.tiff"
#     clipped_raster.rio.to_raster(fname_img)
#     return
