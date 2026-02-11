import warnings
import importlib
import numpy as np
import geopandas as gpd
import Functions as Fun
import FunPlot as FPlot
from scipy.stats import ks_2samp, mannwhitneyu
from shapely import geometry

importlib.reload(Fun)
importlib.reload(FPlot)


def get_feat_stat(gdf_img_mpolys, gdf_poly, dict_ret, tiff_file, plot=False, dir_img="./"):
    """
    Calculates statistical features for a given polygon within a raster image.

    Args:
        gdf_img_polys (GeoDataFrame): GeoDataFrame containing all polygons in the image.
        gdf_poly (GeoDataFrame): GeoDataFrame containing the polygon of interest.
        dict_ret (dict): Dictionary to store the calculated statistical features.
        tiff_file (rasterio DatasetReader): Rasterio dataset representing the image.

    Returns:
        dict: Updated dictionary with calculated statistical features. 

    """

    # -----------------------------------------------------------------------
    # Part 1) Statistical features of the content inside the polygon
    # LIST OF STATISTICAL FEATURES TO BE GENERATED
    # "FG_STD", "FG_VAR", "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF",
    # -----------------------------------------------------------------------
    # Returns MaskedArray of the polygon of interest
    masked_bg, _ = Fun.get_masked_array_from_vector(
        tiff_file, gdf_poly.geometry, filled=False, crop=True, invert=False)
    # plt.imshow(masked[0, :, :]); plt.show()

    # Check if all mask values are True
    # Which means that all values are hidden (masked)
    if not masked_bg.mask.all():
        dict_ret["FG_STD"] = np.ma.std(masked_bg)
        dict_ret["FG_VAR"] = np.ma.var(masked_bg)
        dict_ret["FG_MIN"] = np.ma.min(masked_bg)
        dict_ret["FG_MAX"] = np.ma.max(masked_bg)
        dict_ret["FG_MEAN"] = np.ma.mean(masked_bg)
        dict_ret["FG_MEDIAN"] = np.ma.median(masked_bg)
        dict_ret["FG_VAR_COEF"] = dict_ret["FG_STD"] / dict_ret["FG_MEAN"]

    # -----------------------------------------------------------------------
    # Part 2) Statistical features of the content outside the polygon of interest
    # (other segments contained in the bbox also outside)
    # LIST OF STATISTICAL FEATURES TO BE GENERATED
    # "BG_STD", "BG_VAR", "BG_MIN", "BG_MAX", "BG_MEAN", "BG_MEDIAN", "BG_VAR_COEF", "FG_DARK_INTENS"
    # -----------------------------------------------------------------------

    # Bbox do raster
    # bbox_raster = geometry.box(tiff16.bounds[0], tiff16.bounds[1],
    #                           tiff16.bounds[2], tiff16.bounds[3])
    # Cria uma geometria cujos limites são o bbox do polígono sendo analisado
    exp_deg = 0.0
    bbox_pol = geometry.box(gdf_poly.total_bounds[0]-exp_deg, gdf_poly.total_bounds[1]-exp_deg,
                            gdf_poly.total_bounds[2]+exp_deg, gdf_poly.total_bounds[3]+exp_deg)
    # import shapely
    # bbox_raster.intersects(bbox_pol), bbox_pol.intersects(bbox_raster)
    # res = shapely.union(bbox_pol, bbox_raster)
    # fig, ax = plt.subplots()
    # plt.plot(*bbox_raster.exterior.xy, color="red");
    # plt.plot(*bbox_pol.exterior.xy, color="blue"); plt.show()

    # Cria um GeoPandas DataFrame com o bbox, georreferenciado pelo mesmo CRS
    gdf_bbox = gpd.GeoDataFrame(gpd.GeoSeries(bbox_pol), columns=[
        'geometry'], crs=tiff_file.crs)
    # Captura todos os polígonos que intersectam com o bbox do polígono sendo analisado
    warnings.filterwarnings('error')
    try:
        gdf_all_inside_bbox = gpd.overlay(
            gdf_img_mpolys, gdf_bbox, how='intersection', keep_geom_type=True, make_valid=True)
    except Exception:
        warnings.resetwarnings()
        gdf_all_inside_bbox = gpd.overlay(
            gdf_img_mpolys, gdf_bbox, how='intersection', keep_geom_type=True, make_valid=True)
    warnings.resetwarnings()

    # list([gdf_img_polys.iloc[[x, ]].intersects(gdf_bbox, align=False)
    #     for x in range(len(gdf_img_polys))])
    # gdf_img_polys.iloc[[1, ]].total_bounds
    # gdf_bbox.total_bounds
    # gdf_bbox.plot(); gdf_pol_deg.plot(); plt.show()

    # Retorna MaskedArray e máscara da parte de fora dos polígonos dentro do bbox
    masked_fg, _ = Fun.get_masked_array_from_vector(
        tiff_file, gdf_all_inside_bbox.geometry, filled=False, crop=True, invert=False)
    # Plota feições originais e fundo mascarado
    # plt.imshow(masked[0, :, :], cmap='Greys'); plt.show()
    masked_ori = masked_fg.copy()  # Inverte manualmente as máscaras
    masked_fg.mask = ~masked_fg.mask  # Inverte manualmente as máscaras
    # masked.shape
    # gdf_bbox.total_bounds
    # gdf_all_inside_bbox.total_bounds

    # Plota feições mascaradas e fundo original
    # fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
    # ax1.imshow(masked.data[0, :, :], cmap='Greys'); plt.set_title("Data")
    # ax2.imshow(masked_ori[0, :, :], cmap='Greys'); plt.set_title("Ori Mask")
    # ax3.imshow(masked.mask[0, :, :], cmap='Greys'); plt.set_title("Inv Mask")
    # plt.show()

    if plot:
        FPlot.plot_for_DS(tiff_file, masked_bg, masked_fg,
                          gdf_poly, gdf_all_inside_bbox, dir_img=dir_img)

    if not masked_fg.mask.all():
        dict_ret["BG_STD"] = np.ma.std(masked_fg)
        dict_ret["BG_VAR"] = np.ma.var(masked_fg)
        dict_ret["BG_MIN"] = np.ma.min(masked_fg)
        dict_ret["BG_MAX"] = np.ma.max(masked_fg)
        dict_ret["BG_MEAN"] = np.ma.mean(masked_fg)
        dict_ret["BG_MEDIAN"] = np.ma.median(masked_fg)
        dict_ret["BG_VAR_COEF"] = dict_ret["BG_STD"] / dict_ret["BG_MEAN"]
        dict_ret["FG_DARK_INTENS"] = dict_ret["BG_MEAN"] - dict_ret["FG_MEAN"]

        data_fg = masked_fg.compressed()
        data_bg = masked_bg.compressed()

        # Kolmogorov-Smirnov (K-S) test between fg and bg
        statistic, pvalue = ks_2samp(data_fg, data_bg)
        dict_ret["FG_BG_KS_STAT"] = statistic
        dict_ret["FG_BG_KS_RES"] = "DIFF" if pvalue < 0.05 else "CAN_BE_SAME"

        # Mann-Whitney U test between fg and bg
        statistic, pvalue = mannwhitneyu(data_fg, data_bg)
        dict_ret["FG_BG_MW_STAT"] = statistic
        dict_ret["FG_BG_MW_RES"] = "DIFF" if pvalue < 0.05 else "CAN_BE_SAME"

        # Power Mean Ratio
        # Calculate the ratio for different values of p
        p_value_1 = 1  # Arithmetic mean
        p_value_2 = 2  # Quadratic mean
        # p_value_neg1 = -1  # Harmonic mean
        # p_value_geo = 1e-9  # Geometric mean (approximate)

        dict_ret["FG_BG_RAT_ARI"] = power_mean_ratio(
            data_fg, data_bg, p_value_1)
        dict_ret["FG_BG_RAT_QUA"] = power_mean_ratio(
            data_fg, data_bg, p_value_2)

        # dict_ret["FG_BG_RAT_HAR"] = power_mean_ratio(data_fg, data_bg, p_value_neg1)
        # dict_ret["FG_BG_RAT_GEO"] = power_mean_ratio(data_fg, data_bg, p_value_geo)

        # "THRES", "FG_BG_MAX_CONTRAST", "FG_BG_MEAN_CONTRAST_RATIO",
        # Gradients and Borders (Contour stats)
        # "BORDER_GRAD_STD", "BORDER_GRAD_MEAN", "BORDER_GRAD_MAX"]

    return (dict_ret)


# dist1=data_fg; dist2=data_bg; p=1e-9
def power_mean_ratio(dist1, dist2, p):
    """
    Calculates the ratio of the power means of two distributions.

    Args:
        dist1 (array-like): The first distribution (e.g., a list or numpy array).
        dist2 (array-like): The second distribution (e.g., a list or numpy array).
        p (int/float): The exponent (order) of the power mean.
                       Use a value close to 0 (e.g., 1e-9) for the geometric mean ratio.

    Returns:
        float: The ratio of the power means of the two distributions.
    """
    # Convert to numpy arrays for efficient calculation
    arr1 = np.array(dist1)
    arr2 = np.array(dist2)

    # Stop the program if an exception occurs
    try:
        # Handle the case where p is close to 0 (geometric mean) to avoid division by zero
        if abs(p) < 1e-9:
            # Geometric mean: exp(1/n * sum(log(x_i)))
            mean1 = np.exp(np.mean(np.log(arr1)))
            mean2 = np.exp(np.mean(np.log(arr2)))
        else:
            # General power mean formula
            mean1 = np.mean(arr1**p)**(1/p)
            mean2 = np.mean(arr2**p)**(1/p)

        if mean2 == 0:
            return float('inf')  # Handle division by zero for the ratio
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

    return mean1 / mean2
