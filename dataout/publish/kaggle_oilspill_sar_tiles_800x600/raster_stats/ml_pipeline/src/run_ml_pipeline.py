#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from common import build_split_dataframe, to_xy


DATASET_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = Path(__file__).resolve().parent.parent
RESULTS_CSV = PIPELINE_DIR / "results.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run train/validate/test for raster-stats RandomForest and save CSV metrics"
    )
    p.add_argument("--bits", choices=["8bit", "16bit", "both"], default="both")
    return p.parse_args()


def eval_split(model: RandomForestClassifier, split_df: pd.DataFrame) -> dict[str, float | int]:
    x, y, feature_cols = to_xy(split_df)
    y_pred = model.predict(x)
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        y,
        y_pred,
        average="macro",
        zero_division=0,
    )
    return {
        "rows": int(len(x)),
        "n_features": int(len(feature_cols)),
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision_macro": float(precision_macro),
        "recall_macro": float(recall_macro),
        "f1_macro": float(f1_macro),
    }


def run_for_bits(bits: str) -> list[dict[str, float | int | str]]:
    train_df = build_split_dataframe(DATASET_ROOT, "train", bits=bits)
    val_df = build_split_dataframe(DATASET_ROOT, "val", bits=bits)
    test_df = build_split_dataframe(DATASET_ROOT, "test", bits=bits)

    x_train, y_train, _ = to_xy(train_df)
    model = RandomForestClassifier(
        n_estimators=300,
        criterion="gini",
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        bootstrap=True,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)
    model_cfg = model.get_params()

    rows: list[dict[str, float | int | str]] = []
    for split_name, split_df in (("val", val_df), ("test", test_df)):
        metrics = eval_split(model, split_df)
        cfg_payload = {
            "rf_n_estimators": int(model_cfg["n_estimators"]),
            "rf_criterion": str(model_cfg["criterion"]),
            "rf_max_depth": str(model_cfg["max_depth"]),
            "rf_min_samples_split": int(model_cfg["min_samples_split"]),
            "rf_min_samples_leaf": int(model_cfg["min_samples_leaf"]),
            "rf_max_features": str(model_cfg["max_features"]),
            "rf_bootstrap": bool(model_cfg["bootstrap"]),
            "rf_class_weight": str(model_cfg["class_weight"]),
            "rf_random_state": int(model_cfg["random_state"]),
            "rf_n_jobs": int(model_cfg["n_jobs"]),
        }
        rows.append(
            {
                "bits": bits,
                "split": split_name,
                **cfg_payload,
                **metrics,
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    bits_list = ["8bit", "16bit"] if args.bits == "both" else [args.bits]

    all_rows: list[dict[str, float | int | str]] = []
    for bits in bits_list:
        all_rows.extend(run_for_bits(bits))

    out_df = pd.DataFrame(all_rows)
    out_df.to_csv(RESULTS_CSV, index=False)
    print(f"Saved results to: {RESULTS_CSV}")


if __name__ == "__main__":
    main()