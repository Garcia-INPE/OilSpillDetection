# splits/

## Purpose
This folder defines the official train/validation/test partitions.

## Contents
- `train.csv`, `val.csv`, `test.csv`: split manifests with relative file paths

## How To Use
1. Load the desired split CSV (`train.csv`, `val.csv`, or `test.csv`).
2. Resolve paths relative to the dataset root folder.

## Recommendations
- Keep these files unchanged to ensure reproducible experiments.
- Report results using this official split protocol, i.e., use the predefined train.csv, val.csv, and test.csv splits exactly as provided, and report metrics separately for each split.
