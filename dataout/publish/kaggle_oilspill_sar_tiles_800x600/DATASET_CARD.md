# Dataset Card: Oil Spill SAR Segmentation Tiles (800x600)

## Scope
Publication-ready tile dataset for semantic segmentation of oil spill patterns in SAR imagery.

## Artifacts
- Image-mask triplets (PNG)
- Raster support files (8-bit and 16-bit TIFF)
- Vector labels (GeoJSON, KML, Shapefile bundle)
- Feature statistics files (`features_16bit.csv`, `features_8bit.csv`)
- Train/val/test manifests
- Checksums

## Ground Truth
Use masks in `images/data/mask_1c/` (single-channel class-index mask) or `images/data/mask_rgb/` (three-channel RGB rendering of the same class-index mask).

Class legend is provided in `images/data/class_legend.csv`.

Mask class mapping:
- `0` = `SEA` (background), RGB `#000000` (black)
- `1` = `OIL SPILL`, RGB `#00FFFF` (cyan)
- `2` = `SEEPAGE SLICK`, RGB `#FF0000` (red)
