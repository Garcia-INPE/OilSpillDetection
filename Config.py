import os

DIR_DS = f"{os.sep}home{os.sep}jrmgarcia{os.sep}ProjDocs{os.sep}OilSpill{os.sep}src{os.sep}dataout{os.sep}DS"
DIR_CSV = f"{DIR_DS}{os.sep}CSV"
DIR_1D_IMG = f"{DIR_DS}{os.sep}IMG{os.sep}1D-IMG"
DIR_1D_MASK = f"{DIR_DS}{os.sep}IMG{os.sep}1D-MASK"
DIR_RGB_IMG = f"{DIR_DS}{os.sep}IMG{os.sep}RGB-IMG"
DIR_RGB_MASK = f"{DIR_DS}{os.sep}IMG{os.sep}RGB-MASK"
DIR_TIFF8 = f"{DIR_DS}{os.sep}IMG{os.sep}RASTER-TIFF{os.sep}8-BIT"
DIR_TIFF16 = f"{DIR_DS}{os.sep}IMG{os.sep}RASTER-TIFF{os.sep}16-BIT"
DIR_GEOJSON = f"{DIR_DS}{os.sep}IMG{os.sep}RASTER-VECTOR{os.sep}GEOJSON"
DIR_KML = f"{DIR_DS}{os.sep}IMG{os.sep}RASTER-VECTOR{os.sep}KML"
DIR_SHP = f"{DIR_DS}{os.sep}IMG{os.sep}RASTER-VECTOR{os.sep}SHAPEFILE"

# Buil d the directories if they do not exist
os.makedirs(DIR_DS, exist_ok=True)
os.makedirs(DIR_CSV, exist_ok=True)
os.makedirs(DIR_1D_IMG, exist_ok=True)
os.makedirs(DIR_1D_MASK, exist_ok=True)
os.makedirs(DIR_RGB_IMG, exist_ok=True)
os.makedirs(DIR_RGB_MASK, exist_ok=True)
os.makedirs(DIR_TIFF8, exist_ok=True)
os.makedirs(DIR_TIFF16, exist_ok=True)
os.makedirs(DIR_GEOJSON, exist_ok=True)
os.makedirs(DIR_KML, exist_ok=True)
os.makedirs(DIR_SHP, exist_ok=True)
