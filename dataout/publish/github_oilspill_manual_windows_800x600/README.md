# Oil Spill Manual Windows Dataset (800x600) - GitHub Release Root

This folder is a GitHub publication root containing only final payload assets.
It excludes manual window creation/adjustment process artifacts from stages 1 and 2.

## Included

- `CSV/`
- `IMAGES/`
- `RASTER/`
- `splits/`
- `checksums.sha256`
- `DATASET_CARD.md`
- `LICENSE.txt`

Vector shapefile bundle names in `RASTER/LABELS-VECTOR/SHAPEFILE/`:
- `All_Vectors.*`
- `Individual_Vectors.zip`

## Release Strategy

1. Use Git tag-based releases (`vX.Y.Z`).
2. Keep a short `CHANGELOG.md` per release.
3. Attach a compressed release asset if repository size becomes heavy.
4. Use Git LFS for large binary patterns listed in `.gitattributes`.

## Integrity

Verify file integrity with:

```bash
sha256sum -c checksums.sha256
```
