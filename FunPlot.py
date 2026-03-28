import os
import Functions as Fun
import importlib
from matplotlib import pyplot as plt

importlib.reload(Fun)


dir_img = "./datain"
# dir_img="./dataout/img"


def gen_jpg_for_ds(tiff_file, masked_bg, masked_fg, gdf_poly, gdf_all_inside_bbox, dir_img="./"):
    """
    # GDFs to plot:
    # . masked_bg: values inside polygon are the original (from TIFF), outside are masked (0, False)
    # . masked_fg: values outside polygon are the original (from TIFF), inside are masked (0, False)
    # . gdf_poly: (multi) polygon being analyzed
    # . gdf_all_inside_bbox: all (multi) polygons inside the bbox of the polygon being analyzed
    # -----------------------------------------------------
    # 3 JPG images to plot about the polygon being analyzed: Greyscale, RGB Values, 1D Masked FG
    # 2 TIFF images to build about the polygon being analyzed: Original and 1D Masked FG
    # . Apply the same JPG 1D mask values?
    """

    # -----------------------------------------------------
    fig, axs = plt.subplots(1, 3, figsize=(20, 10))  # nopep8
    # rasterplot.show(tiff16, ax=ax, title='TIFF')
    # gdf_img_polys.plot(ax=axs[0, 0], color="blue")
    # gdf_bbox.plot(ax=axs[0, 0], facecolor="none", edgecolor='red')
    # exp_deg = 0.0015
    # axs[0].set_xlim(
    #    gdf_all_inside_bbox.total_bounds[0]-exp_deg, gdf_all_inside_bbox.total_bounds[2]+exp_deg)
    # axs[1].set_ylim(
    #    gdf_all_inside_bbox.total_bounds[1]-exp_deg, gdf_all_inside_bbox.total_bounds[3]+exp_deg)
    # axs[2].set_title("Bbox exp")

    # 1) Gray scaled
    # i0 = gdf_all_inside_bbox.plot(ax=axs[0])  # , color="grayscale")
    # i0 = gdf_poly.plot(ax=axs[0])  # , color="grayscale")

    # Plot the masked_fg array in greyscale
    i01 = axs[0].imshow(tiff_file.read(1))
    axs[0].set_title("Original")
    # fig.colorbar(i01, ax=axs[0, 1])

    col_rgb = (0, 0, 0)
    col_1d = 0

    # CLASSE            RGB Name    RGB Values      1D Labels
    # -------------------------------------------------------
    # SEA SURFACE       Black       (0, 0, 0)           0
    # OIL SPILL         Cyan        (0, 255, 255)       1
    # SEEPAGE SLICK     Red         (255, 0, 0)         2
    # LAND (*)          Green       (0, 153, 0)         4

    if gdf_poly["CLASSE"].iloc[0] == "OIL SPILL":
        col_rgb = (0, 255, 255)  # Cyan
        col_1d = 1
    elif gdf_poly["CLASSE"].iloc[0] == "SEEPAGE SLICK":
        col_rgb = (255, 0, 0)    # Red
        col_1d = 2

    i1 = axs[1].imshow(masked_bg[0, :, :])
    axs[1].set_title("RGB Masked")
    # fig.colorbar(i1, ax=axs[1])

    i2 = axs[2].imshow(masked_fg[0, :, :])
    axs[2].set_title("1D Masked")
    # fig.colorbar(i2, ax=axs[2])

    # i11 = axs[1, 1].imshow(masked_ori.mask[0, :, :], cmap='Greys')
    # axs[1, 1].set_title(f"Ori Mask {masked_ori.mask[0, :, :].shape}")
    # fig.colorbar(i11, ax=axs[1, 1])

    # i12 = axs[1, 2].imshow(masked_fg.mask[0, :, :], cmap='Greys')
    # axs[1, 2].set_title(f"Inv Mask {masked_fg.mask[0, :, :].shape}")
    # fig.colorbar(i12, ax=axs[1, 2])
    # plt.show()
    fname_img = f".{os.sep}datain{os.sep}IMG_{gdf_poly.Id.iloc[0]}_MPOLY_{gdf_poly.index[0]}.jpg"
    plt.savefig(fname_img)
    plt.close()
    # print(fname_img)
