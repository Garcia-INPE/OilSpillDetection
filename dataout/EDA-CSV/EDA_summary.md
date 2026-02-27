# EDA Report - CSV

## Data Source
- CSV: /home/jrmgarcia/ProjDocs/OilSpill/src/dataout/DS/CSV/Oil_Stats_16bits.csv
- Total rows: 385
- Total columns: 47

## Missing Values
|             |   missing_count |   missing_pct |
|:------------|----------------:|--------------:|
| CLASSE      |               0 |             0 |
| SUBCLASSE   |               0 |             0 |
| AREA_KM2    |               0 |             0 |
| PERIM_KM    |               0 |             0 |
| AREA_KM_DS  |               0 |             0 |
| PERIM_KM_DS |               0 |             0 |

## Distribution of CLASSE
| CLASSE        |   count |
|:--------------|--------:|
| OIL SPILL     |     327 |
| SEEPAGE SLICK |      58 |

Top CLASSE: **OIL SPILL** (327)

## Distribution of SUBCLASSE
| SUBCLASSE           |   count |
|:--------------------|--------:|
| IDENTIFIED TARGET   |     224 |
| UNIDENTIFIED TARGET |     103 |
| CANTAREL            |      26 |
| CLUSTER SEEPAGE     |      20 |
| ORPHAN SEEPAGE      |      12 |

### SUBCLASSE Share (%)
| SUBCLASSE           |   pct |
|:--------------------|------:|
| IDENTIFIED TARGET   | 58.18 |
| UNIDENTIFIED TARGET | 26.75 |
| CANTAREL            |  6.75 |
| CLUSTER SEEPAGE     |  5.19 |
| ORPHAN SEEPAGE      |  3.12 |

Top SUBCLASSE: **IDENTIFIED TARGET** (224)

## CLASSE x SUBCLASSE
### Counts
| CLASSE        |   CANTAREL |   CLUSTER SEEPAGE |   IDENTIFIED TARGET |   ORPHAN SEEPAGE |   UNIDENTIFIED TARGET |
|:--------------|-----------:|------------------:|--------------------:|-----------------:|----------------------:|
| OIL SPILL     |          0 |                 0 |                 224 |                0 |                   103 |
| SEEPAGE SLICK |         26 |                20 |                   0 |               12 |                     0 |

### Row Percentage (%)
| CLASSE        |   CANTAREL |   CLUSTER SEEPAGE |   IDENTIFIED TARGET |   ORPHAN SEEPAGE |   UNIDENTIFIED TARGET |
|:--------------|-----------:|------------------:|--------------------:|-----------------:|----------------------:|
| OIL SPILL     |       0    |              0    |                68.5 |             0    |                  31.5 |
| SEEPAGE SLICK |      44.83 |             34.48 |                 0   |            20.69 |                   0   |

## Differences Between CLASSE and SUBCLASSE
### Number of SUBCLASSE represented inside each CLASSE
| CLASSE        |   n_subclasses |
|:--------------|---------------:|
| SEEPAGE SLICK |              3 |
| OIL SPILL     |              2 |

### Dominant SUBCLASSE inside each CLASSE
| CLASSE        | dominant_subclasse   |   row_pct |
|:--------------|:---------------------|----------:|
| OIL SPILL     | IDENTIFIED TARGET    |     68.5  |
| SEEPAGE SLICK | CANTAREL             |     44.83 |

### SUBCLASSE association strength
A value of 1 means a SUBCLASSE appears in only one CLASSE.
| SUBCLASSE           |   num_classes |
|:--------------------|--------------:|
| CANTAREL            |             1 |
| CLUSTER SEEPAGE     |             1 |
| IDENTIFIED TARGET   |             1 |
| ORPHAN SEEPAGE      |             1 |
| UNIDENTIFIED TARGET |             1 |

### CLASSE composition inside each SUBCLASSE (row %) 
| SUBCLASSE           |   OIL SPILL |   SEEPAGE SLICK |
|:--------------------|------------:|----------------:|
| CANTAREL            |           0 |             100 |
| CLUSTER SEEPAGE     |           0 |             100 |
| IDENTIFIED TARGET   |         100 |               0 |
| ORPHAN SEEPAGE      |           0 |             100 |
| UNIDENTIFIED TARGET |         100 |               0 |

### Dominant CLASSE per SUBCLASSE
| SUBCLASSE           | dominant_classe   |   dominant_pct |   num_classes |   total_count |
|:--------------------|:------------------|---------------:|--------------:|--------------:|
| IDENTIFIED TARGET   | OIL SPILL         |            100 |             1 |           224 |
| UNIDENTIFIED TARGET | OIL SPILL         |            100 |             1 |           103 |
| CANTAREL            | SEEPAGE SLICK     |            100 |             1 |            26 |
| CLUSTER SEEPAGE     | SEEPAGE SLICK     |            100 |             1 |            20 |
| ORPHAN SEEPAGE      | SEEPAGE SLICK     |            100 |             1 |            12 |

## Numeric Features
- IDX_POLY, CENTR_KM_LAT, CENTR_KM_LON, AREA_KM2, PERIM_KM, COMPLEX_MEAS, SPREAD, SHP_FACT, HU_MOM1, HU_MOM2, HU_MOM3, HU_MOM4, HU_MOM5, HU_MOM6, HU_MOM7, CIRCULARITY, PERI_AREA_RATIO, FG_STD, FG_VAR, FG_MIN, FG_MAX, FG_MEAN, FG_MEDIAN, FG_VAR_COEF, BG_STD, BG_VAR, BG_MIN, BG_MAX, BG_MEAN, BG_MEDIAN, BG_VAR_COEF, FG_DARK_INTENS, FG_BG_KS_STAT, FG_BG_MW_STAT, FG_BG_RAT_ARI, FG_BG_RAT_QUA, AREA_KM_DS, PERIM_KM_DS
- See `numeric_summary_overall.csv`, `numeric_summary_by_classe.csv`, and `numeric_summary_by_classe_subclasse.csv`.

## Z-score Interpretation
The float-feature comparison heatmaps use z-score normalization per feature across groups.
- z = (value - feature_mean) / feature_std
- z > 0: group is above the feature average
- z < 0: group is below the feature average
- |z| indicates how far the group is from average in standard deviation units
This allows fair comparison across features with different numeric scales.

## Generated Artifacts
- CSV: distributions, crosstabs, missing report, and numeric summaries.
- PNG: class bars, top-subclass bars, crosstab heatmap, numeric boxplots by class, float-feature aggregated comparison heatmaps, and feature-family boxplots by CLASSE/SUBCLASSE.