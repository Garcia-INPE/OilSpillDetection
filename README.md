# OIL SPILL DETECTION BY RS AND AI

## 01 EDA Vectors

- Script: `01-EDA-Vectors.py`
- Output directory: `dataout/01-EDA-Vectors`

## 02.0 Dataset Build by Geometry BBox

- Script: `02.0-Build_DS_by_geom_bbox.py`
- Output directory: `dataout/02.0-DS_by_geom_bbox`

## 02.1.1 Estimate Windows Over Geometries

- Script: `02.1.1-Estimate_windows_over_geoms_by_target_size.py`
- Plot helper module: `Fun_plot_tiff_with_polygons.py` (supports multiple sizes like 800x600 and 400x300)
- Output directory: `dataout/02.1-DS_by_manual_windows/800x600_windows/1`
- Output JSON: `dataout/02.1-DS_by_manual_windows/800x600_windows/1/Created_windows.json`

## 02.1.2 Adjust Estimated Windows

- Script: `02.1.2-Adjust_estimate_windows.py`
- Output directory: `dataout/02.1-DS_by_manual_windows/800x600_windows/2`
- Output JSON: `dataout/02.1-DS_by_manual_windows/800x600_windows/2/Adjusted_windows.json`

## 02.1.3 Build Dataset From Manual Windows

- Script: `02.1.3-Build_DS_from_manual_windows.py`
- Output directory: `dataout/02.1-DS_by_manual_windows/800x600_windows/3`

## 04 EDA CSV

- Script: `04-EDA-CSV.py`
- Scope: statistics and plots by `CLASSE` only.
- Input directory (versions): `dataout/02.0-DS_by_geom_bbox/CSV`
- Output root directory: `dataout/04-EDA-CSV`
- Output layout:
  - `dataout/04-EDA-CSV/` (root) — CLASSE accounting outputs produced once (`classe_counts.csv`, `bar_counts.png`); identical across bit-depth versions since class annotations are independent of pixel resolution.
  - `dataout/04-EDA-CSV/8bits/` — float/numeric analysis for the 8-bit version (`missing_report`, numeric summaries, float-mean CSV, z-score heatmap, boxplot and histogram families, `EDA_summary.md`).
  - `dataout/04-EDA-CSV/16bits/` — same float/numeric analysis for the 16-bit version.
