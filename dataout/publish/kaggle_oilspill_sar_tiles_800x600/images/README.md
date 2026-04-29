# images/

## Purpose
This folder contains PNG image tiles for semantic segmentation.

## Contents
- `data/`: data container for image-scope assets
- `data/rgb/`: model input images (3-channel PNG)
- `data/mask_1c/`: single-channel class-index masks (ground truth)
- `data/mask_rgb/`: RGB visualization of the same masks
- `data/class_legend.csv`: class index and color mapping

## File Naming
Files are tile-based and share the same base name:
- Input image: `data/rgb/IMG_XX_TILE_YYY.png`
- Index mask: `data/mask_1c/IMG_XX_TILE_YYY_mask.png`
- RGB mask: `data/mask_rgb/IMG_XX_TILE_YYY_mask_rgb.png`

Use the common base `IMG_XX_TILE_YYY` to pair image and labels.

## How To Use
1. Train with `data/rgb/` as input and `data/mask_1c/` as target.
2. Use `data/class_legend.csv` to decode class indices.
3. Use `data/mask_rgb/` only for visualization and QA (not as training target).

## Class Mapping
See `data/class_legend.csv` for the authoritative mapping.

## Quick Script
## ML Pipeline
- See `images/ml_pipeline/` for train/validate/test examples with installation scripts and persisted outputs.
