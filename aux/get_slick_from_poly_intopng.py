import rasterio
from rasterio import mask
import os
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon
import pandas as pd
import glob
import numpy as np

def getSlickPolyFromMultiPolygon(dirImg, dataBase, shpFilePath, tiffFilePath):
    df = pd.read_csv(dataBase)
    vectorAll = gpd.read_file(shpFilePath)
    
    if isinstance(tiffFilePath, str):
        tiffFilePaths = [tiffFilePath]

    results = []

    for tiffFilePath in tiffFilePaths:
        tiffBasename = os.path.basename(tiffFilePath)
        idxImg = int(tiffBasename.split(' ')[0]) 
        vectorImg = vectorAll[vectorAll['IMG_NUMBER'] == idxImg]

        if not vectorImg.empty:
            df_filtered = df[df['IMG_NUMBER'] == idxImg]
            if 'ID_POLY' in df_filtered.columns and not df_filtered.empty:
                for idPoly in df_filtered['ID_POLY'].unique():
                    multipolygonRow = vectorImg[vectorImg['ID_POLY'] == idPoly]
                    if not multipolygonRow.empty:
                        geometry = multipolygonRow.geometry.values[0]
                        
                        # Cria o diretório de saída
                        outputDir = os.path.join(dirImg, str(idxImg), str(idPoly))
                        os.makedirs(outputDir, exist_ok=True)

                        # Verifica se o polígono é um multipolígono
                        geometries = list(geometry.geoms) if isinstance(geometry, MultiPolygon) else [geometry]
                        numPolygons = len(geometries)

                        data = {'ID_POLY': [f"{idPoly}_{idx}" for idx in range(1, numPolygons + 1)]}
                        newGdf = gpd.GeoDataFrame(data, geometry=geometries)
                        
                        with rasterio.open(tiffFilePath, masked=True, chunks=True) as tiff:
                            for idx, row in newGdf.iterrows():
                                outImage, outTransform = mask.mask(tiff, [row['geometry']], crop=True, nodata=np.nan)
                                outMeta = tiff.meta

                                outMeta.update({
                                    "driver": "GTiff",
                                    "height": outImage.shape[1],
                                    "width": outImage.shape[2],
                                    "transform": outTransform
                                })

                                # Definir nomes de saída
                                outputTiff = os.path.join(outputDir, f"{row['ID_POLY']}.tif")
                                outputShp = os.path.join(outputDir, f"{row['ID_POLY']}.shp")
                                outputPng = os.path.join(outputDir, f"{row['ID_POLY']}.png")

                                # Salvar TIFF
                                with rasterio.open(outputTiff, "w", **outMeta) as dest:
                                    dest.write(outImage)

                                # Salvar SHP
                                row['geometry'] = row['geometry'].buffer(0)
                                rowGdf = gpd.GeoDataFrame([row])
                                rowGdf.crs = newGdf.crs
                                rowGdf.to_file(outputShp)

                                # Salvar PNG
                                plt.figure(figsize=(10, 10))
                                plt.imshow(outImage[0], cmap='gray')
                                plt.axis('off')
                                plt.savefig(outputPng, bbox_inches='tight', pad_inches=0)
                                plt.close()

                                # Resultados
                                results.append(f"Created {outputTiff}, shape: {outImage.shape}")
                                results.append(f"Created {outputShp}")
                                results.append(f"Created {outputPng}")

                        if isinstance(geometry, MultiPolygon):
                            results.append(f"ID_POLY {idPoly} is a multipolygon, divided into {numPolygons} polygons.")
                    else:
                        results.append(f"No multipolygon found for ID_POLY {idPoly} in image {idxImg}.")
            else:
                results.append(f"No ID_POLY found for image number {idxImg}.")
        else:
            results.append(f"No polygons found for image number {idxImg}.")
    
    return results

# Variáveis
dirImg = 'C:\\Users\\grazi\\Cantarell\\teste'
dataBase = 'C:\\Users\\grazi\\INPE\\Cantarell\\teste\\Base de Dados Cantarell Sentine1.csv.csv' #glob.glob(f'{dirImg}\\*.csv')[0]
shpFilePath = 'C:\\Users\\grazi\\INPE\\Cantarell\\teste\\OilSlicks_Cantarell_GEOG_18052022_01.shp'#glob.glob(f'{dirImg}\\*.shp')[0]
tiffFilePath = 'C:\\Users\\grazi\\INPE\\Cantarell\\teste\\21 S1B_IW_GRDH_1SDV_20200802T001516_NR_Orb_Cal_TC.tif'#glob.glob(f"{dirImg}*.tif")[0]

# Executar a função
getSlickPolyFromMultiPolygon(dirImg, dataBase, shpFilePath, tiffFilePath)



