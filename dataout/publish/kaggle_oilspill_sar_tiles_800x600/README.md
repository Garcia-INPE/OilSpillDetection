# Oil Spill SAR Segmentation Tiles (800x600)

This Kaggle package contains publication-ready tile data for semantic segmentation.

## Contents
- raster_stats/
- images/
- raster/
- splits/
- checksums.sha256
- DATASET_CARD.md
- dataset-metadata.json

## Folder Guide
- `images/README.md`: input tiles, masks, class legend, and pairing rules under `images/data/`.
- `raster/README.md`: GeoTIFF support rasters and vector geospatial label files under `raster/data/`.
- `splits/README.md`: official train/val/test manifests.
- `raster_stats/README.md`: feature statistics files, key fields, and join usage under `raster_stats/data/`.

## Raster Statistics
- `raster_stats/data/features_16bit.csv`
- `raster_stats/data/features_8bit.csv`

Both statistics files are aligned to the same tile/sample scope.

## Notes
- Pixel-level ground truth is in `images/data/mask_1c/` and `images/data/mask_rgb/`.
- `mask_1c` means a single-channel class-index mask (one pixel value per class).
- `mask_rgb` means a three-channel RGB rendering of the same class-index mask.
- Shapefile bundle names under `raster/data/vectors/shapefile/` are:
  - `All_Vectors.*`
  - `Individual_Vectors.zip`
