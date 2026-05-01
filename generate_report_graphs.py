from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


base = Path(__file__).resolve().parent
out = base / "report_assets" / "figures"
out.mkdir(parents=True, exist_ok=True)

csv_path = base / "image_model_metrics_all_runs.csv"
df = pd.read_csv(csv_path).dropna(how="all")

num_cols = [
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
]
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

df["run_short"] = (
    df["run"].astype(str)
    .str.replace("runs/detect/", "", regex=False)
    .str.replace("NaviAble_Final/", "F/", regex=False)
    .str.slice(0, 28)
)

# 1) Top runs by mAP50-95
fig, ax = plt.subplots(figsize=(12, 6))
top = df.sort_values("best_mAP50_95", ascending=False).head(12)
ax.barh(top["run_short"][::-1], top["best_mAP50_95"][::-1], color="#4C78A8")
ax.set_xlabel("Best mAP50-95")
ax.set_title("Top YOLO Runs by Best mAP50-95")
ax.grid(axis="x", alpha=0.25)
fig.tight_layout()
fig.savefig(out / "fig_top_runs_map50_95.png", dpi=220)
plt.close(fig)

# 2) Precision vs Recall scatter
fig, ax = plt.subplots(figsize=(8, 6))
size = (df["best_mAP50"].fillna(0) * 600) + 40
sc = ax.scatter(
    df["best_recall"],
    df["best_precision"],
    s=size,
    c=df["best_mAP50_95"],
    cmap="viridis",
    alpha=0.8,
    edgecolor="black",
    linewidth=0.3,
)
ax.set_xlabel("Best Recall")
ax.set_ylabel("Best Precision")
ax.set_title("Precision vs Recall (Bubble size = mAP50)")
ax.grid(alpha=0.25)
cbar = fig.colorbar(sc, ax=ax)
cbar.set_label("Best mAP50-95")
fig.tight_layout()
fig.savefig(out / "fig_precision_recall_scatter.png", dpi=220)
plt.close(fig)

# 3) Distribution boxplot
fig, ax = plt.subplots(figsize=(9, 6))
metric_df = df[["best_precision", "best_recall", "best_mAP50", "best_mAP50_95"]]
ax.boxplot(
    [metric_df[c].dropna() for c in metric_df.columns],
    labels=["Precision", "Recall", "mAP50", "mAP50-95"],
    patch_artist=True,
    boxprops=dict(facecolor="#72B7B2"),
)
ax.set_ylabel("Score")
ax.set_title("Distribution of Best Validation Metrics Across Runs")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(out / "fig_metric_distribution_boxplot.png", dpi=220)
plt.close(fig)

# 4) Correlation heatmap
corr = metric_df.corr()
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr.columns)), corr.columns, rotation=30, ha="right")
ax.set_yticks(range(len(corr.columns)), corr.columns)
for i in range(corr.shape[0]):
    for j in range(corr.shape[1]):
        ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", color="black", fontsize=9)
ax.set_title("Correlation Between Best Metrics")
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
fig.tight_layout()
fig.savefig(out / "fig_metric_correlation_heatmap.png", dpi=220)
plt.close(fig)

# 5) Best vs last deltas
fig, ax = plt.subplots(figsize=(12, 6))
d = df[["run_short", "best_mAP50_95", "last_mAP50_95"]].dropna().copy()
d["delta"] = d["best_mAP50_95"] - d["last_mAP50_95"]
d = d.sort_values("delta", ascending=False).head(15)
colors = ["#54A24B" if x >= 0 else "#E45756" for x in d["delta"]]
ax.barh(d["run_short"][::-1], d["delta"][::-1], color=colors[::-1])
ax.axvline(0, color="black", linewidth=1)
ax.set_xlabel("Best mAP50-95 - Last mAP50-95")
ax.set_title("Generalization Drift at End of Training (Top 15 by Delta)")
ax.grid(axis="x", alpha=0.25)
fig.tight_layout()
fig.savefig(out / "fig_best_vs_last_map_delta.png", dpi=220)
plt.close(fig)

# 6) Epoch efficiency scatter
fig, ax = plt.subplots(figsize=(8, 6))
e = df[["epochs_recorded", "best_epoch_by_mAP50_95", "best_mAP50_95"]].dropna().copy()
e["efficiency"] = e["best_epoch_by_mAP50_95"] / e["epochs_recorded"]
sc = ax.scatter(
    e["efficiency"],
    e["best_mAP50_95"],
    c=e["epochs_recorded"],
    cmap="plasma",
    s=90,
    alpha=0.8,
    edgecolor="black",
    linewidth=0.3,
)
ax.set_xlabel("Best-Epoch / Total-Epoch Ratio")
ax.set_ylabel("Best mAP50-95")
ax.set_title("Training Efficiency vs Performance")
ax.grid(alpha=0.25)
cbar = fig.colorbar(sc, ax=ax)
cbar.set_label("Total Epochs")
fig.tight_layout()
fig.savefig(out / "fig_epoch_efficiency_scatter.png", dpi=220)
plt.close(fig)

# 7) Optimizer comparison
fig, ax = plt.subplots(figsize=(7, 5))
o = df.groupby("optimizer", dropna=True)["best_mAP50_95"].mean().sort_values(ascending=False)
ax.bar(o.index.astype(str), o.values, color="#F58518")
ax.set_ylabel("Average Best mAP50-95")
ax.set_title("Optimizer Comparison (Average Best mAP50-95)")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(out / "fig_optimizer_comparison.png", dpi=220)
plt.close(fig)

# 8) NLP reported metrics
nlp = {"Accuracy": 92.79, "Precision": 89.45, "Recall": 97.01, "F1-score": 93.08}
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(list(nlp.keys()), list(nlp.values()), color="#B279A2")
ax.set_ylim(80, 100)
ax.set_ylabel("Percentage (%)")
ax.set_title("NLP Integrity Model Metrics (Reported)")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(out / "fig_nlp_metrics_bar.png", dpi=220)
plt.close(fig)

print(f"Created {len(list(out.glob('*.png')))} figures in {out}")

