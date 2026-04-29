# raster_stats/

## Purpose
This folder contains polygon-level feature statistics files aligned with the tile dataset.

## Contents
- `data/`: data container for raster-statistics assets
- `data/features_8bit.csv`: features computed from 8-bit imagery
- `data/features_16bit.csv`: features computed from 16-bit imagery

## Key Fields
- `RESULT_BASENAME`: tile identifier (example: `IMG_01_TILE_001`)
- `ID_POLY`: polygon identifier
- `CLASSE`: polygon class label

## How To Use
1. Choose `data/features_8bit.csv` or `data/features_16bit.csv` based on your experiment.
2. Join statistics files to image/mask assets using `RESULT_BASENAME`.
3. Use `CLASSE` for polygon-level classification, statistics, or QA.

## Notes
- Both files follow the same tile/sample scope.
- These statistics files complement segmentation masks and are not a replacement for pixel-level labels.

## Quick Script
## ML Pipeline
- See `raster_stats/ml_pipeline/` for train/validate/test examples for tabular modeling.
