from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import pandas as pd


NON_FEATURE_COLS = {
    "IMG_FNAME",
    "IDX_POLY",
    "ID_POLY",
    "SATELITE",
    "BEAM_MODE",
    "RESULT_BASENAME",
    "COMPOSITE_BASENAME",
    "TARGET_TILE_WIDTH",
    "TARGET_TILE_HEIGHT",
    "CLIPPED_WIDTH",
    "CLIPPED_HEIGHT",
    "GRID_COLS",
    "GRID_ROWS",
    "COMPOSITE_WIDTH",
    "COMPOSITE_HEIGHT",
    "PAD_LEFT",
    "PAD_RIGHT",
    "PAD_TOP",
    "PAD_BOTTOM",
    "IS_COMPOSITE",
    "PANEL_INDEX",
    "PANEL_ROW",
    "PANEL_COL",
    "PANEL_COUNT",
    "POLYS_IN_PANEL",
    "POLYS_IN_GROUP",
    "UTM_ZONE",
    "FG_BG_KS_RES",
    "FG_BG_MW_RES",
    "AREA_KM_DS",
    "PERIM_KM_DS",
    "CLASSE",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_split_ids(dataset_root: Path, split_name: str) -> set[str]:
    p = dataset_root / "splits" / f"{split_name}.csv"
    df = pd.read_csv(p)
    if "sample_id" not in df.columns:
        raise ValueError(f"Missing 'sample_id' column in split manifest: {p}")
    return set(df["sample_id"].dropna().astype(str).tolist())


def load_stats_table(dataset_root: Path, bits: str = "8bit") -> pd.DataFrame:
    p = dataset_root / "raster_stats" / "data" / f"features_{bits}.csv"
    return pd.read_csv(p, sep=";")


def build_split_dataframe(dataset_root: Path, split_name: str, bits: str = "8bit") -> pd.DataFrame:
    split_ids = load_split_ids(dataset_root, split_name)
    df = load_stats_table(dataset_root, bits)
    out = df[df["RESULT_BASENAME"].isin(split_ids)].copy()
    out = out.dropna(subset=["CLASSE"])
    return out


def to_xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, list[str]]:
    feature_cols = [
        c for c in df.columns
        if c not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(df[c])
    ]
    x = df[feature_cols].fillna(0.0)
    y = df["CLASSE"].astype(str)
    return x, y, feature_cols
