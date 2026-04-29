# raster/

## Purpose
This folder contains raster support data and vectorized labels linked to the tile dataset.

## Contents
- `data/`: data container for raster-scope assets
- `data/tiff_8bit/`: 8-bit GeoTIFF tiles
- `data/tiff_16bit/`: 16-bit GeoTIFF tiles
- `data/vectors/`: polygon labels in geospatial formats

## How To Use
1. Use `data/tiff_8bit/` for workflows that require lower storage and broad tool compatibility.
2. Use `data/tiff_16bit/` when preserving radiometric detail is important.
3. Use `data/vectors/` for GIS inspection, spatial joins, and polygon-level analysis.

## Notes
- PNG files in `images/` are the primary segmentation training assets.
- GeoTIFF and vector files are useful for geospatial validation and extended analysis.

## Quick Script
## ML Pipeline
- See `raster/ml_pipeline/` for train/validate/test examples using GeoTIFF inputs and segmentation masks.
