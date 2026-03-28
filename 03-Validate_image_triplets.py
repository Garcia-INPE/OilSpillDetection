#!/usr/bin/env python3

"""
Validate image triplets for deep learning datasets.

Checks performed:
- matching sample IDs across IMG-RGB, LABELS-1D, LABELS-RGB
- identical image dimensions within each triplet
- optional expected-size validation

Outputs:
- CSV report with one row per sample
- console summary with counts and status
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from PIL import Image


VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate image/label triplets under an IMAGES directory."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("dataout/02.0-DS_by_geom_bbox/IMAGES"),
        help="Root directory that contains IMG-RGB, LABELS-1D and LABELS-RGB.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Expected width in pixels. If omitted, size is not enforced.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Expected height in pixels. If omitted, size is not enforced.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="CSV output report path.",
    )
    return parser.parse_args()


def list_image_files(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
            yield path


def sample_id_from_name(path: Path, folder_name: str) -> str:
    stem = path.stem
    if folder_name == "LABELS-1D" and stem.endswith("_1D"):
        return stem[:-3]
    if folder_name == "LABELS-RGB" and stem.endswith("_RGB"):
        return stem[:-4]
    return stem


def build_index(folder: Path, folder_name: str) -> Dict[str, Path]:
    index: Dict[str, Path] = {}
    for path in list_image_files(folder):
        sample_id = sample_id_from_name(path, folder_name)
        index[sample_id] = path
    return index


def get_size(path: Optional[Path]) -> Optional[Tuple[int, int]]:
    if path is None:
        return None
    with Image.open(path) as img:
        return img.size


def validate_triplet(
    sample_id: str,
    img_path: Optional[Path],
    label_1d_path: Optional[Path],
    label_rgb_path: Optional[Path],
    expected_size: Optional[Tuple[int, int]],
) -> Dict[str, object]:
    img_size = get_size(img_path)
    label_1d_size = get_size(label_1d_path)
    label_rgb_size = get_size(label_rgb_path)

    exists_img = img_path is not None
    exists_label_1d = label_1d_path is not None
    exists_label_rgb = label_rgb_path is not None

    all_present = exists_img and exists_label_1d and exists_label_rgb
    sizes = [size for size in [img_size, label_1d_size, label_rgb_size] if size is not None]
    same_size = len(set(sizes)) == 1 if sizes else False
    expected = all(size == expected_size for size in sizes) if (expected_size is not None and sizes) else True
    valid = all_present and same_size and expected

    issues: List[str] = []
    if not exists_img:
        issues.append("missing_img")
    if not exists_label_1d:
        issues.append("missing_label_1d")
    if not exists_label_rgb:
        issues.append("missing_label_rgb")
    if all_present and not same_size:
        issues.append("size_mismatch")
    if expected_size is not None and same_size and not expected:
        issues.append("unexpected_size")

    return {
        "sample_id": sample_id,
        "img_exists": exists_img,
        "label_1d_exists": exists_label_1d,
        "label_rgb_exists": exists_label_rgb,
        "img_size": "" if img_size is None else f"{img_size[0]}x{img_size[1]}",
        "label_1d_size": "" if label_1d_size is None else f"{label_1d_size[0]}x{label_1d_size[1]}",
        "label_rgb_size": "" if label_rgb_size is None else f"{label_rgb_size[0]}x{label_rgb_size[1]}",
        "valid": valid,
        "issues": "|".join(issues),
    }


def main() -> None:
    args = parse_args()
    root = args.root
    report_path = args.report if args.report is not None else root / "validation_report.csv"

    if (args.width is None) != (args.height is None):
        raise ValueError("Provide both --width and --height, or omit both.")

    expected_size = (args.width, args.height) if args.width is not None else None

    img_dir = root / "IMG-RGB"
    label_1d_dir = root / "LABELS-1D"
    label_rgb_dir = root / "LABELS-RGB"

    for directory in [img_dir, label_1d_dir, label_rgb_dir]:
        if not directory.exists() or not directory.is_dir():
            raise FileNotFoundError(f"Required directory not found: {directory}")

    img_index = build_index(img_dir, "IMG-RGB")
    label_1d_index = build_index(label_1d_dir, "LABELS-1D")
    label_rgb_index = build_index(label_rgb_dir, "LABELS-RGB")

    sample_ids = sorted(set(img_index) | set(label_1d_index) | set(label_rgb_index))
    rows = [
        validate_triplet(
            sample_id,
            img_index.get(sample_id),
            label_1d_index.get(sample_id),
            label_rgb_index.get(sample_id),
            expected_size,
        )
        for sample_id in sample_ids
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id",
                "img_exists",
                "label_1d_exists",
                "label_rgb_exists",
                "img_size",
                "label_1d_size",
                "label_rgb_size",
                "valid",
                "issues",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    valid_rows = sum(1 for row in rows if row["valid"])
    invalid_rows = len(rows) - valid_rows

    print(f"[INFO] Root: {root}")
    print(
        f"[INFO] Expected size: {args.width}x{args.height}"
        if expected_size is not None
        else "[INFO] Expected size: not enforced"
    )
    print(f"[INFO] Report: {report_path}")
    print(f"[DONE] Samples checked: {len(rows)}")
    print(f"[DONE] Valid triplets: {valid_rows}")
    print(f"[DONE] Invalid triplets: {invalid_rows}")

    if invalid_rows:
        print("[WARN] Some samples failed validation. Inspect the CSV report for details.")
    else:
        if expected_size is None:
            print("[DONE] All samples have matching image/label triplets and consistent per-sample dimensions.")
        else:
            print("[DONE] All samples have matching image/label triplets and expected dimensions.")


if __name__ == "__main__":
    main()