from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "AdditionalGraphs"
CSV_PATH = BASE_DIR / "image_model_metrics_all_runs.csv"


def _to_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _save(fig: plt.Figure, filename: str) -> str:
    path = OUT_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return filename


def _build_architecture_diagram() -> str:
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    boxes = [
        (0.8, 4.9, 2.2, 1.0, "Frontend\n(React)"),
        (3.6, 4.9, 2.4, 1.0, "FastAPI\nBackend"),
        (6.8, 6.2, 2.2, 1.0, "YOLO\nDetector"),
        (6.8, 4.9, 2.2, 1.0, "RoBERTa\nClassifier"),
        (6.8, 3.6, 2.2, 1.0, "Optional\nCLIP/Hybrid"),
        (3.6, 2.2, 2.4, 1.0, "Merged Results\nand Alerts"),
    ]

    for x, y, w, h, text in boxes:
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.3,
            edgecolor="#1f2937",
            facecolor="#dbeafe",
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10)

    arrows = [
        ((3.0, 5.4), (3.6, 5.4)),
        ((6.0, 5.4), (6.8, 6.7)),
        ((6.0, 5.4), (6.8, 5.4)),
        ((6.0, 5.4), (6.8, 4.1)),
        ((7.9, 6.2), (4.8, 3.2)),
        ((7.9, 4.9), (4.8, 3.2)),
        ((7.9, 3.6), (4.8, 3.2)),
        ((4.8, 2.2), (1.9, 4.9)),
    ]

    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=12, linewidth=1.2))

    ax.set_title("NaviAble High-Level System Architecture")
    return _save(fig, "09_system_architecture_diagram.png")


def _build_priority_matrix() -> str:
    fig, ax = plt.subplots(figsize=(9, 6))

    tasks = [
        (4.6, 2.8, "Collect more ramp/stairs images"),
        (4.1, 1.9, "Class-balanced training"),
        (3.2, 1.7, "Per-class confidence tuning"),
        (3.6, 2.2, "Hard-negative mining"),
        (2.4, 1.2, "Versioned evaluation tracking"),
    ]

    for impact, effort, label in tasks:
        ax.scatter(effort, impact, s=140, color="#2563eb", alpha=0.9)
        ax.text(effort + 0.04, impact + 0.04, label, fontsize=9)

    ax.axvline(2.0, color="#9ca3af", linestyle="--", linewidth=1)
    ax.axhline(3.0, color="#9ca3af", linestyle="--", linewidth=1)
    ax.text(0.45, 4.75, "High Impact / Low Effort", fontsize=9, color="#065f46")
    ax.text(2.55, 4.75, "High Impact / High Effort", fontsize=9, color="#7c2d12")
    ax.text(0.45, 0.35, "Low Impact / Low Effort", fontsize=9, color="#1f2937")
    ax.text(2.55, 0.35, "Low Impact / High Effort", fontsize=9, color="#1f2937")

    ax.set_xlim(0.5, 3.2)
    ax.set_ylim(0.7, 5.0)
    ax.set_xlabel("Implementation Effort")
    ax.set_ylabel("Expected Impact")
    ax.set_title("Improvement Priority Matrix")
    return _save(fig, "10_recommendation_priority_matrix.png")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing metrics CSV: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH).dropna(how="all")
    df = _to_numeric(
        df,
        [
            "epochs_recorded",
            "imgsz",
            "batch",
            "best_epoch_by_mAP50_95",
            "best_precision",
            "best_recall",
            "best_mAP50",
            "best_mAP50_95",
            "last_epoch",
            "last_precision",
            "last_recall",
            "last_mAP50",
            "last_mAP50_95",
        ],
    )

    df["run_short"] = (
        df["run"].astype(str)
        .str.replace("runs/detect/", "", regex=False)
        .str.replace("NaviAble_Final/", "F/", regex=False)
        .str.slice(0, 28)
    )

    generated: list[tuple[str, str]] = []

    # 01) Top runs by mAP50-95
    fig, ax = plt.subplots(figsize=(12, 6))
    top = df.sort_values("best_mAP50_95", ascending=False).head(12)
    ax.barh(top["run_short"][::-1], top["best_mAP50_95"][::-1], color="#3b82f6")
    ax.set_xlabel("Best mAP@0.50:0.95")
    ax.set_title("Top YOLO Runs by Best mAP@0.50:0.95")
    ax.grid(axis="x", alpha=0.25)
    generated.append(("01_top_runs_map50_95.png", _save(fig, "01_top_runs_map50_95.png")))

    # 02) Precision vs recall bubble chart
    fig, ax = plt.subplots(figsize=(8, 6))
    size = (df["best_mAP50"].fillna(0) * 600) + 40
    scatter = ax.scatter(
        df["best_recall"],
        df["best_precision"],
        s=size,
        c=df["best_mAP50_95"],
        cmap="viridis",
        alpha=0.85,
        edgecolor="black",
        linewidth=0.3,
    )
    ax.set_xlabel("Best Recall")
    ax.set_ylabel("Best Precision")
    ax.set_title("Precision vs Recall (bubble size = mAP@0.50)")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Best mAP@0.50:0.95")
    generated.append(("02_precision_recall_bubble.png", _save(fig, "02_precision_recall_bubble.png")))

    # 03) Distribution of key metrics
    metric_df = df[["best_precision", "best_recall", "best_mAP50", "best_mAP50_95"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.boxplot(
        [metric_df[c].dropna() for c in metric_df.columns],
        tick_labels=["Precision", "Recall", "mAP@0.50", "mAP@0.50:0.95"],
        patch_artist=True,
        boxprops={"facecolor": "#93c5fd"},
    )
    ax.set_ylabel("Score")
    ax.set_title("Distribution of Best Validation Metrics")
    ax.grid(axis="y", alpha=0.25)
    generated.append(("03_metric_distribution_boxplot.png", _save(fig, "03_metric_distribution_boxplot.png")))

    # 04) Correlation heatmap
    corr = metric_df.corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    labels = ["Precision", "Recall", "mAP@0.50", "mAP@0.50:0.95"]
    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title("Correlation Between Validation Metrics")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    generated.append(("04_metric_correlation_heatmap.png", _save(fig, "04_metric_correlation_heatmap.png")))

    # 05) Best vs last mAP delta
    fig, ax = plt.subplots(figsize=(12, 6))
    delta = df[["run_short", "best_mAP50_95", "last_mAP50_95"]].dropna().copy()
    delta["delta"] = delta["best_mAP50_95"] - delta["last_mAP50_95"]
    delta = delta.sort_values("delta", ascending=False).head(15)
    colors = ["#16a34a" if value >= 0 else "#dc2626" for value in delta["delta"]]
    ax.barh(delta["run_short"][::-1], delta["delta"][::-1], color=colors[::-1])
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Best mAP@0.50:0.95 - Last mAP@0.50:0.95")
    ax.set_title("Generalization Drift Near Training End")
    ax.grid(axis="x", alpha=0.25)
    generated.append(("05_best_vs_last_map_delta.png", _save(fig, "05_best_vs_last_map_delta.png")))

    # 06) Epoch efficiency vs performance
    epoch_df = df[["epochs_recorded", "best_epoch_by_mAP50_95", "best_mAP50_95"]].dropna().copy()
    epoch_df["efficiency"] = epoch_df["best_epoch_by_mAP50_95"] / epoch_df["epochs_recorded"]
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(
        epoch_df["efficiency"],
        epoch_df["best_mAP50_95"],
        c=epoch_df["epochs_recorded"],
        cmap="plasma",
        s=90,
        alpha=0.85,
        edgecolor="black",
        linewidth=0.3,
    )
    ax.set_xlabel("Best Epoch / Total Epochs")
    ax.set_ylabel("Best mAP@0.50:0.95")
    ax.set_title("Training Efficiency vs Performance")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Total Epochs")
    generated.append(("06_epoch_efficiency_scatter.png", _save(fig, "06_epoch_efficiency_scatter.png")))

    # 07) Optimizer comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    optimizer = df.groupby("optimizer", dropna=True)["best_mAP50_95"].mean().sort_values(ascending=False)
    ax.bar(optimizer.index.astype(str), optimizer.values, color="#f59e0b")
    ax.set_ylabel("Average Best mAP@0.50:0.95")
    ax.set_title("Optimizer Comparison")
    ax.grid(axis="y", alpha=0.25)
    generated.append(("07_optimizer_comparison.png", _save(fig, "07_optimizer_comparison.png")))

    # 08) Dataset configuration performance
    fig, ax = plt.subplots(figsize=(11, 5.5))
    data_perf = (
        df.groupby("data", dropna=True)["best_mAP50_95"]
        .mean()
        .sort_values(ascending=False)
        .head(12)
    )
    pretty_names = [Path(value).stem[:22] for value in data_perf.index.astype(str)]
    ax.barh(pretty_names[::-1], data_perf.values[::-1], color="#14b8a6")
    ax.set_xlabel("Average Best mAP@0.50:0.95")
    ax.set_title("Top Dataset Configurations by mAP@0.50:0.95")
    ax.grid(axis="x", alpha=0.25)
    generated.append(("08_dataset_config_comparison.png", _save(fig, "08_dataset_config_comparison.png")))

    # 09) Architecture diagram
    generated.append(("09_system_architecture_diagram.png", _build_architecture_diagram()))

    # 10) Priority matrix for suggested improvements
    generated.append(("10_recommendation_priority_matrix.png", _build_priority_matrix()))

    # Write markdown index in the same folder for easy Report linking.
    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Additional Graphs for NaviAble Report",
                "",
                "All figures in this folder are generated by `generate_additional_graphs.py`.",
                "",
                "## Generated Figures",
                "",
                "- `01_top_runs_map50_95.png`: Top 12 runs ranked by best mAP@0.50:0.95.",
                "- `02_precision_recall_bubble.png`: Precision-recall relationship (bubble size tracks mAP@0.50).",
                "- `03_metric_distribution_boxplot.png`: Distribution spread for precision, recall, mAP@0.50, and mAP@0.50:0.95.",
                "- `04_metric_correlation_heatmap.png`: Correlation matrix between core validation metrics.",
                "- `05_best_vs_last_map_delta.png`: Difference between best and last checkpoint mAP@0.50:0.95.",
                "- `06_epoch_efficiency_scatter.png`: Relationship between training efficiency and model quality.",
                "- `07_optimizer_comparison.png`: Average best mAP@0.50:0.95 per optimizer.",
                "- `08_dataset_config_comparison.png`: Average performance by dataset configuration file.",
                "- `09_system_architecture_diagram.png`: High-level frontend-backend-model architecture diagram.",
                "- `10_recommendation_priority_matrix.png`: Impact-vs-effort matrix for practical model improvements.",
                "",
                "## Extra Figure Ideas You Can Add",
                "",
                "1. Per-class confusion matrix from a final validation run (best for error analysis).",
                "2. PR curve per class from YOLO validation outputs (best for threshold selection).",
                "3. Latency breakdown by hardware target (CPU vs GPU vs edge device).",
                "4. Data drift timeline between training and newly collected field images.",
                "5. Failure-case gallery with short root-cause tags (lighting, occlusion, viewpoint).",
                "",
                "## Regenerate",
                "",
                "```bash",
                "python3 generate_additional_graphs.py",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Generated {len(generated)} figures in {OUT_DIR}")
    print(f"Figure descriptions: {readme}")


if __name__ == "__main__":
    main()

