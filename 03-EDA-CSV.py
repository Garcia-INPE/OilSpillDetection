from pathlib import Path
import argparse
import math

import pandas as pd
import matplotlib.pyplot as plt


DEFAULT_CSV = Path("/home/jrmgarcia/ProjDocs/OilSpill/src/dataout/DS/CSV/Oil_Stats_16bits.csv")
DEFAULT_FALLBACK_CSV = Path("/home/jrmgarcia/ProjDocs/OilSpill/src/dataout/Oil_Stats_16bits.csv")
DEFAULT_OUTDIR = Path("dataout/EDA-CSV")
DEFAULT_SEP = ";"


def save_series(series: pd.Series, path: Path, index_name: str) -> None:
    out_df = series.rename("count").reset_index()
    out_df.columns = [index_name, "count"]
    out_df.to_csv(path, index=False)


def plot_bar(series: pd.Series, title: str, xlabel: str, ylabel: str, out_file: Path) -> None:
    plt.figure(figsize=(10, 5))
    ax = series.plot(kind="bar")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
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

        box = ax.boxplot(
            data,
            tick_labels=labels,
            patch_artist=True,
            showfliers=False,
        )

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


def write_markdown_report(
    out_file: Path,
    csv_path: Path,
    df: pd.DataFrame,
    missing_report: pd.DataFrame,
    classe_counts: pd.Series,
    subclasse_counts: pd.Series,
    crosstab_counts: pd.DataFrame,
    crosstab_row_pct: pd.DataFrame,
    subclass_multi_class: pd.Series,
    subclasse_pct: pd.Series,
    subclasse_class_pct: pd.DataFrame,
    dominant_class_by_subclasse: pd.DataFrame,
    numeric_cols: list[str],
) -> None:
    top_classe = classe_counts.index[0] if not classe_counts.empty else "N/A"
    top_classe_count = int(classe_counts.iloc[0]) if not classe_counts.empty else 0
    top_subclasse = subclasse_counts.index[0] if not subclasse_counts.empty else "N/A"
    top_subclasse_count = int(subclasse_counts.iloc[0]) if not subclasse_counts.empty else 0

    unique_subclasses_per_class = crosstab_counts.gt(0).sum(axis=1).sort_values(ascending=False)
    dominant_subclass_per_class = crosstab_row_pct.idxmax(axis=1)
    dominant_subclass_pct_per_class = crosstab_row_pct.max(axis=1)

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

    lines.append("## Distribution of SUBCLASSE")
    lines.append(subclasse_counts.rename("count").to_frame().to_markdown())
    lines.append("")
    lines.append("### SUBCLASSE Share (%)")
    lines.append(subclasse_pct.rename("pct").to_frame().to_markdown())
    lines.append("")
    lines.append(f"Top SUBCLASSE: **{top_subclasse}** ({top_subclasse_count})")
    lines.append("")

    lines.append("## CLASSE x SUBCLASSE")
    lines.append("### Counts")
    lines.append(crosstab_counts.to_markdown())
    lines.append("")
    lines.append("### Row Percentage (%)")
    lines.append(crosstab_row_pct.to_markdown())
    lines.append("")

    lines.append("## Differences Between CLASSE and SUBCLASSE")
    lines.append("### Number of SUBCLASSE represented inside each CLASSE")
    lines.append(unique_subclasses_per_class.rename("n_subclasses").to_frame().to_markdown())
    lines.append("")

    lines.append("### Dominant SUBCLASSE inside each CLASSE")
    dominant_table = pd.DataFrame({
        "dominant_subclasse": dominant_subclass_per_class,
        "row_pct": dominant_subclass_pct_per_class.round(2),
    })
    lines.append(dominant_table.to_markdown())
    lines.append("")

    lines.append("### SUBCLASSE association strength")
    lines.append("A value of 1 means a SUBCLASSE appears in only one CLASSE.")
    lines.append(subclass_multi_class.rename("num_classes").to_frame().to_markdown())
    lines.append("")
    lines.append("### CLASSE composition inside each SUBCLASSE (row %) ")
    lines.append(subclasse_class_pct.to_markdown())
    lines.append("")
    lines.append("### Dominant CLASSE per SUBCLASSE")
    lines.append(dominant_class_by_subclasse.to_markdown())
    lines.append("")

    if numeric_cols:
        lines.append("## Numeric Features")
        lines.append(f"- {', '.join(numeric_cols)}")
        lines.append("- See `numeric_summary_overall.csv`, `numeric_summary_by_classe.csv`, and `numeric_summary_by_classe_subclasse.csv`.")
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
    lines.append("- CSV: distributions, crosstabs, missing report, and numeric summaries.")
    lines.append("- PNG: class bars, top-subclass bars, crosstab heatmap, numeric boxplots by class, float-feature aggregated comparison heatmaps, and feature-family boxplots by CLASSE/SUBCLASSE.")

    out_file.write_text("\n".join(lines), encoding="utf-8")


def resolve_csv_path(csv_path: Path) -> Path:
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return csv_path

    if csv_path == DEFAULT_CSV and DEFAULT_FALLBACK_CSV.exists() and DEFAULT_FALLBACK_CSV.stat().st_size > 0:
        print(f"[INFO] Default CSV is empty or missing. Using fallback: {DEFAULT_FALLBACK_CSV}")
        return DEFAULT_FALLBACK_CSV

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    raise ValueError(f"CSV exists but is empty: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EDA for Oil_Stats CSV (focus on CLASSE vs SUBCLASSE).")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to input CSV file.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="Directory to save EDA outputs.")
    parser.add_argument("--sep", default=DEFAULT_SEP, help="CSV delimiter (default ';').")
    args = parser.parse_args()

    csv_path = resolve_csv_path(args.csv)
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, sep=args.sep)
    if df.empty:
        raise ValueError(f"Loaded CSV has no rows: {csv_path}")

    print("\n=== BASIC OVERVIEW ===")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    required_cols = ["CLASSE", "SUBCLASSE"]
    missing_required = [col for col in required_cols if col not in df.columns]
    if missing_required:
        raise ValueError(f"Missing required columns in CSV: {missing_required}")

    df["CLASSE"] = df["CLASSE"].astype(str).str.strip()
    df["SUBCLASSE"] = df["SUBCLASSE"].astype(str).str.strip()

    categorical_cols = {
        "IMG_FNAME",
        "ID_POLY",
        "SATELITE",
        "BEAM_MODE",
        "CLASSE",
        "SUBCLASSE",
        "UTM_ZONE",
        "FG_BG_KS_RES",
        "FG_BG_MW_RES",
    }
    for col in df.columns:
        if col not in categorical_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    key_missing_cols = [col for col in ["CLASSE", "SUBCLASSE", "AREA_KM2", "PERIM_KM", "AREA_KM_DS", "PERIM_KM_DS"] if col in df.columns]
    missing_report = pd.DataFrame({
        "missing_count": df[key_missing_cols].isna().sum(),
        "missing_pct": (df[key_missing_cols].isna().mean() * 100).round(2),
    })
    missing_report.to_csv(outdir / "missing_report.csv")

    classe_counts = df["CLASSE"].value_counts(dropna=False)
    subclasse_counts = df["SUBCLASSE"].value_counts(dropna=False)

    save_series(classe_counts, outdir / "classe_counts.csv", "CLASSE")
    save_series(subclasse_counts, outdir / "subclasse_counts.csv", "SUBCLASSE")

    print("\n=== CLASSE COUNTS ===")
    print(classe_counts)
    print("\n=== SUBCLASSE COUNTS ===")
    print(subclasse_counts)

    crosstab_counts = pd.crosstab(df["CLASSE"], df["SUBCLASSE"], dropna=False)
    crosstab_row_pct = pd.crosstab(df["CLASSE"], df["SUBCLASSE"], normalize="index", dropna=False).mul(100).round(2)

    crosstab_counts.to_csv(outdir / "classe_subclasse_crosstab_counts.csv")
    crosstab_row_pct.to_csv(outdir / "classe_subclasse_crosstab_rowpct.csv")

    print("\n=== CLASSE x SUBCLASSE (counts) ===")
    print(crosstab_counts)
    print("\n=== CLASSE x SUBCLASSE (row %) ===")
    print(crosstab_row_pct)

    subclass_multi_class = df.groupby("SUBCLASSE")["CLASSE"].nunique().sort_values(ascending=False)
    subclass_multi_class.to_csv(outdir / "subclasse_num_classes.csv", header=["num_classes"])

    subclasse_pct = (subclasse_counts / len(df) * 100).round(2)
    save_series(subclasse_pct, outdir / "subclasse_percentage.csv", "SUBCLASSE")

    subclasse_class_counts = pd.crosstab(df["SUBCLASSE"], df["CLASSE"], dropna=False)
    subclasse_class_pct = pd.crosstab(df["SUBCLASSE"], df["CLASSE"], normalize="index", dropna=False).mul(100).round(2)
    subclasse_class_counts.to_csv(outdir / "subclasse_classe_crosstab_counts.csv")
    subclasse_class_pct.to_csv(outdir / "subclasse_classe_crosstab_rowpct.csv")

    dominant_class_by_subclasse = pd.DataFrame({
        "dominant_classe": subclasse_class_pct.idxmax(axis=1),
        "dominant_pct": subclasse_class_pct.max(axis=1).round(2),
        "num_classes": subclass_multi_class,
        "total_count": subclasse_counts,
    }).sort_values(by=["dominant_pct", "total_count"], ascending=[False, False])
    dominant_class_by_subclasse.to_csv(outdir / "subclasse_dominant_classe.csv")

    print("\n=== SUBCLASSE SHARE (%) ===")
    print(subclasse_pct)
    print("\n=== DOMINANT CLASSE PER SUBCLASSE ===")
    print(dominant_class_by_subclasse)

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if numeric_cols:
        numeric_summary_overall = df[numeric_cols].describe().transpose()
        numeric_summary_overall.to_csv(outdir / "numeric_summary_overall.csv")

        numeric_by_classe = df.groupby("CLASSE")[numeric_cols].agg(["count", "mean", "median", "std", "min", "max"])
        numeric_by_subclasse = df.groupby(["CLASSE", "SUBCLASSE"])[numeric_cols].agg(["count", "mean", "median", "std", "min", "max"])
        numeric_by_subclasse_only = df.groupby("SUBCLASSE")[numeric_cols].agg(["count", "mean", "median", "std", "min", "max"])

        numeric_by_classe.to_csv(outdir / "numeric_summary_by_classe.csv")
        numeric_by_subclasse.to_csv(outdir / "numeric_summary_by_classe_subclasse.csv")
        numeric_by_subclasse_only.to_csv(outdir / "numeric_summary_by_subclasse.csv")

    float_cols = df.select_dtypes(include=["float32", "float64"]).columns.tolist()
    excluded_prefixes = ("CENTR", "AREA", "PERIM")
    float_cols = [
        col for col in float_cols
        if not col.upper().startswith(excluded_prefixes)
    ]
    if float_cols:
        float_mean_by_classe = df.groupby("CLASSE")[float_cols].mean()
        float_mean_by_subclasse = df.groupby("SUBCLASSE")[float_cols].mean()

        float_mean_by_classe.to_csv(outdir / "float_mean_by_classe.csv")
        float_mean_by_subclasse.to_csv(outdir / "float_mean_by_subclasse.csv")

        def zscore_col(col: pd.Series) -> pd.Series:
            std_val = col.std()
            if pd.isna(std_val) or std_val == 0:
                return pd.Series(0.0, index=col.index)
            return (col - col.mean()) / std_val

        float_mean_by_classe_z = float_mean_by_classe.apply(zscore_col, axis=0)
        float_mean_by_subclasse_z = float_mean_by_subclasse.apply(zscore_col, axis=0)

        float_mean_by_classe_z.to_csv(outdir / "float_mean_by_classe_zscore.csv")
        float_mean_by_subclasse_z.to_csv(outdir / "float_mean_by_subclasse_zscore.csv")

        plot_group_feature_heatmap(
            float_mean_by_classe_z,
            "Floating-point feature means by CLASSE (z-score per feature)",
            outdir / "heatmap_float_means_by_classe_zscore.png",
        )
        plot_group_feature_heatmap(
            float_mean_by_subclasse_z,
            "Floating-point feature means by SUBCLASSE (z-score per feature)",
            outdir / "heatmap_float_means_by_subclasse_zscore.png",
        )

    plot_bar(classe_counts, "Count of samples by CLASSE", "CLASSE", "Count", outdir / "bar_classe_counts.png")
    plot_bar(subclasse_counts.head(15), "Top 15 SUBCLASSE by count", "SUBCLASSE", "Count", outdir / "bar_subclasse_top15_counts.png")
    plot_heatmap(crosstab_counts, "CLASSE x SUBCLASSE (counts)", outdir / "heatmap_classe_subclasse_counts.png")

    top_subclasse = subclasse_counts.head(12).index
    subclasse_class_counts_top = subclasse_class_counts.loc[top_subclasse]
    ax = subclasse_class_counts_top.plot(kind="bar", stacked=True, figsize=(11, 6), colormap="Set2")
    ax.set_title("CLASSE composition inside top 12 SUBCLASSE")
    ax.set_xlabel("SUBCLASSE")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / "bar_subclasse_classe_composition_top12.png", dpi=150)
    plt.close()

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
        plot_feature_family_by_group(
            df=df,
            group_col="SUBCLASSE",
            feature_cols=feature_list,
            title=f"{family_name.upper()} features by SUBCLASSE (original scale)",
            out_file=outdir / f"boxplot_family_{family_name}_by_subclasse.png",
        )

    write_markdown_report(
        out_file=outdir / "EDA_summary.md",
        csv_path=csv_path,
        df=df,
        missing_report=missing_report,
        classe_counts=classe_counts,
        subclasse_counts=subclasse_counts,
        crosstab_counts=crosstab_counts,
        crosstab_row_pct=crosstab_row_pct,
        subclass_multi_class=subclass_multi_class,
        subclasse_pct=subclasse_pct,
        subclasse_class_pct=subclasse_class_pct,
        dominant_class_by_subclasse=dominant_class_by_subclasse,
        numeric_cols=numeric_cols,
    )

    print(f"\nEDA completed. Outputs saved to: {outdir.resolve()}")


if __name__ == "__main__":
    main()
