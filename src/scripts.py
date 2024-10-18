import rasterio
from rasterio.mask import mask as rioMask
import os
import geopandas as gpd
import numpy as np
from typing import List
import fiona

def getPixelResolution(tiffFilePath):
    with rasterio.open(tiffFilePath) as src:
        pixelResolution = src.res[0]
        return pixelResolution * 111110  # TODO: Check the conversion of degrees in latitude and longitude to meters multiplication

def getMaskAndReturnPolygons(tiffFilePath, shpFilePath, idxImg):
    allVectors = gpd.read_file(shpFilePath)
    ImgVectors = allVectors[allVectors['IMG_NUMBER'] == idxImg]
    tiff = rasterio.open(tiffFilePath, masked=True, chunks=True)

    rasters = []
    for idxVector in range(len(ImgVectors)):
        vectorDf = ImgVectors.iloc[[idxVector]]
        imageOut, transformOut = rioMask(tiff, vectorDf["geometry"], crop=True)

        metaOut = tiff.meta
        metaOut.update({"driver": "GTiff",
                         "height": imageOut.shape[1],
                         "width": imageOut.shape[2],
                         "transform": transformOut})

        tiffOutput = f"{os.path.splitext(tiffFilePath)[0]}_polygon{idxVector}.tif"

        with rasterio.open(tiffOutput, "w", **metaOut) as dest:
            dest.write(imageOut)

        rasters.append(imageOut)

    return rasters

def getMaskAndReturnPolygonsTest(tiffFilePath, shpFilePath, idxImg):
    allVectors = gpd.read_file(shpFilePath)
    ImgVectors = allVectors[allVectors['IMG_NUMBER'] == idxImg]
    tiff = rasterio.open(tiffFilePath, masked=True, chunks=True)

    rasters = []
    for idxVector in range(len(ImgVectors)):
        vectorDf = ImgVectors.iloc[[idxVector]]
        imageOut, transformOut = rioMask(tiff, vectorDf["geometry"], crop=True)

        metaOut = tiff.meta
        metaOut.update({"driver": "GTiff",
                        "height": imageOut.shape[1],
                        "width": imageOut.shape[2],
                        "transform": transformOut})

        tiffOutput = f"{os.path.splitext(tiffFilePath)[0]}_polygon{idxVector}.tif"

        with rasterio.open(tiffOutput, "w", **metaOut) as dest:
            dest.write(imageOut)

        rasters.append((imageOut, transformOut))

    return rasters
