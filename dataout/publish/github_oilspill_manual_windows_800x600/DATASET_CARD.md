# Dataset Card: Oil Spill Manual Windows (800x600)

## Summary

- Name: Oil Spill Manual Windows Dataset (800x600)
- Build type: Manual window adjustment workflow
- Primary use: Segmentation and detection experiments on SAR-derived data

## Composition

- Final triplets: 24
- Feature table: `CSV/Oil_Stats_manual_windows_16bits_800x600.csv`
- Feature table rows: 44 (polygon-level records)

## File Layout

- `IMAGES/IMG-RGB/`
- `IMAGES/LABELS-1D/`
- `IMAGES/LABELS-RGB/`
- `CSV/`
- `RASTER/`
- `splits/`

## Generation Lineage

The payload is derived from stage `3/` of the manual-windows pipeline, after estimation and manual adjustment stages were completed.

## Known Limitations

- Class imbalance is present.
- `subclasse` is not populated in split manifests.
- Publication license/citation metadata depends on final project decisions.

## Ethics and Use

This dataset is intended for research and benchmarking in remote sensing and oil spill analysis. Users must verify regulatory and legal constraints for downstream use.
