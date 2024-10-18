import geopandas as gpd
import numpy as np
import cv2
from shapely.geometry import Polygon, MultiPolygon
from PIL import Image, ImageDraw
from math import copysign, log10
from skimage.measure import moments_central, moments_hu
from shapely.affinity import affine_transform
import rasterio.features

class GeometricShape:
    def __init__(self, geometries):
        self.geometries = geometries.to_crs(epsg=32623) 

    def calculateArea(self, pixelResolution):
        pixelAreas = []
        squareMetersAreas = []
        squareKilometersAreas = []
        for geom in self.geometries:
            pixelAreasCount = geom.area / (pixelResolution ** 2)
            pixelAreas.append(pixelAreasCount)
            squareMetersAreasCount = geom.area
            squareMetersAreas.append(squareMetersAreasCount)
            squareKilometersAreasCount = geom.area / (1000000.)
            squareKilometersAreas.append(squareKilometersAreasCount)
        
        return pixelAreas, squareMetersAreas, squareKilometersAreas

    def calculatePerimeter(self, pixelResolution):
        pixelPerimeters = []
        metersPerimeters = []
        kilometersPerimeters = []
        for geom in self.geometries:
            pixelPerimetersCount = geom.length / (pixelResolution)
            pixelPerimeters.append(pixelPerimetersCount)
            metersPerimetersCount = geom.length
            metersPerimeters.append(metersPerimetersCount)
            kilometersPerimetersCount = geom.length / (1000000.)
            kilometersPerimeters.append(kilometersPerimetersCount)
        return pixelPerimeters, metersPerimeters, kilometersPerimeters

    def calculateComplexityMeasure(self, areas, perimeters):
        complexities = []
        for i in range(len(self.geometries)):
            area = areas[i]
            perimeter = perimeters[i]
            complexity = (perimeter ** 2) / area
            complexities.append(complexity)
        return complexities

    def calculateSpreading(self, shpFilePath):
        shpFile = gpd.read_file(shpFilePath)
        bounds = shpFile.bounds
        spreadings = []
        for minx, miny, maxx, maxy in zip(bounds['minx'], bounds['miny'], bounds['maxx'], bounds['maxy']):
            length = maxx - minx
            width = maxy - miny
            spreading = width / length
            spreadings.append(spreading)
        return spreadings
    
    def calculateShapeFactor(self, areas, perimeters):
        shapesFactors = []
        for i in range(len(self.geometries)):
            area = areas[i]
            perimeter = perimeters[i]
            shapeFactor = perimeter / (4 * np.sqrt(area)) # verificar
            shapesFactors.append(shapeFactor)
        return shapesFactors

    def calculateCircularity(self, areas, perimeters):
        circularities = []
        for i in range(len(self.geometries)):
            area = areas[i]
            perimeter = perimeters[i]
            circularity = (perimeter ** 2) / (4 * np.pi * area) 
            circularities.append(circularity)
        return circularities
    
    def calculatePerimeterToAreaRatio(self, areas, perimeters):
        perimetersToAreasRatios = []
        for i in range(len(self.geometries)):
            area = areas[i]
            perimeter = perimeters[i]
            perimeterToAreaRatio = perimeter / area 
            perimetersToAreasRatios.append(perimeterToAreaRatio)
        return perimetersToAreasRatios