# Dataset Card: Geom BBox Dataset (02.0)

## 1. Summary

- **Name:** Oil Spill Detection Dataset - Geom BBox build
- **Version:** v0.1.0 (working)
- **Primary task:** oil spill segmentation / detection from paired image-mask triplets
- **Generation method:** geometry-driven bounding-box extraction
- **Dataset root:** `02.0-DS_by_geom_bbox/`

## 2. Data Composition

- **Primary feature table:** `CSV/Oil_Stats_16bits.csv` and `CSV/Oil_Stats_8bits.csv`
- **Rows in `Oil_Stats_16bits.csv`:** 385
- **Class distribution (CLASSE):**
	- `OIL SPILL`: 327
	- `SEEPAGE SLICK`: 58
- **Image/mask bundles:**
	- `IMAGES/IMG-RGB/`
	- `IMAGES/LABELS-1D/`
	- `IMAGES/LABELS-RGB/`

## 3. Build and Validation Workflow

- **Dataset generation reference:** `02.0-Build_DS_by_geom_bbox.py`
- **Triplet validation reference:** `03-Validate_image_triplets.py`
- **Default validation output:** `02.0-DS_by_geom_bbox/IMAGES/validation_report.csv`
- **Package README:** `02.0-DS_by_geom_bbox/README.md`

Validation covers:

- sample-id pairing consistency across `IMG-RGB`, `LABELS-1D`, `LABELS-RGB`
- per-sample size consistency across triplets
- optional fixed-size enforcement via `--width` and `--height`

## 4. Feature Scope

The CSVs include geometry and radiometric/statistical descriptors used in EDA and downstream modeling, including:

- geometric descriptors (`AREA_KM2`, `PERIM_KM`, `COMPLEX_MEAS`, `CIRCULARITY`, etc.)
- Hu moments (`HU_MOM1` to `HU_MOM7`)
- foreground/background statistics (`FG_*`, `BG_*`, `FG_BG_*`)
- target labels (`CLASSE`)

## 5. EDA Products Linked to This Dataset

Associated CSV EDA products are generated with `04-EDA-CSV.py` and stored in:

- `04-EDA-CSV/` (shared CLASSE accounting)
- `04-EDA-CSV/8bits/`
- `04-EDA-CSV/16bits/`

## 6. Recommended Splits and Packaging

This package already includes:

- `splits/` (train/val/test manifests placeholder or populated externally)
- `checksums.sha256`
- `README.md` with publication checklist

## 7. Known Limitations

- Class imbalance is present (`OIL SPILL` dominates over `SEEPAGE SLICK`).
- Label taxonomy is currently emphasized at the class level; subclass analyses are present in the raw data history but are not the main focus of the current package summaries.
- License/citation metadata still need final publication values.

## 8. Licensing and Citation

- **Dataset license:** TBD
- **Usage restrictions:** TBD
- **Citation text / DOI:** TBD

## 9. Maintenance

- **Maintainers:** project owners
- **Update policy:** update this card whenever generation logic, schema, or counts change
