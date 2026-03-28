from pathlib import Path
import argparse
import math
import re

import pandas as pd
import matplotlib.pyplot as plt


DEFAULT_CSV_DIR = Path("dataout") / "02.0-DS_by_geom_bbox" / "CSV"
DEFAULT_OUTDIR = Path("dataout/04-EDA-CSV")
DEFAULT_SEP = ";"


def _version_label_from_csv(csv_path: Path) -> str:
    match = re.search(r"(\d+bits)", csv_path.stem)
    return match.group(1) if match else csv_path.stem


def _collect_version_csvs(csv_dir: Path) -> list[Path]:
    candidates = sorted(csv_dir.glob("Oil_Stats_*bits.csv"))
    return [path for path in candidates if path.is_file() and path.stat().st_size > 0]


def save_series(series: pd.Series, path: Path, index_name: str) -> None:
    out_df = series.rename("count").reset_index()
    out_df.columns = [index_name, "count"]
    out_df.to_csv(path, index=False)


def plot_counts_bars(classe_counts: pd.Series, out_file: Path) -> None:
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    classe_counts.plot(kind="bar", ax=ax, color="#1f77b4")
    ax.set_title("Count of samples by CLASSE")
    ax.set_xlabel("CLASSE")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=35, labelsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    fig.suptitle("Counts by CLASSE", fontsize=13)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_file, dpi=150)
    plt.close()


def plot_heatmap(table: pd.DataFrame, title: str, out_file: Path) -> None:
    fig, ax = plt.subplots(figsize=(max(8, table.shape[1] * 1.8), max(5, table.shape[0] * 0.8)))
    im = ax.imshow(table.values, aspect="auto", cmap="YlGnBu", interpolation="nearest")
    ax.set_xticks(range(table.shape[1]))
    ax.set_yticks(range(table.shape[0]))
    ax.set_xticklabels(table.columns, rotation=45, ha="right")
    ax.set_yticklabels(table.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="count")

    max_value = table.values.max() if table.size else 0
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            value = int(table.iloc[i, j])
            color = "white" if max_value and value > max_value * 0.45 else "#1f2937"
            ax.text(j, i, value, ha="center", va="center", color=color, fontsize=10, fontweight="semibold")

    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close()


def plot_group_feature_heatmap(table: pd.DataFrame, title: str, out_file: Path, cmap: str = "RdYlBu_r") -> None:
    if table.empty:
        return

    fig_w = max(10, table.shape[1] * 0.35)
    fig_h = max(4, table.shape[0] * 0.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(table.values, aspect="auto", cmap=cmap, interpolation="nearest")
    ax.set_xticks(range(table.shape[1]))
    ax.set_yticks(range(table.shape[0]))
    ax.set_xticklabels(table.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticklabels(table.index, fontsize=9)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="z-score")

    plt.tight_layout()
    plt.savefig(out_file, dpi=150)
    plt.close()


def plot_feature_family_by_group(
    df: pd.DataFrame,
    group_col: str,
    feature_cols: list[str],
    title: str,
    out_file: Path,
) -> None:
    available_features = [feature for feature in feature_cols if feature in df.columns]
    if not available_features:
        return

    group_order = (
        df[group_col]
        .value_counts(dropna=False)
        .index
        .tolist()
    )

    numeric_features = [
        feature for feature in available_features
        if pd.to_numeric(df[feature], errors="coerce").notna().any()
    ]
    if not numeric_features:
        return

    n_features = len(numeric_features)
    n_cols = min(3, n_features)
    n_rows = math.ceil(n_features / n_cols)
    fig_w = max(12, n_cols * 5.0)
    fig_h = max(4, n_rows * 3.8)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_w, fig_h), squeeze=False)
    axes_flat = axes.ravel()
    cmap = plt.get_cmap("tab20")

    for idx, feature in enumerate(numeric_features):
        ax = axes_flat[idx]
        data = []
        labels = []

        for group_value in group_order:
            values = pd.to_numeric(
                df.loc[df[group_col] == group_value, feature],
                errors="coerce",
            ).dropna()
            if not values.empty:
                data.append(values.values)
                labels.append(str(group_value))

        if not data:
            ax.set_visible(False)
            continue

        boxplot_kwargs = {
            "patch_artist": True,
            "showfliers": False,
        }
        try:
            box = ax.boxplot(data, tick_labels=labels, **boxplot_kwargs)
        except TypeError:
            box = ax.boxplot(data, labels=labels, **boxplot_kwargs)

        for i, patch in enumerate(box["boxes"]):
            patch.set_facecolor(cmap(i % cmap.N))
            patch.set_alpha(0.7)

        ax.set_title(feature, fontsize=10)
        ax.set_ylabel("value")
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.tick_params(axis="x", labelrotation=35, labelsize=8)

    for idx in range(n_features, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle(title, fontsize=13)
    plt.tight_layout(rect=[0, 0, 1, 0.985])
    plt.savefig(out_file, dpi=150)
    plt.close()


def plot_feature_family_hist_by_group(
    df: pd.DataFrame,
    group_col: str,
    feature_cols: list[str],
    title: str,
    out_file: Path,
) -> None:
    available_features = [feature for feature in feature_cols if feature in df.columns]
    if not available_features:
        return

    group_order = (
        df[group_col]
        .value_counts(dropna=False)
        .index
        .tolist()
    )

    numeric_features = [
        feature for feature in available_features
        if pd.to_numeric(df[feature], errors="coerce").notna().any()
    ]
    if not numeric_features:
        return

    n_features = len(numeric_features)
    n_cols = min(3, n_features)
    n_rows = math.ceil(n_features / n_cols)
    fig_w = max(12, n_cols * 5.0)
    fig_h = max(4, n_rows * 3.8)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_w, fig_h), squeeze=False)
    axes_flat = axes.ravel()

    legend_handles = None
    legend_labels = None

    for idx, feature in enumerate(numeric_features):
        ax = axes_flat[idx]
        has_data = False

        for group_value in group_order:
            values = pd.to_numeric(
                df.loc[df[group_col] == group_value, feature],
                errors="coerce",
            ).dropna()
            if values.empty:
                continue

            has_data = True
            ax.hist(values.values, bins=20, alpha=0.35, label=str(group_value))

        if not has_data:
            ax.set_visible(False)
            continue

        if legend_handles is None:
            legend_handles, legend_labels = ax.get_legend_handles_labels()

        ax.set_title(feature, fontsize=10)
        ax.set_ylabel("frequency")
        ax.grid(axis="y", linestyle="--", alpha=0.35)

    for idx in range(n_features, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle(title, fontsize=13)
    if legend_handles and legend_labels:
        fig.legend(
            legend_handles,
            legend_labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.01),
            ncol=min(4, len(legend_labels)),
        )
        plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    else:
        plt.tight_layout(rect=[0, 0, 1, 0.985])
    plt.savefig(out_file, dpi=150)
    plt.close()


def write_markdown_report(
    out_file: Path,
    csv_path: Path,
    df: pd.DataFrame,
    missing_report: pd.DataFrame,
    classe_counts: pd.Series,
    numeric_cols: list[str],
) -> None:
    top_classe = classe_counts.index[0] if not classe_counts.empty else "N/A"
    top_classe_count = int(classe_counts.iloc[0]) if not classe_counts.empty else 0

    lines = []
    lines.append("# EDA Report - CSV")
    lines.append("")
    lines.append("## Data Source")
    lines.append(f"- CSV: {csv_path}")
    lines.append(f"- Total rows: {len(df)}")
    lines.append(f"- Total columns: {len(df.columns)}")
    lines.append("")

    lines.append("## Missing Values")
    lines.append(missing_report.to_markdown())
    lines.append("")

    lines.append("## Distribution of CLASSE")
    lines.append(classe_counts.rename("count").to_frame().to_markdown())
    lines.append("")
    lines.append(f"Top CLASSE: **{top_classe}** ({top_classe_count})")
    lines.append("")

    if numeric_cols:
        lines.append("## Numeric Features")
        lines.append(f"- {', '.join(numeric_cols)}")
        lines.append("- See `numeric_summary_overall.csv` and `numeric_summary_by_classe.csv`.")
        lines.append("")

    lines.append("## Z-score Interpretation")
    lines.append("The float-feature comparison heatmaps use z-score normalization per feature across groups.")
    lines.append("- z = (value - feature_mean) / feature_std")
    lines.append("- z > 0: group is above the feature average")
    lines.append("- z < 0: group is below the feature average")
    lines.append("- |z| indicates how far the group is from average in standard deviation units")
    lines.append("This allows fair comparison across features with different numeric scales.")
    lines.append("")

    lines.append("## Generated Artifacts")
    lines.append("- CSV: CLASSE distribution, missing report, and numeric summaries by CLASSE.")
    lines.append("- PNG (core): `bar_counts.png` for CLASSE counts and float-feature aggregated comparison heatmaps by CLASSE.")
    lines.append("- PNG (families): feature-family boxplots and `hist_family_*` histogram panels by CLASSE.")

    out_file.write_text("\n".join(lines), encoding="utf-8")


def _load_and_prepare_df(csv_path: Path, sep: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=sep)
    if df.empty:
        raise ValueError(f"Loaded CSV has no rows: {csv_path}")
    if "CLASSE" not in df.columns:
        raise ValueError(f"Missing required column 'CLASSE' in {csv_path}")
    df["CLASSE"] = df["CLASSE"].astype(str).str.strip()
    categorical_cols = {
        "IMG_FNAME",
        "ID_POLY",
        "SATELITE",
        "BEAM_MODE",
        "CLASSE",
        "UTM_ZONE",
        "FG_BG_KS_RES",
        "FG_BG_MW_RES",
    }
    for col in df.columns:
        if col not in categorical_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def run_shared_eda(csv_path: Path, shared_outdir: Path, sep: str) -> None:
    """Generate outputs that depend only on CLASSE labels (bit-depth independent).

    Class distribution and its bar chart are identical across all version CSVs
    (the same polygons are annotated regardless of image bit depth), so these
    are produced once and stored in a shared directory.
    """
    shared_outdir.mkdir(parents=True, exist_ok=True)
    df = _load_and_prepare_df(csv_path, sep)

    classe_counts = df["CLASSE"].value_counts(dropna=False)
    save_series(classe_counts, shared_outdir / "classe_counts.csv", "CLASSE")
    plot_counts_bars(classe_counts, shared_outdir / "bar_counts.png")

    print("\n=== CLASSE COUNTS ===")
    print(classe_counts)
    print(f"\n[INFO] Shared CLASSE outputs saved to: {shared_outdir.resolve()}")


def run_numeric_eda_for_csv(csv_path: Path, outdir: Path, sep: str) -> None:
    """Generate version-specific outputs that depend on floating-point values.

    Results differ between 8bits and 16bits due to numeric resolution differences,
    so each version gets its own output subdirectory.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    df = _load_and_prepare_df(csv_path, sep)

    print(f"\n=== {csv_path.name}: BASIC OVERVIEW ===")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    key_missing_cols = [col for col in ["CLASSE", "AREA_KM2", "PERIM_KM", "AREA_KM_DS", "PERIM_KM_DS"] if col in df.columns]
    missing_report = pd.DataFrame({
        "missing_count": df[key_missing_cols].isna().sum(),
        "missing_pct": (df[key_missing_cols].isna().mean() * 100).round(2),
    })
    missing_report.to_csv(outdir / "missing_report.csv")

    classe_counts = df["CLASSE"].value_counts(dropna=False)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if numeric_cols:
        numeric_summary_overall = df[numeric_cols].describe().transpose()
        numeric_summary_overall.index.name = "feature"
        numeric_summary_overall.to_csv(outdir / "numeric_summary_overall.csv")

        numeric_by_classe = df.groupby("CLASSE")[numeric_cols].agg(["count", "mean", "median", "std", "min", "max"])
        numeric_by_classe.to_csv(outdir / "numeric_summary_by_classe.csv")

    float_cols = df.select_dtypes(include=["float32", "float64"]).columns.tolist()
    excluded_prefixes = ("CENTR", "AREA", "PERIM")
    float_cols = [
        col for col in float_cols
        if not col.upper().startswith(excluded_prefixes)
    ]
    if float_cols:
        float_mean_by_classe = df.groupby("CLASSE")[float_cols].mean()

        float_mean_by_classe.to_csv(outdir / "float_mean_by_classe.csv")

        def zscore_col(col: pd.Series) -> pd.Series:
            std_val = col.std()
            if pd.isna(std_val) or std_val == 0:
                return pd.Series(0.0, index=col.index)
            return (col - col.mean()) / std_val

        float_mean_by_classe_z = float_mean_by_classe.apply(zscore_col, axis=0)

        float_mean_by_classe_z.to_csv(outdir / "float_mean_by_classe_zscore.csv")

        plot_group_feature_heatmap(
            float_mean_by_classe_z,
            "Floating-point feature means by CLASSE (z-score per feature)",
            outdir / "heatmap_float_means_by_classe_zscore.png",
        )

    feat_shape = [
        "COMPLEX_MEAS",
        "SPREAD",
        "SHP_FACT",
        "CIRCULARITY",
        "PERI_AREA_RATIO",
    ]
    feat_hu = sorted([col for col in df.columns if col.startswith("HU_")])
    feat_fg = sorted([col for col in df.columns if col.startswith("FG_") and not col.startswith("FG_BG_")])
    feat_bg = sorted([col for col in df.columns if col.startswith("BG_")])
    feat_fgbg = sorted([
        col for col in df.columns
        if col.startswith("FG_BG_") and pd.api.types.is_float_dtype(df[col])
    ])

    families = [
        ("shape", feat_shape),
        ("hu", feat_hu),
        ("fg", feat_fg),
        ("bg", feat_bg),
        ("fg_bg", feat_fgbg),
    ]

    for family_name, feature_list in families:
        plot_feature_family_by_group(
            df=df,
            group_col="CLASSE",
            feature_cols=feature_list,
            title=f"{family_name.upper()} features by CLASSE (original scale)",
            out_file=outdir / f"boxplot_family_{family_name}_by_classe.png",
        )
        plot_feature_family_hist_by_group(
            df=df,
            group_col="CLASSE",
            feature_cols=feature_list,
            title=f"{family_name.upper()} histograms by CLASSE (original scale)",
            out_file=outdir / f"hist_family_{family_name}_by_classe.png",
        )

    write_markdown_report(
        out_file=outdir / "EDA_summary.md",
        csv_path=csv_path,
        df=df,
        missing_report=missing_report,
        classe_counts=classe_counts,
        numeric_cols=numeric_cols,
    )

    print(f"\nNumeric EDA completed. Outputs saved to: {outdir.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "EDA for Oil_Stats CSV. "
            "CLASSE accounting outputs (class counts, bar chart) are written once to "
            "<outdir>/shared. Float/numeric analysis, which differs by bit depth, "
            "is written per version to <outdir>/<version> (e.g. 8bits, 16bits)."
        )
    )
    parser.add_argument("--csv", type=Path, default=None, help="Optional single CSV path. If omitted, process all versions in --csv-dir.")
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR, help="Directory containing Oil_Stats_*bits.csv files.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="Root output directory.")
    parser.add_argument("--sep", default=DEFAULT_SEP, help="CSV delimiter (default ';').")
    args = parser.parse_args()

    if args.csv is not None:
        csv_paths = [args.csv]
    else:
        csv_paths = _collect_version_csvs(args.csv_dir)
        if not csv_paths:
            raise FileNotFoundError(
                f"No Oil_Stats_*bits.csv files found in: {args.csv_dir}"
            )

    for csv_path in csv_paths:
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        if csv_path.stat().st_size == 0:
            raise ValueError(f"CSV exists but is empty: {csv_path}")

    # CLASSE accounting (shared, bit-depth independent) — generated once from the first CSV
    print(f"\n[INFO] Generating shared CLASSE accounting outputs from: {csv_paths[0].name}")
    run_shared_eda(csv_path=csv_paths[0], shared_outdir=args.outdir, sep=args.sep)

    # Float/numeric analysis (version-specific, one subdir per bit-depth)
    for csv_path in csv_paths:
        version_label = _version_label_from_csv(csv_path)
        version_outdir = args.outdir / version_label
        print(f"\n[INFO] Running numeric EDA for {csv_path.name} -> {version_outdir}")
        run_numeric_eda_for_csv(csv_path=csv_path, outdir=version_outdir, sep=args.sep)


if __name__ == "__main__":
    main()
