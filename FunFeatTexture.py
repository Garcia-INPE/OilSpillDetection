from skimage.feature import graycomatrix, graycoprops
from matplotlib import pyplot as plt
import numpy as np
import importlib

import FunDiv
from Config import *

importlib.reload(FunDiv)

# INTUITION: These functions need a uint8 matrix, tiff8, is int16, bbox is likely
# to have number 256 as nodata, so we must consider only data from inside
# the bbox, which should not have nodata values


def get_texture_features(pol_deg, tiff8):
    # pol_deg = gdf_pol.geometry

    nodata = 256.   # 256.0 | np.nan
    masked_array, _ = FunDiv.get_masked_array_from_vector(
        tiff8, pol_deg.geometry, filled=True, crop=True, invert=False, nodata=nodata)

    # Squeezing each row by removing elements = <nodata>
    # Submit each row to calculation and get the mean
    ma2d = masked_array[0].copy().ravel()  # 2d to 1d
    ma2d = ma2d[ma2d != nodata]            # Removing nodata 8bits
    ma2d = ma2d[ma2d >= 0]                 # Removing negative data
    # "256" values are out, now convert to int8
    ma2d = ma2d.astype(np.int8)
    # plt.hist(ma2d, edgecolor='black', bins=20); plt.show()
    ma2d = np.expand_dims(ma2d, axis=0)    # graycoprops() needs 2d
    # ma2d.shape

    dict_text = {"TEXT_CONTR_GLCM": None, "TEXT_HOMOG_GLCM": None, "TEXT_ENTRO_GLCM": None,
                 "TEXT_CORREL_GLCM": None, "TEXT_DISSIM_GLCM": None, "TEXT_VAR_GLCM": None,
                 "TEXT_ENERGY_GLCM": None, "TEXT_MEAN_GLCM": None, }

    try:
        glcm = None
        max_value = np.max(ma2d)         # int16
        levels = max_value + 1
        glcm = graycomatrix(ma2d, distances=[1], angles=[
                            0], levels=levels, symmetric=True, normed=True)
        glcm_normalized = glcm / np.sum(glcm)

        try:
            dict_text["TEXT_CONTR_GLCM"] = float(
                graycoprops(glcm, 'contrast').ravel()[0])
        except:
            pass
        try:
            dict_text["TEXT_HOMOG_GLCM"] = float(
                graycoprops(glcm, 'homogeneity').ravel()[0])
        except:
            pass
        try:
            dict_text["TEXT_ENTRO_GLCM"] = float(
                -np.sum(glcm_normalized * np.log2(glcm_normalized + 1e-10)))
        except:
            pass
        try:
            dict_text["TEXT_CORREL_GLCM"] = float(
                graycoprops(glcm, 'correlation').ravel()[0])
        except:
            pass
        try:
            dict_text["TEXT_DISSIM_GLCM"] = float(
                graycoprops(glcm, 'dissimilarity').ravel()[0])
        except:
            pass
        try:
            dict_text["TEXT_VAR_GLCM"] = float(np.var(glcm).ravel()[0])
        except:
            pass
        try:
            dict_text["TEXT_ENERGY_GLCM"] = float(
                graycoprops(glcm, 'energy').ravel()[0])
        except:
            pass
        try:
            dict_text["TEXT_MEAN_GLCM"] = float(np.mean(glcm).ravel()[0])
        except:
            pass
    except:
        print("\nma2d\n", ma2d, flush=True)
        print("\nglcm\n", glcm, flush=True)
        pass

    return (dict_text)
