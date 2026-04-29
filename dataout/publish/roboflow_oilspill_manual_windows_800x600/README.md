# Roboflow Publication Prep - Oil Spill Manual Windows (800x600)

This folder prepares the dataset for Roboflow upload and conversion workflows.

## Included Staging Layout

- `raw/train/images`, `raw/train/masks`
- `raw/valid/images`, `raw/valid/masks`
- `raw/test/images`, `raw/test/masks`
- `yolo_seg/{train,valid,test}/{images,labels}`
- `coco/{train,valid,test}/images`
- `coco/annotations/`
- `train.csv`, `valid.csv`, `test.csv` (source split manifests)

## Current State

- Split folders are physically materialized (17/3/4).
- Images and masks are aligned 1:1 in raw folders.
- YOLO labels and COCO annotations are not generated yet.

## Next Mandatory Steps for Roboflow

1. Convert binary masks (`raw/*/masks`) to polygon or RLE annotations.
2. Generate YOLO segmentation `.txt` labels into `yolo_seg/*/labels`.
3. Generate COCO JSON files in `coco/annotations`.
4. Validate class IDs and instance consistency.
5. Upload to Roboflow using either YOLO or COCO package.
