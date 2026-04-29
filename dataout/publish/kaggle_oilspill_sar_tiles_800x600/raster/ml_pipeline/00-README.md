# ML Pipeline Examples (Train, Validate, Test)

This folder contains end-to-end example scripts for semantic segmentation using raster GeoTIFF tiles as input.

## What Is Included
- `requirements.txt`: Python dependencies.
- `01-install.sh`: package installation.
- `02-run_ml_pipeline.sh`: one command for train/validate/test execution.
- `src/train.py`: training pipeline with checkpoint persistence.
- `src/validate.py`: validation pipeline using a saved checkpoint.
- `src/test.py`: test pipeline with persisted metrics and predicted masks.
- `src/common.py`, `src/model.py`: source and model utilities.

Input/target mapping used by these scripts:
- Input: `raster/data/tiff_8bit/*.tiff` (or `raster/data/tiff_16bit/*.tiff`)
- Target: `images/data/mask_1c/*_mask.png`

## Setup
From this directory:

```bash
bash 01-install.sh
```

## Training
```bash
bash 02-run_ml_pipeline.sh train
```

To switch bit depth, pass `--tiff-variant 16bit` to train/validate/test.

Artifacts are saved to:
- `ml_pipeline/results/<run-name>/checkpoints/best.pt`
- `ml_pipeline/results/<run-name>/checkpoints/last.pt`
- `ml_pipeline/results/<run-name>/history.json`

## Validation
Example on validation split:
```bash
bash 02-run_ml_pipeline.sh validate
```

Metrics are saved to:
- `ml_pipeline/results/<run-name>/metrics_val.json`

## Testing
Example on test split:
```bash
bash 02-run_ml_pipeline.sh test
```

Test artifacts are saved to:
- `ml_pipeline/results/<run-name>/metrics_test.json`
- `ml_pipeline/results/<run-name>/test_samples.csv`
- `ml_pipeline/results/<run-name>/predictions/*.png`

## Notes
- Scripts accept `--device auto|cpu|cuda`.
- Default `--device auto` uses available compute automatically.
- Default `--dataset-root` points to the package root automatically.
