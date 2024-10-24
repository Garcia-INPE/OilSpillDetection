import os
import pandas as pd
import geopandas as gpd
from os.path import expanduser

# A cross-platform way to get the home directory
home = expanduser("~")

dir_ds = f"{home}/ProjData/Oil-Datasets/Cantarell"
fname_vetores = f"{
    dir_ds}/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp"

# Vetores originais
vetores = gpd.read_file(fname_vetores)

# DS gerado
DS = pd.read_csv('stats.csv', sep=";")
DS_SUM = DS.groupby('ID_VECT')[['SHP_AREA_KM2', 'SHP_PERIM_KM']].sum()


idx_vect = 0
id_vect = vetores.iloc[idx_vect]["ID_POLY"]

len(DS[DS['ID_VECT'] == id_vect]["AREA_KM_DS"]), "polygons"

print('\n',
      float(vetores.iloc[idx_vect]["AREA_KM"]), '\n',
      float(DS[DS['ID_VECT'] == id_vect]["AREA_KM_DS"].iloc[0]), '\n',
      float(DS[DS['ID_VECT'] == id_vect]["SHP_AREA_KM2"].sum()), '\n',
      float(DS_SUM.loc[id_vect].SHP_AREA_KM2))
