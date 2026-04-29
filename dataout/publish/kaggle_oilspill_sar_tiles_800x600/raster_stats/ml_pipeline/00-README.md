# ML Pipeline for Raster Statistics

This pipeline trains, validates, and tests tabular ML models using the feature statistics files in `raster_stats/`.

## Files
- `requirements.txt`
- `01-install.sh`
- `02-run_ml_pipeline.sh`
- `src/run_ml_pipeline.py`
- `src/common.py`

## Setup
From this directory:

```bash
bash 01-install.sh
```

## Run Full Pipeline
```bash
bash 02-run_ml_pipeline.sh both
```

Run a single bit-depth:
```bash
bash 02-run_ml_pipeline.sh 8bit
```

Equivalent direct command:
```bash
python src/run_ml_pipeline.py --bits both
```

## Persisted Outputs
- `results.csv` (saved directly in `ml_pipeline/`)

`results.csv` has one row per `(bits, split)` for val/test only, including metrics and Random Forest configuration fields.
