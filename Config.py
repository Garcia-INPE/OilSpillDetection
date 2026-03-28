"""
Configuration file for the project. It defines input and output paths, as well as other constants used throughout the code.
"""
from os.path import expanduser
import os
import glob
import geopandas as gpd

HOME = expanduser("~")
BITS = 16  # 8 or 16

# Define input paths and files
DIR_IN = os.path.join(HOME, "ProjData", "Oil_Spill", "Cantarell_Beisl")
DIR_IN_TIF = os.path.join(DIR_IN, "Calibrada" if BITS == 16 else "8bits")
FNAME_IN_VECTORS = os.path.join(DIR_IN, "Vetores", "Oil_slick", "OilSlicks_Cantarell_GEOG_18052022_01.shp")  # nopep8
VECTORS = gpd.read_file(FNAME_IN_VECTORS)
# Get all TIFF file names
FNAMES_TIF = sorted(
    glob.glob(
        os.path.join(DIR_IN_TIF, "*_NR_Orb_Cal_TC.tif")
        if BITS == 16
        else os.path.join(DIR_IN_TIF, "*_8b.tif")
    )
)

# Define output paths and build output structure
DIR_OUT = os.path.join("dataout", "02.0-DS_by_geom_bbox")
DIR_OUT_CSV = os.path.join(DIR_OUT, "CSV")

DIR_OUT_IMG = os.path.join(DIR_OUT, "IMAGES", "IMG-RGB")
DIR_OUT_LABELS_1D = os.path.join(DIR_OUT, "IMAGES", "LABELS-1D")
DIR_OUT_LABELS_RGB = os.path.join(DIR_OUT, "IMAGES", "LABELS-RGB")

DIR_OUT_TIF = os.path.join(DIR_OUT, "RASTER", "IMG-TIFF", "8-BIT" if BITS == 8 else "16-BIT")
DIR_OUT_JSON = os.path.join(DIR_OUT, "RASTER", "LABELS-VECTOR", "GEOJSON")
DIR_OUT_KML = os.path.join(DIR_OUT, "RASTER", "LABELS-VECTOR", "KML")
DIR_OUT_SHP = os.path.join(DIR_OUT, "RASTER", "LABELS-VECTOR", "SHAPEFILE")

# Create output directories if they don't exist
os.makedirs(DIR_OUT_CSV, exist_ok=True)
os.makedirs(DIR_OUT_IMG, exist_ok=True)
os.makedirs(DIR_OUT_LABELS_1D, exist_ok=True)
os.makedirs(DIR_OUT_LABELS_RGB, exist_ok=True)
os.makedirs(DIR_OUT_TIF, exist_ok=True)
os.makedirs(DIR_OUT_JSON, exist_ok=True)
os.makedirs(DIR_OUT_KML, exist_ok=True)
os.makedirs(DIR_OUT_SHP, exist_ok=True)
