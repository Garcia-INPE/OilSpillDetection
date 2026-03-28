#!/home/jrmgarcia/miniconda3/envs/OIL_SPILL/bin/python

import os
import importlib
import rasterio
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

os.chdir("/home/jrmgarcia/ProjDocs/OilSpill/src")

import Config as Cfg  # nopep8

importlib.reload(Cfg)

DIR_OUT = os.path.join("dataout", "02.3-QA_POLYGONS_BY_IMAGE")
os.makedirs(DIR_OUT, exist_ok=True)


def build_id_to_tiff_path(tiff_paths):
    mapping = {}
    for path in tiff_paths:
        bname = os.path.basename(path)
        id_tiff = int(bname.split(" ")[0])
        mapping[id_tiff] = path
    return mapping


def plot_image_polygons(tiff_path, gdf_img, out_png):
    with rasterio.open(tiff_path) as src:
        bounds = src.bounds

        fig, ax = plt.subplots(figsize=(14, 10), dpi=140)
        ax.set_aspect("equal", adjustable="box")

        # Draw full image footprint
        img_rect = Rectangle(
            (bounds.left, bounds.bottom),
            bounds.right - bounds.left,
            bounds.top - bounds.bottom,
            linewidth=2.5,
            edgecolor="#4A90E2",
            facecolor="none",
            linestyle="-",
            label="Image footprint",
        )
        ax.add_patch(img_rect)

        if len(gdf_img) > 0:
            gdf_plot = gdf_img.copy()
            if gdf_plot.crs != src.crs:
                gdf_plot = gdf_plot.to_crs(src.crs)

            # Draw all polygons with high-visibility styling
            gdf_plot.plot(
                ax=ax,
                facecolor="none",
                edgecolor="#FFD400",
                linewidth=2.0,
                alpha=1.0,
                zorder=3,
            )

            minx, miny, maxx, maxy = gdf_plot.total_bounds
            bbox_rect = Rectangle(
                (minx, miny),
                maxx - minx,
                maxy - miny,
                linewidth=2.3,
                edgecolor="#FF2D55",
                facecolor="none",
                linestyle="--",
                label="BBox of all polygons",
            )
            ax.add_patch(bbox_rect)

            # Compute bbox size in raster pixels and annotate beside the bbox.
            row_ul, col_ul = src.index(minx, maxy)
            row_lr, col_lr = src.index(maxx, miny)
            bbox_width_px = abs(col_lr - col_ul) + 1
            bbox_height_px = abs(row_lr - row_ul) + 1
            x_offset = 0.004 * (bounds.right - bounds.left)
            y_offset = 0.004 * (bounds.top - bounds.bottom)
            ax.text(
                maxx + x_offset,
                maxy - y_offset,
                f"BBox: {bbox_width_px} x {bbox_height_px} px",
                color="#FF2D55",
                fontsize=10,
                fontweight="bold",
                ha="left",
                va="top",
                zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#FF2D55", lw=1.0, alpha=0.9),
            )

            # Number each polygon by centroid
            for idx_local, (_, row) in enumerate(gdf_plot.iterrows(), start=1):
                c = row.geometry.centroid
                ax.text(
                    c.x,
                    c.y,
                    str(idx_local),
                    color="white",
                    fontsize=10,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    zorder=5,
                    bbox=dict(boxstyle="round,pad=0.20", fc="black", ec="white", lw=0.6, alpha=0.8),
                )

            # Add index-to-polygon reference text block on the side
            ref_lines = []
            for idx_local, (_, row) in enumerate(gdf_plot.iterrows(), start=1):
                ref_lines.append(f"{idx_local:02d}: {row['ID_POLY']} | {row['CLASSE']}")
            ref_text = "\n".join(ref_lines)
            ax.text(
                1.01,
                1.0,
                ref_text,
                transform=ax.transAxes,
                fontsize=8,
                va="top",
                ha="left",
                family="monospace",
                bbox=dict(boxstyle="round,pad=0.35", fc="#F6F8FA", ec="#D0D7DE", lw=0.8),
            )

    # Styling and labels
    ax.set_title(
        f"TIFF {int(os.path.basename(tiff_path).split(' ')[0]):02d} | Polygons: {len(gdf_img)}",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.6)

    # Keep full image footprint in view
    ax.set_xlim(bounds.left, bounds.right)
    ax.set_ylim(bounds.bottom, bounds.top)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="lower left", fontsize=9)

        plt.tight_layout()
        plt.savefig(out_png)
        plt.close(fig)


def main():
    id_to_tiff = build_id_to_tiff_path(Cfg.FNAMES_TIF)

    print(f"[INFO] Creating QA plots in: {DIR_OUT}")
    print(f"[INFO] TIFF files found: {len(Cfg.FNAMES_TIF)}")

    generated = 0
    for id_tiff, tiff_path in sorted(id_to_tiff.items()):
        gdf_img = Cfg.VECTORS[Cfg.VECTORS["Id"] == id_tiff].copy()
        out_png = os.path.join(DIR_OUT, f"IMG_{id_tiff:02d}_POLYGONS_QA.png")
        plot_image_polygons(tiff_path, gdf_img, out_png)
        generated += 1

    print(f"[INFO] Done. Generated {generated} plots.")


if __name__ == "__main__":
    main()
