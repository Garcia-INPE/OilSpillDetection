from os.path import expanduser
import os
import csv
import glob
import importlib
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.plot import show
import Functions as Fun
import FunGetFeat_Geom as Geom
import FunGetFeat_Stat as Stat
importlib.reload(Fun)
importlib.reload(Geom)
importlib.reload(Stat)

# from rasterio import plot as rasterplot
# A cross-platform way to get the home directory
home = expanduser("~")

# Habilita checagem das áreas e perimetros calculados por este script e o que está registrado no DS
check_stop = False
check_idx_img = 6
check_idx_mpoly = 0
check_idx_poly = 3

dir_img = "./img"
fname_csv = "Oil_Stats.csv"
os.makedirs(dir_img, exist_ok=True)
dir_data = f"{home}/ProjData/Oil-Datasets/Cantarell"
dir_tif = f"{dir_data}/Calibrada/"
fname_vetores = f"{dir_data}/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp"  # nopep8
vetores = gpd.read_file(fname_vetores)
# Nomes das imagens TIF do diretório
# fnames_img = sorted(glob.glob(f"{dir_tif}*_8b.tif"))           # 8 Bits
fnames_img = sorted(glob.glob(f"{dir_tif}*_NR_Orb_Cal_TC.tif"))  # Calibrada

# LISTA DE CARACTERÍSTICAS A SEREM GERADAS (GEOMÉTRICAS, ESTATISTICAS, TEXTURAIS, ...)
# NO CSV DE GERADO
# AREA_KM_DS e PERIM_KM_DS são preenchidas do shapefile, para comparações com o nosso
keys_head = ["IMG_FNAME", "IDX_MPOLY", "ID_MPOLY", "IDX_POLY"]
keys_feat_geom = ["CENTR_KM_LAT", "CENTR_KM_LON", "AREA_KM2", "PERIM_KM", "COMPLEX_MEAS", "SPREAD", "SHP_FACT",
                  "HU_MOM1", "HU_MOM2", "HU_MOM3", "HU_MOM4", "HU_MOM5", "HU_MOM6", "HU_MOM7", "CIRCULARITY", "PERI_AREA_RATIO"]
keys_feat_stat = ["FG_STD", "FG_VAR", "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF",
                  "BG_STD", "BG_VAR", "BG_MIN", "BG_MAX", "BG_MEAN", "BG_MEDIAN", "BG_VAR_COEF",
                  "FG_DARK_INTENS", "THRES", "FG_BG_MAX_CONTRAST", "POWER_MEAN_RATIO", "FG_BG_MEAN_CONTRAST_RATIO",
                  "BORDER_GRAD_STD", "BORDER_GRAD_MEAN", "BORDER_GRAD_MAX"]
keys_tail = ["AREA_KM_DS", "PERIM_KM_DS",
             "SATELITE", "BEAM_MODE", "CLASSE", "SUBCLASSE"]

dict_head = {k: v for (k, v) in zip(keys_head, [None]*len(keys_head))}  # nopep8
dict_feat_geom = {k: v for (k, v) in zip(keys_feat_geom, [None]*len(keys_feat_geom))}  # nopep8
dict_feat_stat = {k: v for (k, v) in zip(keys_feat_stat, [None]*len(keys_feat_stat))}  # nopep8
dict_tail = {k: v for (k, v) in zip(keys_tail, [None]*len(keys_tail))}  # nopep8
dict = {**dict_head, **dict_feat_geom, **dict_feat_stat, **dict_tail}  # nopep8  # Une os Dicts

with open(fname_csv, 'w') as f1:
    writer = csv.writer(f1, delimiter=";", lineterminator='\n')
    _ = writer.writerow(keys_head + keys_feat_geom +
                        keys_feat_stat + keys_tail)

    idx_img = 6
    fname_img = fnames_img[idx_img]
    # Loop pelas imagens TIF encontradas no diretório
    poly_count = 1
    for idx_img in range(len(fnames_img)):
        # Nome do arquivo COM path
        fname_img = fnames_img[idx_img]
        # Nome do arquivo SEM path
        bname = os.path.basename(fname_img)
        # ID da imagem, no nome do arq.
        id_img = int(bname.split(" ")[0])

        # tiff = rioxarray.open_rasterio(fname_img, masked=True, chunks=True)
        # Abre o raster (o TIFF)
        # IMG_ID=21, IDX_POLY=66
        # vetores[vetores["ID_POLY"] == "SP00369GXS1"]
        tiff16 = rasterio.open(fname_img, masked=True, chunks=True)
        # show(tiff16)
        # tiff16 = rasterio.open("SP00369GXS1_66.tif", masked=True, chunks=True)
        # tiff16_data = tiff16.read(1)
        # Fun.CheckTIFF(tiff16)
        # tiff16_extent = [tiff16.bounds[0], tiff16.bounds[2],
        #                 tiff16.bounds[1], tiff16.bounds[3]]

        # Inicia preenchimento do dict Head (que vai no início do CSV)
        dict_head_pol = dict_head
        dict_head_pol["IMG_FNAME"] = bname

        # Captura todos os polígonos referentes à imagem
        # Vetores registrados na imagem sendo analisada
        gdf_img_mpolys = vetores[vetores['Id'] == id_img]
        gdf_img_mpolys.reset_index(inplace=True)
        # gdf_img_mpolys.crs == tiff16.crs

        # Cria uma mascara para todos os polígonos da imagem
        # masked_fg, transf_fg = Fun.get_masked_array_from_vector(
        #   tiff16, gdf_img_mpolys.geometry, filled=False, crop=False, invert=True)
        # masked_fg.shape, tiff16.shape
        # plt.imshow(masked_fg[0, :, :]); plt.show()

        # Plota uma imagem com todos os polígonos da imagem e uma imagem para cada polígono da imagem
        # gdf_img_mpols.plot(); plt.show()

        # Converte todos os mutipolígonos da imagem em polígonos individuais
        # Os polígonos permanecem polígonos
        # index_parts=True cria um índice composto (entrada original + partes explodidas)
        gdf_img_polys = gdf_img_mpolys.explode(index_parts=True)
        # 'MultiPolygon' in gdf_img_mpolys.geometry.geom_type.values
        # 'MultiPolygon' in gdf_img_polys.geometry.geom_type.values
        # Percorre a lista dos polígonos individuais da imagem
        lev0_cur = -1
        idx_poly = 3

        for idx_poly in range(len(gdf_img_polys)):
            gdf_poly = gdf_img_polys.iloc[[idx_poly]]
            # Finaliza preenchimento do dict Head (que vai no início do CSV)
            dict_head_pol["IDX_POLY"] = gdf_poly.index[0][1]

            if gdf_poly.index[0][0] != lev0_cur:
                lev0_cur = gdf_poly.index[0][0]
                lev0_qtd = np.sum(
                    gdf_img_polys.index.get_level_values(0) == lev0_cur)
                # Continua preenchimento do dict Head (que vai no início do CSV)
                dict_head_pol["IDX_MPOLY"] = lev0_cur
                dict_head_pol["ID_MPOLY"] = gdf_poly.ID_POLY.iloc[0]
                # Cria um tail que é geral para o multipolígono explodido
                # e preenche o dict Tail (que vai no final do CSV)
                dict_tail_pol = dict_tail
                dict_tail_pol["AREA_KM_DS"] = gdf_poly.AREA_KM.iloc[0]
                dict_tail_pol["PERIM_KM_DS"] = gdf_poly.PERIM_KM.iloc[0]
                dict_tail_pol["SATELITE"] = gdf_poly.SATELITE.iloc[0]
                dict_tail_pol["BEAM_MODE"] = gdf_poly.BEAM_MODE.iloc[0]
                dict_tail_pol["CLASSE"] = gdf_poly.CLASSE.iloc[0]
                dict_tail_pol["SUBCLASSE"] = gdf_poly.SUBCLASSE.iloc[0]

                # Cria variáveis para ir somando as areas e perímetro dos polígonos individuais
                #    para poder comparar as somas com a área e perím gravados no DS
                pols_areas = 0.0
                pols_perims = 0.0
            # FIM DO: if poly.index[0][0] != lev0_cur:
            matched = False
            if check_stop:
                print("Checkpoint #1:  IDX_IMG:", idx_img,
                      "  IDX_MPOLY:", dict_head_pol["IDX_MPOLY"],
                      "  IDX_POLY:",  dict_head_pol["IDX_POLY"], end="")
                if idx_img == check_idx_img and \
                   dict_head_pol["IDX_MPOLY"] == check_idx_mpoly and \
                   dict_head_pol["IDX_POLY"] == check_idx_poly:
                    print(" - SIM")
                    matched = True
                else:
                    print(" - NÃO")

            # Captura features geométricas ---------------------------------------------------
            dict_feat_geom_pol = Geom.get_feat_geom(gdf_poly, dict_feat_geom)

            # Captura features estatísticas --------------------------------------------------
            dict_feat_stat_pol = Stat.get_feat_stat(
                gdf_img_polys, gdf_poly, dict_feat_stat, tiff16, matched)
            if matched:
                print(dict_feat_stat_pol)
                break
            # Armazenas as áreas e perímetros individuais
            pols_areas += dict_feat_geom_pol["AREA_KM2"]
            pols_perims += dict_feat_geom_pol["PERIM_KM"]

            # with open(fname_csv, 'w') as f1:
            #    writer = csv.writer(f1, delimiter=";", lineterminator='\n')
            row = list(dict_head_pol.values()) + list(dict_feat_geom_pol.values()) + \
                list(dict_feat_stat_pol.values()) + \
                list(dict_tail_pol.values())

            print(list(dict_head_pol.values()))
            _ = writer.writerow(row)
            poly_count += 1
            # Plota os polígonos
            # gdf_pol_deg.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
            # gdf_pol_deg.plot()
            # plt.show()
            # plt.savefig(f"{dir_img}{os.sep}{bname.replace(".tif", "")}_Vet{
            #            str(idx_vet).rjust(3, '0')}_Pol{str(idx_pol).rjust(3, '0')}.png")
            # plt.close()
            # Verifica se é o último polígono do multipolígono
            if idx_poly+1 == lev0_qtd:
                print("MULTIPOLYGON AREA_KM_DS.:", dict_tail_pol["AREA_KM_DS"],
                      "   SUM OF INDIVIDUAL POLYGONS AREA.:", pols_areas)
                print("MULTIPOLYGON PERIM_KM_DS:", dict_tail_pol["PERIM_KM_DS"],
                      "   SUM OF INDIVIDUAL POLYGONS PERIM:", pols_perims, "\n")
        # FIM DO: for idx_poly in range(len(gdf_img_polys)):
        if check_stop:
            print("Checkpoint #2:  IDX_IMG:", idx_img,
                  "  IDX_MPOLY:", dict_head_pol["IDX_MPOLY"],
                  "  IDX_POLY:",  dict_head_pol["IDX_POLY"], end="")
            if idx_img == check_idx_img and \
                    dict_head_pol["IDX_MPOLY"] == check_idx_mpoly and \
                    dict_head_pol["IDX_POLY"] == check_idx_poly:
                print(" - SIM")
                break
            else:
                print(" - NÃO")

    # FIM DO: for idx_img in range(len(fnames_img)):
# FIM DO: with open(fname_csv, 'w') as f1:

print("Polígonos totais:", poly_count)

# f, ax = plt.subplots()
# rasterplot.show(tiff,  # use tiff.read(1) with your data
#     extent=tiff_extent,
#     ax=ax,
# )
# # plot shapefiles
# row.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
# #plt.savefig('test.jpg')
# plt.show()
