from os.path import expanduser
from glob import glob
import os
import re
import pandas as pd
import numpy as np

# A cross-platform way to get the home directory
home = expanduser("~")
marg_exp = 0.0005

pd.set_option("display.max_columns", 1000)
np.set_printoptions(suppress=True)

dir_img = "./img"
os.makedirs(dir_img, exist_ok=True)
dir_ds = f"{home}/ProjData/Oil-Datasets/Cantarell"
dir_raw_data = dir_ds                 # Root dir where .SAFE dir is
dir_tif8 = f"{dir_ds}/8bits"          # To print
dir_tif16 = f"{dir_ds}/Calibrada"     # To extract features

fname_vetores = f"{
    dir_ds}/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp"

# Captura todas as imagens dos diretórios
fnames_img8 = sorted(glob(f"{dir_tif8}/*_8b.tif"))
fnames_img16 = sorted(glob(f"{dir_tif16}/*_NR_Orb_Cal_TC.tif"))

# Filtra somente Sentinel-1
# Lista devem ter mesmo tamanho, relação 1:1 (8bits:16bits)
fnames_img8 = [f for f in fnames_img8 if re.search(
    "[0-9]{2} S1A_IW_GRDH_1SDV_", os.path.basename(f))]
fnames_img16 = [f for f in fnames_img16 if re.search(
    "[0-9]{2} S1A_IW_GRDH_1SDV_", os.path.basename(f))]
assert len(fnames_img8) == len(fnames_img16)
