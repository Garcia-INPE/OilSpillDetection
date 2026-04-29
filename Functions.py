import os
import math
import importlib
import zipfile
import rasterio
import utm
import numpy as np
import geopandas as gpd
from PIL import Image
from affine import Affine
from rasterio.features import rasterize
from rasterio.mask import mask
from rasterio.windows import Window
from shapely.geometry import mapping, box

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
os.chdir(SCRIPT_DIR)

import Config as Cfg     # nopep8
import FunPlot as FPlot  # nopep8
import Functions as Fun  # nopep8
importlib.reload(Cfg)
importlib.reload(FPlot)
importlib.reload(Fun)


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


def get_outer_white_crop_box(rgb_hwc):
    """Return crop box (left, top, right, bottom) removing pure-white outer frame."""
    height, width = rgb_hwc.shape[:2]
    white = np.all(rgb_hwc == 255, axis=2)

    top = 0
    while top < height and white[top, :].all():
        top += 1

    bottom = height - 1
    while bottom >= top and white[bottom, :].all():
        bottom -= 1

    left = 0
    while left < width and white[top:bottom + 1, left].all():
        left += 1

    right = width - 1
    while right >= left and white[top:bottom + 1, right].all():
        right -= 1

    if top > bottom or left > right:
        return (0, 0, width, height)

    return (left, top, right + 1, bottom + 1)


def get_content_crop_box_from_mask(mask_2d):
    """Return crop box (left, top, right, bottom) from non-zero label content."""
    ys, xs = np.where(mask_2d != 0)
    if len(xs) == 0 or len(ys) == 0:
        h, w = mask_2d.shape
        return (0, 0, w, h)

    left = int(xs.min())
    right = int(xs.max()) + 1
    top = int(ys.min())
    bottom = int(ys.max()) + 1
    return (left, top, right, bottom)


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
    # raster=tiff_file; vectors=gdf_poly.geometry; filled=False; crop=True; invert=False
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


def build_output_dirs(dir_out, bits):
    """Build a dataset output directory dictionary and ensure it exists."""
    output_dirs = {
        "DIR_OUT": dir_out,
        "DIR_OUT_CSV": os.path.join(dir_out, "CSV"),
        "DIR_OUT_IMG": os.path.join(dir_out, "IMAGES", "IMG-RGB"),
        "DIR_OUT_LABELS_1D": os.path.join(dir_out, "IMAGES", "LABELS-1D"),
        "DIR_OUT_LABELS_RGB": os.path.join(dir_out, "IMAGES", "LABELS-RGB"),
        "DIR_OUT_TIF": os.path.join(dir_out, "RASTER", "IMG-TIFF", "8-BIT" if bits == 8 else "16-BIT"),
        "DIR_OUT_JSON": os.path.join(dir_out, "RASTER", "LABELS-VECTOR", "GEOJSON"),
        "DIR_OUT_KML": os.path.join(dir_out, "RASTER", "LABELS-VECTOR", "KML"),
        "DIR_OUT_SHP": os.path.join(dir_out, "RASTER", "LABELS-VECTOR", "SHAPEFILE"),
    }

    for key, value in output_dirs.items():
        if key != "DIR_OUT":
            os.makedirs(value, exist_ok=True)

    return output_dirs


def get_target_grid_size(width_px, height_px, target_width, target_height):
    """Return the minimal fixed-tile grid that can contain a crop."""
    grid_cols = max(1, math.ceil(width_px / target_width))
    grid_rows = max(1, math.ceil(height_px / target_height))
    composite_width = grid_cols * target_width
    composite_height = grid_rows * target_height
    return grid_cols, grid_rows, composite_width, composite_height


def gen_images_for_DS_target_size(tiff_file, gdf_all_polys, target_width, target_height, output_dirs):
    """
    Generate fixed-size panels using a strict non-overlapping raster grid.

    The raster is tiled with stride exactly equal to tile size (target_width,
    target_height), so no source area is repeated across panels.
    Only tiles that contain at least one class polygon are exported.

    Returns
    -------
    dict mapping each iloc position in gdf_all_polys to a panel_info dict.
    """
    if target_width <= 0 or target_height <= 0:
        raise ValueError("target_width and target_height must be positive integers")

    if len(gdf_all_polys) == 0:
        return {}

    gdf_local = gdf_all_polys.copy()
    if gdf_local.crs != tiff_file.crs:
        gdf_local = gdf_local.to_crs(tiff_file.crs)

    id_tiff = str(int(gdf_all_polys.Id.iloc[0])).zfill(2)
    nodata_value = tiff_file.nodata if tiff_file.nodata is not None else 0

    grid_cols = math.ceil(tiff_file.width / target_width)
    grid_rows = math.ceil(tiff_file.height / target_height)

    # Precompute pixel-space bboxes for quick tile intersection checks.
    px_bboxes = []
    for i in range(len(gdf_local)):
        minx, miny, maxx, maxy = gdf_local.geometry.iloc[i].bounds
        row_ul, col_ul = tiff_file.index(minx, maxy)
        row_lr, col_lr = tiff_file.index(maxx, miny)
        r0 = max(0, min(row_ul, row_lr))
        r1 = min(tiff_file.height - 1, max(row_ul, row_lr))
        c0 = max(0, min(col_ul, col_lr))
        c1 = min(tiff_file.width - 1, max(col_ul, col_lr))
        px_bboxes.append((r0, c0, r1, c1))

    shp_sidecars = [
        ".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj",
        ".sbn", ".sbx", ".shp.xml", ".aih", ".ain", ".atx",
        ".ixs", ".mxs", ".qix", ".fix",
    ]

    panel_infos = {}
    panel_polygons = {}
    panel_overlap_count = {i: [] for i in range(len(gdf_local))}

    out_meta = tiff_file.meta.copy()
    out_meta.update({"driver": "GTiff", "height": target_height, "width": target_width})

    for panel_row in range(grid_rows):
        row_off = panel_row * target_height
        read_height = min(target_height, tiff_file.height - row_off)
        if read_height <= 0:
            continue

        for panel_col in range(grid_cols):
            col_off = panel_col * target_width
            read_width = min(target_width, tiff_file.width - col_off)
            if read_width <= 0:
                continue

            tile_r0 = row_off
            tile_r1 = row_off + read_height - 1
            tile_c0 = col_off
            tile_c1 = col_off + read_width - 1

            candidate_ilocs = []
            for i, (r0, c0, r1, c1) in enumerate(px_bboxes):
                if r1 < tile_r0 or r0 > tile_r1 or c1 < tile_c0 or c0 > tile_c1:
                    continue
                candidate_ilocs.append(i)

            if not candidate_ilocs:
                continue

            read_window = Window(col_off, row_off, read_width, read_height)
            src_data = tiff_file.read(window=read_window, boundless=False)

            tile_data = np.full(
                (src_data.shape[0], target_height, target_width),
                nodata_value,
                dtype=src_data.dtype,
            )
            tile_data[:, :read_height, :read_width] = src_data

            valid_pixels = np.zeros((target_height, target_width), dtype=bool)
            valid_pixels[:read_height, :read_width] = True

            tile_transform = tiff_file.window_transform(Window(col_off, row_off, target_width, target_height))

            # RGB rendering
            rgb_src = tile_data[:3] if tile_data.shape[0] >= 3 else np.repeat(tile_data[:1], 3, axis=0)
            rgb_tile = np.zeros((3, target_height, target_width), dtype=np.uint8)
            for ch in range(3):
                band = rgb_src[ch].astype(np.float32)
                vmask = valid_pixels.copy()
                if np.isfinite(float(nodata_value)):
                    vmask = vmask & (band != float(nodata_value))
                if np.any(vmask):
                    bmin = np.nanmin(band[vmask])
                    bmax = np.nanmax(band[vmask])
                    if np.isfinite(bmin) and np.isfinite(bmax) and bmax > bmin:
                        rgb_tile[ch] = ((band - bmin) / (bmax - bmin) * 255).astype(np.uint8)

            # Combined labels for all classes that intersect this tile.
            mask1_tile = np.zeros((target_height, target_width), dtype=np.uint8)
            effective_ilocs = []
            for iloc_i in candidate_ilocs:
                class_id = 2 if gdf_all_polys.CLASSE.iloc[iloc_i] == "SEEPAGE SLICK" else 1
                poly_mask = rasterize(
                    [(gdf_local.geometry.iloc[iloc_i], class_id)],
                    out_shape=(target_height, target_width),
                    transform=tile_transform,
                    fill=0,
                    dtype=np.uint8,
                )
                overlap = int(np.count_nonzero(poly_mask))
                if overlap == 0:
                    continue
                effective_ilocs.append(iloc_i)
                panel_overlap_count[iloc_i].append((panel_row + 1, panel_col + 1, overlap))
                mask1_tile = np.maximum(mask1_tile, poly_mask)

            if not effective_ilocs:
                continue

            panel_basename = (
                f"IMG_{id_tiff}_TILE"
                f"_R{str(panel_row + 1).zfill(3)}"
                f"C{str(panel_col + 1).zfill(3)}"
            )

            mask3_tile = np.zeros((3, target_height, target_width), dtype=np.uint8)
            mask3_tile[0] = np.where(mask1_tile == 2, 255, 0)
            mask3_tile[1] = np.where(mask1_tile == 1, 255, 0)
            mask3_tile[2] = np.where(mask1_tile == 1, 255, 0)

            Image.fromarray(np.transpose(rgb_tile, (1, 2, 0)), mode="RGB").save(
                f"{output_dirs['DIR_OUT_IMG']}{os.sep}{panel_basename}.png"
            )
            Image.fromarray(np.transpose(mask3_tile, (1, 2, 0)), mode="RGB").save(
                f"{output_dirs['DIR_OUT_LABELS_RGB']}{os.sep}{panel_basename}_RGB.png"
            )
            Image.fromarray(mask1_tile, mode="L").save(
                f"{output_dirs['DIR_OUT_LABELS_1D']}{os.sep}{panel_basename}_1D.png"
            )

            with rasterio.open(
                f"{output_dirs['DIR_OUT_TIF']}{os.sep}{panel_basename}.tiff", "w", **{**out_meta, "transform": tile_transform}
            ) as dst:
                dst.write(tile_data)

            panel_info = {
                "RESULT_BASENAME": panel_basename,
                "COMPOSITE_BASENAME": panel_basename,
                "TARGET_TILE_WIDTH": target_width,
                "TARGET_TILE_HEIGHT": target_height,
                "CLIPPED_WIDTH": read_width,
                "CLIPPED_HEIGHT": read_height,
                "GRID_COLS": 1,
                "GRID_ROWS": 1,
                "COMPOSITE_WIDTH": target_width,
                "COMPOSITE_HEIGHT": target_height,
                "PAD_LEFT": 0,
                "PAD_RIGHT": target_width - read_width,
                "PAD_TOP": 0,
                "PAD_BOTTOM": target_height - read_height,
                "IS_COMPOSITE": 0,
                "PANEL_INDEX": 1,
                "PANEL_ROW": 1,
                "PANEL_COL": 1,
                "PANEL_COUNT": 1,
                "POLYS_IN_PANEL": 0,
                "POLYS_IN_GROUP": 0,
            }
            panel_infos[(panel_row + 1, panel_col + 1)] = panel_info
            panel_polygons[(panel_row + 1, panel_col + 1)] = sorted(set(effective_ilocs))

            gdf_tile = gdf_all_polys.iloc[sorted(set(effective_ilocs))].copy()
            for col_name in list(gdf_tile.columns):
                if col_name == "geometry":
                    continue
                if "datetime" in str(gdf_tile[col_name].dtype).lower():
                    gdf_tile[col_name] = gdf_tile[col_name].dt.strftime("%Y-%m-%d")
            if "DATE" in gdf_tile.columns:
                gdf_tile["DATE"] = gdf_tile["DATE"].astype(str)

            kml_path = f"{output_dirs['DIR_OUT_KML']}{os.sep}{panel_basename}.kml"
            if os.path.exists(kml_path):
                os.remove(kml_path)
            gdf_tile.to_file(kml_path, driver="KML")

            geojson_path = f"{output_dirs['DIR_OUT_JSON']}{os.sep}{panel_basename}.geojson"
            if os.path.exists(geojson_path):
                os.remove(geojson_path)
            gdf_tile.to_file(geojson_path, driver="GeoJSON")

            shp_base = f"{output_dirs['DIR_OUT_SHP']}{os.sep}{panel_basename}"
            for ext in shp_sidecars:
                old_file = f"{shp_base}{ext}"
                if os.path.exists(old_file):
                    os.remove(old_file)
            gdf_tile.to_file(f"{shp_base}.shp", driver="ESRI Shapefile")

            with zipfile.ZipFile(f"{shp_base}.zip", "w") as zipf:
                for ext in shp_sidecars:
                    old_file = f"{shp_base}{ext}"
                    if os.path.exists(old_file):
                        zipf.write(old_file, arcname=os.path.basename(old_file))

            for ext in shp_sidecars:
                old_file = f"{shp_base}{ext}"
                if os.path.exists(old_file):
                    os.remove(old_file)

    # Assign each polygon to one panel: prefer centroid tile, fallback to max-overlap tile.
    result = {}
    for iloc_i in range(len(gdf_local)):
        cent = gdf_local.geometry.iloc[iloc_i].centroid
        cent_row, cent_col = tiff_file.index(cent.x, cent.y)
        row_idx = int(cent_row // target_height) + 1
        col_idx = int(cent_col // target_width) + 1
        key = (row_idx, col_idx)

        if key not in panel_infos and panel_overlap_count[iloc_i]:
            best = max(panel_overlap_count[iloc_i], key=lambda x: x[2])
            key = (best[0], best[1])

        if key not in panel_infos:
            continue

        info = panel_infos[key].copy()
        info["POLYS_IN_PANEL"] = len(panel_polygons.get(key, []))
        info["POLYS_IN_GROUP"] = len(panel_polygons.get(key, []))
        result[iloc_i] = info

    return result


def gen_images_for_DS(tiff_file, gdf_poly):
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

    # Reativar depois de pronto
    #FPlot.gen_raste_for_ds(tiff_file, masked_bg, masked_fg, gdf_poly, gdf_all_inside_bbox, dir_img="./")
    #FPlot.gen_jpg_for_ds(tiff_file, masked_bg, masked_fg, gdf_poly, gdf_all_inside_bbox, dir_img="./")

    # Clip the raster using the geometries
    #tiff_file = rasterio.open(tiff_fname, masked=True)
    out_img, out_transform = mask(
        dataset=tiff_file, shapes=geometries, crop=True
    )  # `crop=True` clips the raster to the extent of the bounding box

    # TODO: Land mask is missing

    root_str = f"IMG_{str(gdf_poly.Id.iloc[0]).zfill(2)}_MPOLY_{gdf_poly.ID_POLY.iloc[0]}"
    # ============================================================
    # File to save 1): TIFF IN RGB/PNG FORMAT (clipped image)
    # Save clipped image as RGB PNG (array write, no cmap/plot)
    # ============================================================
    # If raster has <3 bands, replicate first band; if >3, use first 3 bands.
    if out_img.shape[0] >= 3:
        rgb_src = out_img[:3]
    else:
        rgb_src = np.repeat(out_img[:1], 3, axis=0)

    rgb_png = np.zeros((3, out_img.shape[1], out_img.shape[2]), dtype=np.uint8)
    for idx in range(3):
        band = rgb_src[idx].astype(np.float32)
        band_min = np.nanmin(band)
        band_max = np.nanmax(band)
        if not np.isfinite(band_min) or not np.isfinite(band_max) or band_max <= band_min:
            rgb_png[idx] = 0
        else:
            rgb_png[idx] = ((band - band_min) / (band_max - band_min) * 255).astype(np.uint8)

    # =======================================================
    # Important observations about saving masks (labels):
    # =======================================================
    # Ground-truth masks must be saved by writing raw arrays directly.
    # Why not matplotlib (`imshow` + `savefig`)? Because it renders a figure canvas
    #   (DPI, interpolation, anti-aliasing, bbox/cropping), which can change pixel
    #   values and even output dimensions.
    # Why not JPG? It is lossy compression and may alter class IDs/colors.
    # Correct approach:
    # - 1D mask: single-channel uint8 PNG or TIFF with exact class IDs.
    # - RGB mask: three-channel uint8 PNG or TIFF with fixed class colors.

    # =======================================================
    # Class definitions for masks (labels)
    # -------------------------------------------------------
    # CLASSE            RGB Name    RGB Values      1D Labels
    # -------------------------------------------------------
    # SEA SURFACE       Black       (0, 0, 0)           0
    # OIL SPILL         Cyan        (0, 255, 255)       1
    # SEEPAGE SLICK     Red         (255, 0, 0)         2
    # LAND (*)          Green       (0, 153, 0)         4
    # =======================================================

    # ============================================================
    # File to save 2) 1D MASKS (LABELS) IN 1D/PNG FORMAT
    # ============================================================
    # Get masked array of tiff_file and gdf_poly geometry
    masked_1d, _ = get_masked_array_from_vector(tiff_file, gdf_poly.geometry, crop=True, filled=False, invert=True)
    masked_1d = masked_1d.mask.astype(np.uint8)

    # if CLASSE == "OIL SPILL" then masked_1d should remains 1 where the polygon is and 0 outside
    # if CLASSE == "SEEPAGE SLICK" then masked_1d should change to 2 where the polygon is and 0 outside
    if gdf_poly.CLASSE.iloc[0] == "SEEPAGE SLICK":
        masked_1d = np.where(masked_1d==1, 2, masked_1d) 
        # print("Masked FG - min:", masked_fg.min(), " max:", masked_fg.max())

    # ============================================================
    # File to save 3) RGB MASKS (LABELS) IN RGB/PNG FORMAT
    # Convert out_image, according to the class of the polygon, into two imkages, 
    #   one with the RGB value and another wit 1D labels
    # ============================================================
    masked_3d = np.zeros((3, masked_1d.shape[1], masked_1d.shape[2]), dtype=np.uint8)
                         
    # if CLASSE == "OIL SPILL"     then masked_1d should be (0, 255, 255)[cyan], where the polygon is and (0,0,0)[black] outside
    # if CLASSE == "SEEPAGE SLICK" then masked_1d should be (255, 0, 0)[red]   , where the polygon is and (0,0,0)[black] outside
    if gdf_poly["CLASSE"].iloc[0] == "OIL SPILL":
        masked_3d[0] = np.where(masked_1d != 0, 0, 0)  # Cyan for oil spill
        masked_3d[1] = np.where(masked_1d != 0, 255, 0)
        masked_3d[2] = np.where(masked_1d != 0, 255, 0)
    elif gdf_poly["CLASSE"].iloc[0] == "SEEPAGE SLICK":
        masked_3d[0] = np.where(masked_1d != 0, 255, 0)  # Red for seepage slick
        masked_3d[1] = np.where(masked_1d != 0, 0, 0)
        masked_3d[2] = np.where(masked_1d != 0, 0, 0)

    # Keep all outputs aligned and crop to actual polygon content.
    rgb_hwc = np.transpose(rgb_png, (1, 2, 0))
    mask1_hwc = masked_1d[0]
    mask3_hwc = np.transpose(masked_3d, (1, 2, 0))

    # Primary crop: use the mask content bbox, which removes any constant outer frame
    # regardless of whether it appears white, gray, or another value.
    left, top, right, bottom = get_content_crop_box_from_mask(mask1_hwc)

    # Fallback for empty masks: retain existing white-border trimming behavior.
    if (left, top, right, bottom) == (0, 0, mask1_hwc.shape[1], mask1_hwc.shape[0]) and not np.any(mask1_hwc != 0):
        left, top, right, bottom = get_outer_white_crop_box(rgb_hwc)

    rgb_hwc = rgb_hwc[top:bottom, left:right]
    mask1_hwc = mask1_hwc[top:bottom, left:right]
    mask3_hwc = mask3_hwc[top:bottom, left:right]

    fname_img_png = f"{Cfg.DIR_OUT_IMG}{os.sep}{root_str}.png"
    Image.fromarray(rgb_hwc, mode="RGB").save(fname_img_png)

    fname_mask_rgb_png = f"{Cfg.DIR_OUT_LABELS_RGB}{os.sep}{root_str}_RGB.png"
    Image.fromarray(mask3_hwc, mode="RGB").save(fname_mask_rgb_png)

    fname_mask_1d_png = f"{Cfg.DIR_OUT_LABELS_1D}{os.sep}{root_str}_1D.png"
    Image.fromarray(mask1_hwc, mode="L").save(fname_mask_1d_png)

    # plot masked_3d to check if it is correct
    # plt.imshow(masked_3d.transpose(1, 2, 0))
    # plt.title("Masked RGB")
    # plt.show()
    # print("Masked FG - min:", masked_3d.min(), " max:", masked_3d.max())

    # ============================================================
    # File to save 4) Raster/TIFF and vetorial MASKS (LABELS) IN 3 FORMATS: GeoJSON, KML, SHP
    # ============================================================

    # -------------------------------------------------------------------
    # 4.1) Save clipped raster as GeoTIFF (with georeferencing)
    # -------------------------------------------------------------------
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
    fname_tiff = f"{Cfg.DIR_OUT_TIF}{os.sep}{root_str}.tiff"
    with rasterio.open(fname_tiff, "w", **out_meta) as dst:
        dst.write(out_img)

    # -------------------------------------------------------------------
    # 4.2) Save clipped vector as GeoJSON, KML, and Shapefile (with georeferencing)
    # -------------------------------------------------------------------
    # Convert gdf (GeoPandas) to KML
    kml_path = f'{Cfg.DIR_OUT_KML}{os.sep}{root_str}.kml'
    # delete file if it exists
    if os.path.exists(kml_path):
        os.remove(kml_path)
    gdf_poly.to_file(kml_path, driver='KML')

    # Convert gdf (GeoPandas) to GeoJSON
    geojson_path = f'{Cfg.DIR_OUT_JSON}{os.sep}{root_str}.geojson'
    # delete file if it exists
    if os.path.exists(geojson_path):
        os.remove(geojson_path)
    gdf_poly.to_file(geojson_path, driver='GeoJSON')

    # Convert gdf (GeoPandas) to Shapefile
    gdf_shp = gdf_poly.copy()
    for col in gdf_shp.columns:
        if col == 'geometry':
            continue
        if 'datetime' in str(gdf_shp[col].dtype).lower():
            gdf_shp[col] = gdf_shp[col].dt.strftime('%Y-%m-%d')

    if 'DATE' in gdf_shp.columns:
        gdf_shp['DATE'] = gdf_shp['DATE'].astype(str)

    shp_base = f'{Cfg.DIR_OUT_SHP}{os.sep}{root_str}'
    shp_sidecars = [
        '.shp', '.shx', '.dbf', '.prj', '.cpg', '.qpj',
        '.sbn', '.sbx', '.shp.xml', '.aih', '.ain', '.atx',
        '.ixs', '.mxs', '.qix', '.fix'
    ]
    for ext in shp_sidecars:
        old_file = f'{shp_base}{ext}'
        if os.path.exists(old_file):
            os.remove(old_file)
    # Save as shapefile but compact them in a single zip file
    gdf_shp.to_file(f'{shp_base}.shp', driver='ESRI Shapefile')

    # Zip the shapefile and its sidecars and delete them after zipping
    with zipfile.ZipFile(f'{shp_base}.zip', 'w') as zipf:
        for ext in shp_sidecars:
            old_file = f'{shp_base}{ext}'
            if os.path.exists(old_file):
                zipf.write(old_file, arcname=os.path.basename(old_file))

    # Delete the individual shapefile and sidecar files
    for ext in shp_sidecars:
        old_file = f'{shp_base}{ext}'
        if os.path.exists(old_file):
            os.remove(old_file)

    return

def save_gdf_as_shapefile(output_dir_shp=None):
    """
    Saves a GeoDataFrame as a Shapefile, ensuring that all datetime columns are converted to string format.
    After saving, it creates a zip file containing the shapefile and its associated files, and
    """
    VETORES_TO_SAVE = Cfg.VECTORS[['Id', 'ID_POLY',
                               'SATELITE', 'CLASSE', 'geometry']].copy()

    datetime_cols = VETORES_TO_SAVE.select_dtypes(
        include=["datetime64[ns]", "datetime64[ns, UTC]"]
    ).columns
    for col in datetime_cols:
        VETORES_TO_SAVE[col] = VETORES_TO_SAVE[col].dt.strftime("%Y-%m-%d")

    if "DATE" in VETORES_TO_SAVE.columns:
        VETORES_TO_SAVE["DATE"] = VETORES_TO_SAVE["DATE"].astype(str) 

    dir_out_shp = output_dir_shp if output_dir_shp is not None else Cfg.DIR_OUT_SHP

    fname_shp = f"{dir_out_shp}{os.sep}All_Vectors.shp"
    if os.path.exists(fname_shp):
        os.remove(fname_shp)
    VETORES_TO_SAVE.to_file(fname_shp, driver='ESRI Shapefile')

    # After zipping all make a final zip file with the .zip extension
    # and delete the zip files with the base name
    final_zip_path = f'{dir_out_shp}{os.sep}Individual_Vectors.zip'
    with zipfile.ZipFile(final_zip_path, 'w') as final_zip:
        for file in os.listdir(dir_out_shp):
            if file.endswith('.zip') and file != 'Individual_Vectors.zip':
                final_zip.write(os.path.join(dir_out_shp, file), arcname=file)
                os.remove(os.path.join(dir_out_shp, file))
    

    
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
