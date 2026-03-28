# Split Manifests

This folder stores dataset split files for reproducible experiments.

## Files

- `train.csv`
- `val.csv`
- `test.csv`

## Required columns

- `sample_id`: unique ID for a sample.
- `image_path`: relative path from `DS/` to image/raster input.
- `mask_path`: relative path from `DS/` to mask/label file (if applicable).
- `classe`: primary class label.
- `subclasse`: subclass label.

## Rules

- A `sample_id` must appear in exactly one split.
- Paths must be valid and relative.
- Keep class distributions documented in publication artifacts.
