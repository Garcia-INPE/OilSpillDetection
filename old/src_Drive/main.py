import geopandas as gpd
from geometricShape import GeometricShape
from getTexture import Texture
from scripts import getPixelResolution, getMaskAndReturnPolygons, getMaskAndReturnPolygonsTest, getMaskAndReturnPolygonsTest2
import csv
import resource

def main():
    tiffFilePath = 'data/21_S1B_IW_GRDH_1SDV_20200802T001516_NR_Orb_Cal_TC.tif'
    shpFilePath = 'data/OilSlicks_Cantarell_GEOG_18052022_01.shp'

    # satelliteImage = rasterio.open(tiffFile)
    # print(satelliteImage.meta)
    # imageData = satelliteImage.read(1).astype(np.uint8)
    shpFile = gpd.read_file(shpFilePath)
    # bounds = shpFile.bounds

    # # Visualizar os limites
    # print(bounds)

    # print("Dados do arquivo TIFF:")
    # print(satelliteImage)
    # print("\nDados do arquivo shapefile:")
    # print(shapeFileData)

    pixelResolution = getPixelResolution(tiffFilePath)
    # print(pixelResolution)
    mask = getMaskAndReturnPolygons(tiffFilePath, shpFilePath, 19)
    # testMask = getMaskAndReturnPolygonsTest(tiffFilePath, shpFilePath, 19)
    # test2Mask  = getMaskAndReturnPolygonsTest2(tiffFilePath, shpFilePath, 1)
    # testonlymasks = [mask for mask, _ in testMaskRaster] # remover as transformações das tuplas
    # teste = geometryToBinaryImage(mask, pixelResolution)
    
    geometricShapeStatistics = GeometricShape(shpFile['geometry'])
    pixelAreas, squareMetersAreas, squareKilometersAreas = geometricShapeStatistics.calculateArea(pixelResolution)
    pixelPerimeters, metersPerimeters, kilometersPerimeters = geometricShapeStatistics.calculatePerimeter(pixelResolution)
    complexitiesMeasure = geometricShapeStatistics.calculateComplexityMeasure(squareMetersAreas, metersPerimeters)
    spreadingsMeasure = geometricShapeStatistics.calculateSpreading(shpFilePath)
    shapesFactorsMeasure = geometricShapeStatistics.calculateShapeFactor(pixelAreas, pixelPerimeters)
    circularitiesMeasure = geometricShapeStatistics.calculateCircularity(pixelAreas, pixelPerimeters)
    perimetersToAreasRatiosMeasure = geometricShapeStatistics.calculatePerimeterToAreaRatio(pixelAreas, pixelPerimeters)
    # huMomentsInvariants = []
    
    # for i, mask in enumerate(test2Mask):
    #     huMomentInvariant = geometricShapeStatistics.calculateHuInvariantMoments(mask)
    #     huMomentsInvariants.append(huMomentInvariant)
    #     print(f"Momentos invariantes de Hu da máscara {i+1}:\n{huMomentInvariant}\n")
    
    # for idx, testMaskRaster in enumerate(testMask):
    #     masks = [mask for mask in testMaskRaster] # extrair somente as máscaras
    #     huMomentInvariant = geometricShapeStatistics.calculateHuInvariantMoments(masks)
    #     huMomentsInvariants.append(huMomentInvariant)
    #     print(f"Geometria {idx+1}:")
    #     print(f"   Medida de Hu Moment Invariant: {huMomentInvariant}")
    
    # for idx, testMaskRaster in enumerate(testMask):
    #     if len(testMaskRaster) == 2:
    #         mask, _ = testMaskRaster
    #     else:
    #         mask = testMaskRaster[0]

    #     huMomentInvariant = geometricShapeStatistics.calculateHuInvariantMoments([mask])
    #     huMomentsInvariants.append(huMomentInvariant)
    #     print(f"Geometria {idx+1}:")
    #     print(f"   Medida de Hu Moment Invariant: {huMomentInvariant}")
    # for idx, testMaskRaster in enumerate(testMask):
    #     huMomentInvariant = geometricShapeStatistics.calculateHuInvariantMoments(testonlymasks)
    #     huMomentsInvariants.append(huMomentInvariant)
    #     print(f"Geometria {idx+1}:")
    #     print(f"   Medida de Hu Moment Invariant: {huMomentsInvariants}")
    
    contrasts = []
    homogeneities =[]
    entropies = []
    correlations = []
    dissimilarities = []
    variances = []
    energies = []
    means = []
    for idx, maskRaster in enumerate(mask):
        texture = Texture(maskRaster)
        contrast = texture.calculateContrastGlcm()
        contrasts.append(contrast)
        homogeneity = texture.calculateHomogeneityGlcm()
        homogeneities.append(homogeneity)
        entropy = texture.calculateEntropyGlcm()
        entropies.append(entropy)
        correlation = texture.calculateCorrelationGlcm()
        correlations.append(correlation)
        dissimilarity = texture.calculateDissimilarityGlcm()
        dissimilarities.append(dissimilarity)
        variance = texture.calculateVarianceGlcm()
        variances.append(variance)
        energy = texture.calculateEnergyGlcm()
        energies.append(energy)
        mean = texture.calculateMeanGlcm()
        means.append(mean)
       
        # print(f"GLCM contrast para polígono {idx+1}:\n{contrasts}")
        # print(f"GLCM Homogeneity para polígono {idx+1}:\n{homogeneities}")
        # print(f"GLCM Entropy para polígono {idx+1}:\n{entropies}")
        # print(f"GLCM Correlation para polígono {idx+1}:\n{correlations}")
        # print(f"GLCM Dissimilarity para polígono {idx+1}:\n{dissimilarities}")
        # print(f"GLCM Variance para polígono {idx+1}:\n{variances}")
        # print(f"GLCM Energy para polígono {idx+1}:\n{energies}")
        # print(f"GLCM Mean para polígono {idx+1}:\n{means}")
    
    dataGeometricShape = []
    for i, (pixelArea, squareMetersArea, squareKilometersArea) in enumerate(zip(pixelAreas, squareMetersAreas, squareKilometersAreas)):
        dataGeometricShape.append([f"Polygon {i+1}", pixelArea, squareMetersArea, squareKilometersArea])
        # print(f"Geometria {i+1}:")
        # print(f"   Área em número de pixels: {pixelArea}")
        # print(f"   Área em metros quadrados: {squareMetersArea}")
        # print(f"   Área em quilômetros quadrados: {squareKilometersArea}")
        
    for i, (pixelPerimeter, meterPerimeter, kilometerPerimeter) in enumerate(zip(pixelPerimeters, metersPerimeters, kilometersPerimeters)):
        dataGeometricShape[i].extend([pixelPerimeter, meterPerimeter, kilometerPerimeter])
        # dataGeometricShape.append([f"Polygon {i+1}", pixelPerimeter, meterPerimeter, kilometerPerimeter])
    #     print(f"Geometria {i+1}:")
    #     print(f"   Perímetro em número de pixels: {pixelPerimeter}")
    #     print(f"   Perímetro em metros quadrados: {metersPerimeter}")
    #     print(f"   Perímetro em quilômetros quadrados: {kilometersPerimeter}")
    
    for i, complexityMeasure in enumerate(complexitiesMeasure):
        dataGeometricShape[i].extend([complexityMeasure])
    #     print(f"Geometria {i+1}:")
    #     print(f"   Medida de complexidade é (adimensional): {complexityMeasure}")
        
    for i, spreadingMeasure in enumerate(spreadingsMeasure):
        dataGeometricShape[i].extend([spreadingMeasure])
    #     print(f"Geometria {i+1}:")
    #     print(f"   Medida de Spreading é (adimensional): {spreadingMeasure}")
        
    for i, shapeFactorMeasure in enumerate(shapesFactorsMeasure):
        dataGeometricShape[i].extend([shapeFactorMeasure])
    #     print(f"Geometria {i+1}:")
    #     print(f"   Medida de ShapeFactor é (adimensional): {shapeFactorMeasure}")
    
    # for i, huMomentInvariant in enumerate(huMomentsInvariants):
    #     print(f"Geometria {i+1}:")
    #     print(f"   Medida de Hu Moment Invariant: {huMomentInvariant}")
        # dataGeometricShape[i].extend([huMomentIinvariant])
        

    for i, circularityMeasure in enumerate(circularitiesMeasure):
        dataGeometricShape[i].extend([circularityMeasure])
    #     print(f"Geometria {i+1}:")
    #     print(f"   Medida de Circularity é (adimensional): {circularityMeasure}")

    for i, perimeterToAreaRatioMeasure in enumerate(perimetersToAreasRatiosMeasure):
        dataGeometricShape[i].extend([perimeterToAreaRatioMeasure])
    #     print(f"Geometria {i+1}:")
    #     print(f"   Medida de Perimeter to Area Ratio é (px-1, m-1 ou km-1): {perimeterToAreaRatioMeasure}")

    with open('resultadosGeometricShape.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Polygon', 'Area (pixel*)', 'Area (m²)', 'Area (km²)', 
                        'Perimeter (pixel*)', 'Perimeter (m²)', 'Perimeter (km²)',
                        'Complexity Measure', 'Spreading', 'Shape Factor*',
                        'Circularity', 'Perimeter to Area Ratio'])  
        writer.writerows(dataGeometricShape)
        
if __name__ == "__main__":
    main()