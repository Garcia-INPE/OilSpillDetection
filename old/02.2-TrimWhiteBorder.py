#!/usr/bin/env python3

"""
Trim pure-white outer borders from paired image/label triplets.

The crop box is computed from IMG-RGB and then applied to LABELS-1D and
LABELS-RGB for the same sample to preserve exact alignment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


def is_white_rgb(pixel: Tuple[int, int, int]) -> bool:
    return pixel[0] == 255 and pixel[1] == 255 and pixel[2] == 255


def compute_white_border_box(img_rgb: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    rgb = img_rgb.convert("RGB")
    width, height = rgb.size
    px = rgb.load()

    top = 0
    while top < height and all(is_white_rgb(px[x, top]) for x in range(width)):
        top += 1

    bottom = height - 1
    while bottom >= top and all(is_white_rgb(px[x, bottom]) for x in range(width)):
        bottom -= 1

    left = 0
    while left < width and all(is_white_rgb(px[left, y]) for y in range(top, bottom + 1)):
        left += 1

    right = width - 1
    while right >= left and all(is_white_rgb(px[right, y]) for y in range(top, bottom + 1)):
        right -= 1

    # No non-white content detected or nothing to crop.
    if top > bottom or left > right:
        return None

    box = (left, top, right + 1, bottom + 1)
    if box == (0, 0, width, height):
        return None
    return box


def main() -> None:
    root = Path("dataout/DS/IMAGES")
    dir_img = root / "IMG-RGB"
    dir_l1d = root / "LABELS-1D"
    dir_lrgb = root / "LABELS-RGB"

    if not (dir_img.exists() and dir_l1d.exists() and dir_lrgb.exists()):
        raise FileNotFoundError("Expected IMG-RGB, LABELS-1D, and LABELS-RGB under dataout/DS/IMAGES")

    processed = 0
    trimmed = 0
    skipped = 0

    for img_path in sorted(dir_img.glob("*.png")):
        sample_id = img_path.stem
        l1d_path = dir_l1d / f"{sample_id}_1D.png"
        lrgb_path = dir_lrgb / f"{sample_id}_RGB.png"

        if not l1d_path.exists() or not lrgb_path.exists():
            skipped += 1
            continue

        with Image.open(img_path) as img, Image.open(l1d_path) as lbl1d, Image.open(lrgb_path) as lblrgb:
            if img.size != lbl1d.size or img.size != lblrgb.size:
                skipped += 1
                continue

            box = compute_white_border_box(img)
            processed += 1

            if box is None:
                continue

            img.crop(box).save(img_path)
            lbl1d.crop(box).save(l1d_path)
            lblrgb.crop(box).save(lrgb_path)
            trimmed += 1

    print(f"[DONE] Triplets scanned: {processed}")
    print(f"[DONE] Triplets trimmed: {trimmed}")
    print(f"[DONE] Triplets skipped: {skipped}")


if __name__ == "__main__":
    main()
