import rasterio
import geopandas as gpd
import csv
import os

import importlib
import FunDiv as FunDiv
import FunFeatShape as FunShape
import FunFeatStat as FunStat
import FunFeatTexture as FunText
import FunPlot as FunPlot
from Config import *

importlib.reload(FunDiv)
importlib.reload(FunShape)
importlib.reload(FunStat)
importlib.reload(FunText)
importlib.reload(FunPlot)

# pd.set_option("display.max_columns", 1000)

vetores = gpd.read_file(fname_vetores)
# vetores.crs
# Nomes das imagens TIF do diretório

idx_img = 0
fname_img16 = fnames_img16[idx_img]
# Loop pelas imagens TIF encontradas no diretório
for idx_img in range(len(fnames_img16)):
    fname_img16 = fnames_img16[idx_img]
    fname_img16 = '/home/josegarcia/ProjData/Oil-Datasets/Cantarell/Calibrada/07 S1A_IW_GRDH_1SDV_20200727T001546_NR_Orb_Cal_TC.tif'
    # Basename (nome do arquivo somente, sem o path)
    bname16 = os.path.basename(fname_img16)
    # Pega o ID da imagem do nome, para poder pegar seus vetores
    id_img = int(bname16.split(" ")[0])
    flds = FunDiv.get_S1A_fname_fields(dir_raw_data, bname16)

    # 1st prefix for each row of the CSV (related to the image)
    dict_tiff = {'ID_IMG': id_img,
                 'IMG_NAME': bname16,
                 'YEAR': flds['date_on'][:4],
                 'MONTH': flds['date_on'][4:6],
                 'DAY': flds['date_on'][6:]}

    # Abre o raster original (o GeoTIFF de 16 bits)
    # tiff = rioxarray.open_rasterio(fname_img, masked=True, chunks=True)
    tiff16 = rasterio.open(fname_img16, chunks=True)
    # rasterplot.show(tiff16)

    # Abre o raster 8b (o GeoTIFF de 8 bits)
    bname8 = f"{bname16[:36]}8b.tif"
    fname_img8 = f"{dir_tif8}/{bname8}"
    tiff8 = rasterio.open(fname_img8, chunks=True)
    # rasterplot.show(tiff8)

    # Captura todas as geometrias (polígonos) referentes à imagem
    gdf_img_mpolys = vetores[vetores['Id'] == id_img]
    gdf_img_mpolys.reset_index(inplace=True)
    gdf_img_mpolys = gdf_img_mpolys.set_crs(tiff16.crs, allow_override=True)

    # Converte todos os mutipolígonos da imagem em polígonos individuais
    # Os polígonos permanecem polígonos
    # index_parts=True cria um índice composto (entrada original + partes explodidas)
    gdf_img_polys = gdf_img_mpolys.explode(index_parts=True)

    # Percorre a lista dos polígonos individuais da imagem
    idx_pol = 3
    for idx_pol in range(len(gdf_img_polys)):
        gdf_pol = gdf_img_polys.iloc[[idx_pol]]
        # gdf_pol.plot(); plt.show()

        # If 1st pol in the multipol
        if gdf_pol.index[0][1] == 0:
            # 2nd prefix for each row of the CSV (wrt to the main multipol and child pol)
            dict_head_vect = {'IDX_VECT': int(gdf_pol.index[0][0]),  # Multipol idx
                              # Multipolygon id (custom)
                              'ID_VECT': gdf_pol.ID_POLY.iloc[0]}

            # Suffix for each row of the CSV
            dict_tail_vect = {"AREA_KM_DS": float(gdf_pol.AREA_KM.iloc[0]),
                              "PERIM_KM_DS": float(gdf_pol.PERIM_KM.iloc[0]),
                              "CLASSE": gdf_pol.CLASSE.iloc[0],
                              "SUBCLASSE": gdf_pol.SUBCLASSE.iloc[0]}

        # Pol idx in multipol
        dict_head_pol = {'IDX_POLYG': int(gdf_pol.index[0][1])}

        print(dict_tiff["IMG_NAME"], dict_head_vect['IDX_VECT'],
              dict_head_pol['IDX_POLYG'], flush=True, end='')

        print(": P", flush=True, end='')
        dict_shape_feat = FunShape.get_shape_features(gdf_pol.geometry)
        print(".", flush=True, end='')

        print("S", flush=True, end='')
        dict_stat_feat = FunStat.get_stat_features(
            gdf_img_polys, gdf_pol.geometry, tiff16)
        print(".", flush=True, end='')

        print("T", flush=True, end='')
        dict_text_feat = FunText.get_texture_features(
            gdf_pol.geometry, tiff8)
        print(".", flush=True, end='')

        # Adding 0.05 to prevent division by 0 error
        dict_in_x_out = {"SLICK_DARKNESS": (
            dict_stat_feat["IN_MEAN"] + 0.05) / (dict_stat_feat["OUT_MEAN"] + 0.05)}

        # Contatenates dicts
        pol_info = dict_tiff | dict_head_vect | dict_head_pol | dict_shape_feat | \
            dict_stat_feat | dict_text_feat | dict_in_x_out | dict_tail_vect

        mode = "w" if idx_img == 0 and gdf_pol.index[0] == (0, 0) else "a"
        # Open output CSV for writing (DS-OIL)
        with open('stats.csv', mode) as f1:
            writer = csv.writer(f1, delimiter=";", lineterminator='\n')

            # Writes the CSV header if is the 1st polygon
            if mode == "w":
                _ = writer.writerow(pol_info.keys())

            # Appends the data line in the CSV
            _ = writer.writerow(pol_info.values())

        # Plot the polygon (individually)
        print("P1", flush=True, end='')
        FunPlot.plot_pol(gdf_pol, pol_info)
        print(".", flush=True, end='')

        # Plot the valued polygon's bbox
        print("P2", flush=True, end='')
        FunPlot.plot_bbox_png(gdf_pol, tiff8, pol_info)
        print(".", flush=True, end='')
        print()

    # # Copy the metadata from the source and update the new clipped layer
    # out_meta = tiff16.meta.copy()
    # out_meta.update({
    #     "driver": "GTiff",
    #     "height": out_raster.shape[1],  # height starts with shape[1]
    #     "width": out_raster.shape[2],  # width starts with shape[2]
    #     "transform": out_transform})
    # # Write output to file
    # out_file = 'clip.tif'
    # with rasterio.open(out_file, 'w', **out_meta) as dest:
    #     dest.write(out_raster)

    # clip = rasterio.open("clip.tif", masked=False, chunks=True)
    # clip.shape
    # rasterplot.show(clip, cmap="gray")

    # from rasterio.plot import show
    # fig, ax = plt.subplots()
    # areabbox.plot(ax=ax, facecolor='none', edgecolor='black', lw=1.0)
    # rasterplot.show(tiff16, ax=ax)
    # plt.show()

    # fig, ax = plt.subplots(figsize=(12, 12))
    # show(out_raster, ax=ax)

    #     # Plotting
    #     pol_deg.geometry.plot(facecolor='w', edgecolor='red')
    #     # pol_deg.plot()
    #     # plt.savefig(f"{dir_img}{os.sep}{bname.replace(".tif", "")}_Vet{str(idx_vet).rjust(3, '0')}_Pol{str(idx_pol).rjust(3, '0')}.png");
    #     # plt.close();
    #     plt.show()

    #     print(pol_deg.bounds)
    #     f, ax = plt.subplots()
    #     # rasterplot.show(tiff,  # use tiff.read(1) with your data
    #     #                 # minx, maxx, miny, maxy
    #     #                 extent=[pol_deg.bounds.minx, pol_deg.bounds.maxx,
    #     #                         pol_deg.bounds.miny, pol_deg.bounds.maxy],
    #     #                 ax=ax,
    #     #                 )

    #     data, _ = rasterio.mask.mask(tiff16, shapes=seg, crop=True)
    #     rasterplot.show(data, ax=ax)
    #     # rasterplot.show(pol_deg, ax=ax)
    #     # plot shapefiles
    #     # pol_deg.geometry.plot(ax=ax, facecolor='w', edgecolor='red')
    #     # plt.savefig('test.jpg')
    #     plt.show()

    #     with rasterio.open(fname_img) as src:
    # data, _ = rasterio.mask.mask(src, shapes=bbox, crop=True)

    # fig = plt.figure(figsize=[12, 8])
    # # Plot the raster data using matplotlib
    # ax = fig.add_axes([0, 0, 1, 1])
    # raster_image = ax.imshow(
    #     data[0, :, :], cmap="terrain", vmax=5000, vmin=-4000)
    # fig.colorbar(raster_image, ax=ax, label="Elevation (in m) ",
    #              orientation='vertical', extend='both', shrink=0.5)
    # plt.show()

    # # ================================================================
    # # Open the raster data using rasterio
    # data, _ = rasterio.mask.mask(
    #     tiff16, shapes=pol_deg.geometry, crop=True)

    # fig = plt.figure(figsize=[12, 8])
    # # Plot the raster data using matplotlib
    # ax = fig.add_axes([0, 0, 1, 1])
    # raster_image = ax.imshow(
    #     data[0, :, :], cmap="terrain", vmax=5000, vmin=-3000)
    # fig.colorbar(raster_image, ax=ax, label="Elevation (in m) ",
    #              orientation='vertical', extend='both', shrink=0.5)
    # plt.show()

    # bbox = MultiPolygon(
    #     [Polygon([[xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin]])])
    # tiff2 = rasterio.open(fname_img, masked=False, chunks=True)
    # tiff2.shape
    # out_img, out_transform = rioMask(tiff2, shapes=bbox, crop=False)
    # ax = rasterplot.show(out_img, cmap="gray", shapes=bbox)
    # # pol_deg.boundary.plot(ax=ax) # ax=ax)
    # plt.show()

    # # Check your coordinate ordering,
    # # I wasn't sure which was X and which was Y
    # ulx, uly = 5773695.0, 601200.0
    # width, height = 700, 500

    # with rasterio.open('/path/to/someraster') as ds:
    #     # Note - index takes coordinates in X,Y order
    #     #        and returns row, col (Y,X order)
    # row, col = ds.index(ulx, uly)
    # window = Window(row, col, width, height)
    # data = ds.read(window)
