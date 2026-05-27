#!/usr/bin/env python
"""Summarize completed 8-plate U2OS compound experiments into paper tables."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd


FROZEN_RUNS = [
    {
        "model": "DINOv2-S/14",
        "summary": "dinov2_vits14_u2os_compound_8plate/dinov2_vits14_u2os_compound_8plate_summary.csv",
        "transforms": "dinov2_vits14_u2os_compound_8plate_transforms/dinov2_vits14_u2os_compound_8plate_transform_comparison.csv",
        "split": "dinov2_vits14_u2os_compound_8plate_split/dinov2_vits14_u2os_compound_8plate_split_retrieval_summary.csv",
    },
    {
        "model": "DINOv2-B/14",
        "summary": "dinov2_vitb14_u2os_compound_8plate/dinov2_vitb14_u2os_compound_8plate_summary.csv",
        "transforms": "dinov2_vitb14_u2os_compound_8plate_transforms/dinov2_vitb14_u2os_compound_8plate_transform_comparison.csv",
        "split": "dinov2_vitb14_u2os_compound_8plate_split/dinov2_vitb14_u2os_compound_8plate_split_retrieval_summary.csv",
    },
    {
        "model": "DINOv2-L/14",
        "summary": "dinov2_vitl14_u2os_compound_8plate/dinov2_vitl14_u2os_compound_8plate_summary.csv",
        "transforms": "dinov2_vitl14_u2os_compound_8plate_transforms/dinov2_vitl14_u2os_compound_8plate_transform_comparison.csv",
        "split": "dinov2_vitl14_u2os_compound_8plate_split/dinov2_vitl14_u2os_compound_8plate_raw_split_retrieval_summary.csv",
    },
]


HEAD_RUNS = [
    {
        "model": "DINOv2-S/14",
        "loss": "SupCon",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vits14_8plate_supcon_plate_zscore",
        "dir": "train_head_dinov2_vits14_8plate_supcon_plate_zscore",
    },
    {
        "model": "DINOv2-S/14",
        "loss": "Proxy-CE",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vits14_8plate_proxy_ce_plate_zscore",
        "dir": "train_head_dinov2_vits14_8plate_proxy_ce_plate_zscore",
    },
    {
        "model": "DINOv2-S/14",
        "loss": "SupCon",
        "input_transform": "negcon_zscore_l2",
        "prefix": "dinov2_vits14_8plate_supcon_negcon_zscore",
        "dir": "train_head_dinov2_vits14_8plate_supcon_negcon_zscore",
    },
    {
        "model": "DINOv2-S/14",
        "loss": "SupCon",
        "input_transform": "raw_l2",
        "prefix": "dinov2_vits14_8plate_supcon_raw_l2",
        "dir": "train_head_dinov2_vits14_8plate_supcon_raw_l2",
    },
    {
        "model": "DINOv2-S/14",
        "loss": "Triplet",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vits14_8plate_triplet_plate_zscore",
        "dir": "train_head_dinov2_vits14_8plate_triplet_plate_zscore",
    },
    {
        "model": "DINOv2-B/14",
        "loss": "SupCon",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vitb14_supcon_plate_zscore",
        "dir": "dinov2_vitb14_u2os_compound_8plate_head_supcon_plate_zscore",
    },
    {
        "model": "DINOv2-B/14",
        "loss": "Proxy-CE",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vitb14_proxy_plate_zscore",
        "dir": "dinov2_vitb14_u2os_compound_8plate_head_proxy_plate_zscore",
    },
    {
        "model": "DINOv2-L/14",
        "loss": "SupCon",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vitl14_supcon_plate_zscore",
        "dir": "dinov2_vitl14_u2os_compound_8plate_head_supcon_plate_zscore",
    },
    {
        "model": "DINOv2-L/14",
        "loss": "Proxy-CE",
        "input_transform": "plate_zscore_l2",
        "prefix": "dinov2_vitl14_proxy_plate_zscore",
        "dir": "dinov2_vitl14_u2os_compound_8plate_head_proxy_plate_zscore",
    },
]


METRIC_COLUMNS = {
    "replicate_retrieval": "full_replicate_ap",
    "negcon_challenge": "full_negcon_ap",
    "target_retrieval": "target_ap",
}


def read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def metric_value(summary: pd.DataFrame | None, metric: str) -> float:
    if summary is None or summary.empty:
        return np.nan
    match = summary[summary["metric"] == metric]
    if match.empty:
        return np.nan
    return float(match["mean_ap"].iloc[0])


def split_value(split: pd.DataFrame | None, scope: str, metric: str) -> float:
    if split is None or split.empty:
        return np.nan
    match = split[(split["scope"] == scope) & (split["metric"] == metric)]
    if match.empty:
        return np.nan
    return float(match["mean_ap"].iloc[0])


def best_val(history: pd.DataFrame | None) -> float:
    if history is None or "val_replicate_map" not in history:
        return np.nan
    return float(history["val_replicate_map"].max())


def collect_frozen(metrics_root: Path) -> pd.DataFrame:
    rows = []
    for run in FROZEN_RUNS:
        summary = read_csv(metrics_root / run["summary"])
        split = read_csv(metrics_root / run["split"])
        row = {
            "model": run["model"],
            "feature_type": "frozen raw",
            "input_transform": "none",
            "test_replicate_ap": split_value(split, "test_queries", "replicate_retrieval"),
            "test_negcon_ap": split_value(split, "test_queries", "negcon_challenge"),
        }
        for metric, col in METRIC_COLUMNS.items():
            row[col] = metric_value(summary, metric)
        rows.append(row)
    return pd.DataFrame(rows)


def collect_transforms(metrics_root: Path) -> pd.DataFrame:
    rows = []
    for run in FROZEN_RUNS:
        transforms = read_csv(metrics_root / run["transforms"])
        if transforms is None:
            continue
        for variant, frame in transforms.groupby("variant", sort=False):
            row = {"model": run["model"], "input_transform": variant}
            for metric, col in METRIC_COLUMNS.items():
                row[col] = metric_value(frame, metric)
            rows.append(row)
    return pd.DataFrame(rows)


def collect_heads(metrics_root: Path) -> pd.DataFrame:
    rows = []
    for run in HEAD_RUNS:
        base = metrics_root / run["dir"]
        prefix = run["prefix"]
        summary = read_csv(base / f"{prefix}_summary.csv")
        split = read_csv(base / f"{prefix}_split_retrieval_summary.csv")
        history = read_csv(base / f"{prefix}_train_history.csv")
        row = {
            "model": run["model"],
            "loss": run["loss"],
            "input_transform": run["input_transform"],
            "best_val_replicate_ap": best_val(history),
            "test_replicate_ap": split_value(split, "test_queries", "replicate_retrieval"),
            "test_negcon_ap": split_value(split, "test_queries", "negcon_challenge"),
        }
        for metric, col in METRIC_COLUMNS.items():
            row[col] = metric_value(summary, metric)
        rows.append(row)
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, float_digits: int = 4) -> str:
    if df.empty:
        return "_No rows._"
    formatted = df.copy()
    for col in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[col]):
            formatted[col] = formatted[col].map(lambda value: "" if pd.isna(value) else f"{value:.{float_digits}f}")
    columns = list(formatted.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in formatted.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def prepare_matplotlib(output_dir: Path) -> None:
    cache_dir = output_dir / ".matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))


def plot_projection_heads(heads: pd.DataFrame, output_dir: Path) -> Path:
    prepare_matplotlib(output_dir)
    import matplotlib.pyplot as plt

    frame = heads.sort_values("test_replicate_ap", ascending=True).copy()
    frame["label"] = frame["model"] + " " + frame["loss"] + " (" + frame["input_transform"] + ")"

    fig_height = max(4.8, 0.42 * len(frame) + 1.2)
    fig, ax = plt.subplots(figsize=(9.5, fig_height))
    colors = ["#4C78A8" if loss == "Proxy-CE" else "#72B7B2" if loss == "SupCon" else "#E45756" for loss in frame["loss"]]
    bars = ax.barh(frame["label"], frame["test_replicate_ap"], color=colors)
    for bar, value in zip(bars, frame["test_replicate_ap"], strict=True):
        ax.text(value + 0.006, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=8)
    ax.set_xlabel("Held-out test replicate AP")
    ax.set_ylabel("")
    ax.set_xlim(0, max(0.36, float(frame["test_replicate_ap"].max()) + 0.04))
    ax.set_title("8-plate projection-head ablation")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    path = output_dir / "8plate_projection_head_ablation.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_normalization(transforms: pd.DataFrame, output_dir: Path) -> Path:
    prepare_matplotlib(output_dir)
    import matplotlib.pyplot as plt

    variants = ["raw_l2", "global_zscore_l2", "plate_zscore_l2", "negcon_zscore_l2"]
    frame = transforms[transforms["input_transform"].isin(variants)].copy()
    frame["label"] = frame["model"] + "\n" + frame["input_transform"].str.replace("_", " ", regex=False)
    frame["order_model"] = frame["model"].map({"DINOv2-S/14": 0, "DINOv2-B/14": 1, "DINOv2-L/14": 2})
    frame["order_variant"] = frame["input_transform"].map({variant: idx for idx, variant in enumerate(variants)})
    frame = frame.sort_values(["order_model", "order_variant"])

    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(len(frame))
    width = 0.26
    metrics = [
        ("full_replicate_ap", "Replicate", "#4C78A8"),
        ("full_negcon_ap", "Negcon", "#54A24B"),
        ("target_ap", "Target", "#E45756"),
    ]
    offsets = [-width, 0, width]
    for offset, (column, label, color) in zip(offsets, metrics, strict=True):
        ax.bar(x + offset, frame[column], width=width, label=label, color=color)

    ax.set_ylabel("Mean AP")
    ax.set_title("8-plate frozen-feature normalization ablation")
    ax.set_xticks(x)
    ax.set_xticklabels(frame["label"], rotation=35, ha="right", fontsize=8)
    ax.set_ylim(0, max(0.42, float(frame[["full_replicate_ap", "full_negcon_ap", "target_ap"]].max().max()) + 0.05))
    ax.legend(frameon=False, ncols=3, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    path = output_dir / "8plate_normalization_ablation.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def write_outputs(output_dir: Path, frozen: pd.DataFrame, transforms: pd.DataFrame, heads: pd.DataFrame) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    frozen.to_csv(output_dir / "8plate_frozen_backbones.csv", index=False)
    transforms.to_csv(output_dir / "8plate_normalization_ablation.csv", index=False)
    heads.to_csv(output_dir / "8plate_projection_head_ablation.csv", index=False)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    plot_normalization(transforms, figure_dir)
    plot_projection_heads(heads, figure_dir)

    best_heads = heads.sort_values("test_replicate_ap", ascending=False).reset_index(drop=True)
    best_transforms = (
        transforms.sort_values(["model", "full_replicate_ap"], ascending=[True, False])
        .groupby("model", as_index=False)
        .head(2)
        .reset_index(drop=True)
    )

    report = "\n\n".join(
        [
            "# 8-Plate U2OS Compound Result Summary",
            "These tables summarize completed 24h+48h U2OS compound experiments. Test metrics use held-out test plates when available; full metrics use all query wells.",
            "## Frozen Backbones",
            markdown_table(frozen),
            "## Best Normalization Variants Per Backbone",
            markdown_table(best_transforms),
            "## Projection-Head Ablation",
            markdown_table(best_heads),
        ]
    )
    (output_dir / "8plate_results_summary.md").write_text(report + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-root", default="st/outputs/metrics")
    parser.add_argument("--output-dir", default="st/reports/experiment_tables")
    args = parser.parse_args()

    metrics_root = Path(args.metrics_root)
    output_dir = Path(args.output_dir)
    frozen = collect_frozen(metrics_root)
    transforms = collect_transforms(metrics_root)
    heads = collect_heads(metrics_root)
    write_outputs(output_dir, frozen, transforms, heads)
    print(f"wrote {output_dir / '8plate_results_summary.md'}")
    print(markdown_table(heads.sort_values("test_replicate_ap", ascending=False).head(5)))


if __name__ == "__main__":
    main()
