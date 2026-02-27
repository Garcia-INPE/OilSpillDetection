from pathlib import Path
import argparse

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt


DEFAULT_SHP = Path("/home/jrmgarcia/ProjData/Oil_Spill/Cantarell_Beisl/Vetores/Oil_slick/OilSlicks_Cantarell_GEOG_18052022_01.shp")
DEFAULT_OUTDIR = Path("dataout/EDA-Vectors")


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


def write_markdown_report(
    out_file: Path,
    shp_path: Path,
    gdf: gpd.GeoDataFrame,
    missing_report: pd.DataFrame,
    classe_counts: pd.Series,
    subclasse_counts: pd.Series,
    crosstab_counts: pd.DataFrame,
    crosstab_row_pct: pd.DataFrame,
    subclass_multi_class: pd.Series,
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
    lines.append("# EDA Report - Vector Shapefile")
    lines.append("")
    lines.append("## Data Source")
    lines.append(f"- Shapefile: {shp_path}")
    lines.append(f"- Total rows: {len(gdf)}")
    lines.append(f"- Total columns: {len(gdf.columns)}")
    lines.append(f"- CRS: {gdf.crs}")
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

    if numeric_cols:
        lines.append("## Numeric Features Available")
        lines.append(f"- {', '.join(numeric_cols)}")
        lines.append("- See CSV files: `numeric_summary_by_classe.csv` and `numeric_summary_by_classe_subclasse.csv`.")
        lines.append("")

    lines.append("## Generated Artifacts")
    lines.append("- CSV: missing report, classe/subclasse counts, crosstabs, and association metrics.")
    lines.append("- PNG: class bars, top-subclass bars, crosstab heatmap, and optional numeric boxplots.")

    out_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="EDA for vector shapefile (focus on CLASSE and SUBCLASSE).")
    parser.add_argument("--shp", type=Path, default=DEFAULT_SHP, help="Path to input shapefile.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="Directory to save EDA outputs.")
    args = parser.parse_args()

    shp_path = args.shp
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if not shp_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shp_path}")

    gdf = gpd.read_file(shp_path)

    print("\n=== BASIC OVERVIEW ===")
    print(f"Rows: {len(gdf)}")
    print(f"Columns: {len(gdf.columns)}")
    print(f"CRS: {gdf.crs}")
    print("Geometry types:")
    print(gdf.geometry.geom_type.value_counts(dropna=False))

    required_cols = ["CLASSE", "SUBCLASSE"]
    missing_required = [col for col in required_cols if col not in gdf.columns]
    if missing_required:
        raise ValueError(f"Missing required columns in shapefile: {missing_required}")

    df = gdf.copy()
    df["CLASSE"] = df["CLASSE"].astype(str).str.strip()
    df["SUBCLASSE"] = df["SUBCLASSE"].astype(str).str.strip()

    missing_report = pd.DataFrame({
        "missing_count": df[["CLASSE", "SUBCLASSE", "geometry"]].isna().sum(),
        "missing_pct": (df[["CLASSE", "SUBCLASSE", "geometry"]].isna().mean() * 100).round(2),
    })
    missing_report.to_csv(outdir / "missing_report.csv")

    classe_counts = df["CLASSE"].value_counts(dropna=False)
    subclasse_counts = df["SUBCLASSE"].value_counts(dropna=False)

    print("\n=== CLASSE COUNTS ===")
    print(classe_counts)
    print("\n=== SUBCLASSE COUNTS ===")
    print(subclasse_counts)

    save_series(classe_counts, outdir / "classe_counts.csv", "CLASSE")
    save_series(subclasse_counts, outdir / "subclasse_counts.csv", "SUBCLASSE")

    crosstab_counts = pd.crosstab(df["CLASSE"], df["SUBCLASSE"], dropna=False)
    crosstab_row_pct = pd.crosstab(
        df["CLASSE"],
        df["SUBCLASSE"],
        normalize="index",
        dropna=False,
    ).mul(100).round(2)

    crosstab_counts.to_csv(outdir / "classe_subclasse_crosstab_counts.csv")
    crosstab_row_pct.to_csv(outdir / "classe_subclasse_crosstab_rowpct.csv")

    print("\n=== CLASSE x SUBCLASSE (counts) ===")
    print(crosstab_counts)
    print("\n=== CLASSE x SUBCLASSE (row %) ===")
    print(crosstab_row_pct)

    subclass_multi_class = (
        df.groupby("SUBCLASSE")["CLASSE"]
        .nunique()
        .sort_values(ascending=False)
    )
    subclass_multi_class.to_csv(outdir / "subclasse_num_classes.csv", header=["num_classes"])

    print("\n=== SUBCLASSE ASSOCIATION STRENGTH ===")
    print("Number of distinct CLASSE per SUBCLASSE (1 means strongly tied to one class):")
    print(subclass_multi_class)

    numeric_candidates = ["AREA_KM", "PERIM_KM"]
    numeric_cols = [col for col in numeric_candidates if col in df.columns]
    if numeric_cols:
        numeric_by_classe = df.groupby("CLASSE")[numeric_cols].agg(["count", "mean", "median", "std", "min", "max"])
        numeric_by_subclasse = df.groupby(["CLASSE", "SUBCLASSE"])[numeric_cols].agg(["count", "mean", "median", "std", "min", "max"])

        numeric_by_classe.to_csv(outdir / "numeric_summary_by_classe.csv")
        numeric_by_subclasse.to_csv(outdir / "numeric_summary_by_classe_subclasse.csv")

        print("\n=== NUMERIC SUMMARY BY CLASSE ===")
        print(numeric_by_classe)

        for col in numeric_cols:
            plt.figure(figsize=(10, 5))
            df.boxplot(column=col, by="CLASSE", rot=45)
            plt.title(f"{col} by CLASSE")
            plt.suptitle("")
            plt.xlabel("CLASSE")
            plt.ylabel(col)
            plt.tight_layout()
            plt.savefig(outdir / f"boxplot_{col.lower()}_by_classe.png", dpi=150)
            plt.close()

    plot_bar(classe_counts, "Count of samples by CLASSE", "CLASSE", "Count", outdir / "bar_classe_counts.png")
    top_subclasse = subclasse_counts.head(15)
    plot_bar(top_subclasse, "Top 15 SUBCLASSE by count", "SUBCLASSE", "Count", outdir / "bar_subclasse_top15_counts.png")
    plot_heatmap(crosstab_counts, "CLASSE x SUBCLASSE (counts)", outdir / "heatmap_classe_subclasse_counts.png")

    write_markdown_report(
        out_file=outdir / "EDA_summary.md",
        shp_path=shp_path,
        gdf=gdf,
        missing_report=missing_report,
        classe_counts=classe_counts,
        subclasse_counts=subclasse_counts,
        crosstab_counts=crosstab_counts,
        crosstab_row_pct=crosstab_row_pct,
        subclass_multi_class=subclass_multi_class,
        numeric_cols=numeric_cols,
    )

    print(f"\nEDA completed. Outputs saved to: {outdir.resolve()}")


if __name__ == "__main__":
    main()
