# EDA Report - Vector Shapefile

## Data Source
- Shapefile: /home/jrmgarcia/ProjData/Oil_Spill/Cantarell_Beisl/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp
- Total rows: 409
- Total columns: 12
- CRS: EPSG:4326

## Missing Values
|           |   missing_count |   missing_pct |
|:----------|----------------:|--------------:|
| CLASSE    |               0 |             0 |
| SUBCLASSE |               0 |             0 |
| geometry  |               0 |             0 |

## Distribution of CLASSE
| CLASSE        |   count |
|:--------------|--------:|
| OIL SPILL     |     349 |
| SEEPAGE SLICK |      60 |

Top CLASSE: **OIL SPILL** (349)

## Distribution of SUBCLASSE
| SUBCLASSE           |   count |
|:--------------------|--------:|
| IDENTIFIED TARGET   |     243 |
| UNIDENTIFIED TARGET |     106 |
| CANTAREL            |      26 |
| CLUSTER SEEPAGE     |      22 |
| ORPHAN SEEPAGE      |      12 |

Top SUBCLASSE: **IDENTIFIED TARGET** (243)

## CLASSE x SUBCLASSE
### Counts
| CLASSE        |   CANTAREL |   CLUSTER SEEPAGE |   IDENTIFIED TARGET |   ORPHAN SEEPAGE |   UNIDENTIFIED TARGET |
|:--------------|-----------:|------------------:|--------------------:|-----------------:|----------------------:|
| OIL SPILL     |          0 |                 0 |                 243 |                0 |                   106 |
| SEEPAGE SLICK |         26 |                22 |                   0 |               12 |                     0 |

### Row Percentage (%)
| CLASSE        |   CANTAREL |   CLUSTER SEEPAGE |   IDENTIFIED TARGET |   ORPHAN SEEPAGE |   UNIDENTIFIED TARGET |
|:--------------|-----------:|------------------:|--------------------:|-----------------:|----------------------:|
| OIL SPILL     |       0    |              0    |               69.63 |                0 |                 30.37 |
| SEEPAGE SLICK |      43.33 |             36.67 |                0    |               20 |                  0    |

## Differences Between CLASSE and SUBCLASSE
### Number of SUBCLASSE represented inside each CLASSE
| CLASSE        |   n_subclasses |
|:--------------|---------------:|
| SEEPAGE SLICK |              3 |
| OIL SPILL     |              2 |

### Dominant SUBCLASSE inside each CLASSE
| CLASSE        | dominant_subclasse   |   row_pct |
|:--------------|:---------------------|----------:|
| OIL SPILL     | IDENTIFIED TARGET    |     69.63 |
| SEEPAGE SLICK | CANTAREL             |     43.33 |

### SUBCLASSE association strength
A value of 1 means a SUBCLASSE appears in only one CLASSE.
| SUBCLASSE           |   num_classes |
|:--------------------|--------------:|
| CANTAREL            |             1 |
| CLUSTER SEEPAGE     |             1 |
| IDENTIFIED TARGET   |             1 |
| ORPHAN SEEPAGE      |             1 |
| UNIDENTIFIED TARGET |             1 |

## Numeric Features Available
- AREA_KM, PERIM_KM
- See CSV files: `numeric_summary_by_classe.csv` and `numeric_summary_by_classe_subclasse.csv`.

## Generated Artifacts
- CSV: missing report, classe/subclasse counts, crosstabs, and association metrics.
- PNG: class bars, top-subclass bars, crosstab heatmap, and optional numeric boxplots.