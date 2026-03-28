# EDA Report - CSV

## Data Source
- CSV: dataout/02.0-DS_by_geom_bbox/CSV/Oil_Stats_8bits.csv
- Total rows: 409
- Total columns: 47

## Missing Values
|             |   missing_count |   missing_pct |
|:------------|----------------:|--------------:|
| CLASSE      |               0 |             0 |
| AREA_KM2    |               0 |             0 |
| PERIM_KM    |               0 |             0 |
| AREA_KM_DS  |               0 |             0 |
| PERIM_KM_DS |               0 |             0 |

## Distribution of CLASSE
| CLASSE        |   count |
|:--------------|--------:|
| OIL SPILL     |     349 |
| SEEPAGE SLICK |      60 |

Top CLASSE: **OIL SPILL** (349)

## Numeric Features
- IDX_POLY, CENTR_KM_LAT, CENTR_KM_LON, AREA_KM2, PERIM_KM, COMPLEX_MEAS, SPREAD, SHP_FACT, HU_MOM1, HU_MOM2, HU_MOM3, HU_MOM4, HU_MOM5, HU_MOM6, HU_MOM7, CIRCULARITY, PERI_AREA_RATIO, FG_STD, FG_VAR, FG_MIN, FG_MAX, FG_MEAN, FG_MEDIAN, FG_VAR_COEF, BG_STD, BG_VAR, BG_MIN, BG_MAX, BG_MEAN, BG_MEDIAN, BG_VAR_COEF, FG_DARK_INTENS, FG_BG_KS_STAT, FG_BG_MW_STAT, FG_BG_RAT_ARI, FG_BG_RAT_QUA, AREA_KM_DS, PERIM_KM_DS, SUBCLASSE
- See `numeric_summary_overall.csv` and `numeric_summary_by_classe.csv`.

## Z-score Interpretation
The float-feature comparison heatmaps use z-score normalization per feature across groups.
- z = (value - feature_mean) / feature_std
- z > 0: group is above the feature average
- z < 0: group is below the feature average
- |z| indicates how far the group is from average in standard deviation units
This allows fair comparison across features with different numeric scales.

## Generated Artifacts
- CSV: CLASSE distribution, missing report, and numeric summaries by CLASSE.
- PNG (core): `bar_counts.png` for CLASSE counts and float-feature aggregated comparison heatmaps by CLASSE.
- PNG (families): feature-family boxplots and `hist_family_*` histogram panels by CLASSE.