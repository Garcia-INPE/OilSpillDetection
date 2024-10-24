from shapely import geometry
from rasterio import plot as rasterplot
# from rasterio.plot import show
from matplotlib import pyplot as plt
import os
import warnings
import geopandas as gpd
import importlib
import numpy as np
import FunDiv
importlib.reload(FunDiv)


def get_feat_stat(gdf_img_polys, gdf_poly, dict_ret, tiff16, matched, plot=False):
    # dict_ret = dict_feat_stat

    # -----------------------------------------------------------------------
    # Parte 1) Estatísticas do conteúdo de dentro do polígono
    # LISTA DE CARACTERÍSTICAS ESTATÍSTICAS A SEREM GERADAS
    # "FG_STD", "FG_VAR", "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF",
    # -----------------------------------------------------------------------
    # Retorna MaskedArray e máscara do polígono
    masked_bg, _ = FunDiv.get_masked_array_from_vector(
        tiff16, gdf_poly.geometry, filled=False, crop=True, invert=False)
    # plt.imshow(masked[0, :, :]); plt.show()

    # Checa se todos os valores da máscara são True
    # Que significa que todos estão escondidos (mascarado)
    if not masked_bg.mask.all():
        dict_ret["FG_STD"] = np.ma.std(masked_bg)
        dict_ret["FG_VAR"] = np.ma.var(masked_bg)
        dict_ret["FG_MIN"] = np.ma.min(masked_bg)
        dict_ret["FG_MAX"] = np.ma.max(masked_bg)
        dict_ret["FG_MEAN"] = np.ma.mean(masked_bg)
        dict_ret["FG_MEDIAN"] = np.ma.median(masked_bg)
        dict_ret["FG_VAR_COEF"] = dict_ret["FG_STD"] / dict_ret["FG_MEAN"]

    # -----------------------------------------------------------------------
    # Parte 2) Estatísticas do conteúdo de fora do polígono
    # (demais segmentos contidos no bb também fora)
    # LISTA DE CARACTERÍSTICAS ESTATÍSTICAS A SEREM GERADAS
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
        'geometry'], crs=tiff16.crs)
    # Captura todos os polígonos que intersectam com o bbox do polígono sendo analisado
    warnings.filterwarnings('error')
    inters_check = "OK"
    try:
        gdf_all_inside_bbox = gpd.overlay(
            gdf_img_polys, gdf_bbox, how='intersection', keep_geom_type=True, make_valid=True)
    except:
        inters_check = "FAIL"
        warnings.resetwarnings()
        gdf_all_inside_bbox = gpd.overlay(
            gdf_img_polys, gdf_bbox, how='intersection', keep_geom_type=True, make_valid=True)
        if matched:
            return ()
    warnings.resetwarnings()

    # list([gdf_img_polys.iloc[[x, ]].intersects(gdf_bbox, align=False)
    #     for x in range(len(gdf_img_polys))])

    """
    gdf_img_polys.iloc[[1, ]].total_bounds
    gdf_bbox.total_bounds
    gdf_bbox.plot(); gdf_pol_deg.plot(); plt.show()
    """

    # Retorna MaskedArray e máscara da parte de fora dos polígonos dentro do bbox
    masked_fg, _ = FunDiv.get_masked_array_from_vector(
        tiff16, gdf_all_inside_bbox.geometry, filled=False, crop=True, invert=False)
    # Plota feições originais e fundo mascarado
    # plt.imshow(masked[0, :, :], cmap='Greys'); plt.show()
    masked_ori = masked_fg.copy()  # Inverte manualmente as máscaras
    masked_fg.mask = ~masked_fg.mask  # Inverte manualmente as máscaras
    # masked.shape
    # gdf_bbox.total_bounds
    # gdf_all_inside_bbox.total_bounds
    """
    # Plota feições mascaradas e fundo original
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
    ax1.imshow(masked.data[0, :, :], cmap='Greys'); plt.set_title("Data")
    ax2.imshow(masked_ori[0, :, :], cmap='Greys'); plt.set_title("Ori Mask")
    ax3.imshow(masked.mask[0, :, :], cmap='Greys'); plt.set_title("Inv Mask")
    plt.show()
    """
    if plot:
        # Plota o polígono e bbox para todos
        fig, axs = plt.subplots(2, 3, figsize=(20, 10))  # nopep8
        # rasterplot.show(tiff16, ax=ax, title='TIFF')
        gdf_img_polys.plot(ax=axs[0, 0], color="blue")
        gdf_bbox.plot(ax=axs[0, 0], facecolor="none", edgecolor='red')
        exp_deg = 0.0015
        axs[0, 0].set_xlim(
            gdf_all_inside_bbox.total_bounds[0]-exp_deg, gdf_all_inside_bbox.total_bounds[2]+exp_deg)
        axs[0, 0].set_ylim(
            gdf_all_inside_bbox.total_bounds[1]-exp_deg, gdf_all_inside_bbox.total_bounds[3]+exp_deg)
        axs[0, 0].set_title("Bbox exp")

        i01 = gdf_all_inside_bbox.plot(ax=axs[0, 1], color="green")
        axs[0, 1].set_title("Bbox")
        # fig.colorbar(i01, ax=axs[0, 1])

        i02 = axs[0, 2].imshow(masked_ori[0, :, :])
        axs[0, 2].set_title(f"Masked Data Ori {masked_ori[0, :, :].shape}")
        fig.colorbar(i02, ax=axs[0, 2])

        i10 = axs[1, 0].imshow(masked_fg[0, :, :])
        axs[1, 0].set_title(f"Masked Data Inv {masked_fg[0, :, :].shape}")
        fig.colorbar(i10, ax=axs[1, 0])

        i11 = axs[1, 1].imshow(masked_ori.mask[0, :, :], cmap='Greys')
        axs[1, 1].set_title(f"Ori Mask {masked_ori.mask[0, :, :].shape}")
        fig.colorbar(i11, ax=axs[1, 1])

        i12 = axs[1, 2].imshow(masked_fg.mask[0, :, :], cmap='Greys')
        axs[1, 2].set_title(f"Inv Mask {masked_fg.mask[0, :, :].shape}")
        fig.colorbar(i12, ax=axs[1, 2])
        # plt.show()
        fname_img = f"./img{os.sep}{inters_check}_IDX_IMG-{gdf_poly.Id.iloc[0]}_IDX_MPOLY-{
            gdf_poly.index[0][0]}_IDX_POLY-{gdf_poly.index[0][1]}.png"
        plt.savefig(fname_img)
        plt.close()
        # print(fname_img)

    if not masked_fg.mask.all():
        dict_ret["BG_STD"] = np.ma.std(masked_fg)
        dict_ret["BG_VAR"] = np.ma.var(masked_fg)
        dict_ret["BG_MIN"] = np.ma.min(masked_fg)
        dict_ret["BG_MAX"] = np.ma.max(masked_fg)
        dict_ret["BG_MEAN"] = np.ma.mean(masked_fg)
        dict_ret["BG_MEDIAN"] = np.ma.median(masked_fg)
        dict_ret["BG_VAR_COEF"] = dict_ret["BG_STD"] / dict_ret["BG_MEAN"]
        dict_ret["FG_DARK_INTENS"] = dict_ret["BG_MEAN"] - dict_ret["FG_MEAN"]

        # "FG_BG_THRES", "FG_BG_MAX_CONTRAST", "POWER_MEAN_RATIO", "FG_BG_MEAN_CONTRAST_RATIO",
        # Gradientes e Bordas (Considerar somente o contorno????)
        # "BORDER_GRAD_STD", "BORDER_GRAD_MEAN", "BORDER_GRAD_MAX"]

    return (dict_ret)
