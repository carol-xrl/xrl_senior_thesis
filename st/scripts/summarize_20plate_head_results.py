#!/usr/bin/env python
"""Summarize 20-plate frozen and projection-head multimodal results."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


RUNS = {
    "frozen_B_plate_zscore": (
        "Frozen DINOv2-B/14 + plate z-score",
        "dinov2_vitb14_multimodal_short_20plate_multimodal_plate_zscore_l2/"
        "dinov2_vitb14_multimodal_short_20plate_plate_zscore_l2_summary.csv",
    ),
    "sample_proxy": (
        "Sample Proxy-CE head",
        "dinov2_vitb14_20plate_head_sample_proxy_plate_zscore_multimodal_raw_l2/"
        "dinov2_vitb14_20plate_sample_proxy_plate_zscore_raw_l2_summary.csv",
    ),
    "bio_target_proxy": (
        "Bio-target Proxy-CE head",
        "dinov2_vitb14_20plate_head_biotarget_proxy_plate_zscore_multimodal_raw_l2/"
        "dinov2_vitb14_20plate_biotarget_proxy_plate_zscore_raw_l2_summary.csv",
    ),
}

KEY_CONDITIONS = [
    ("A549_compound", "replicate_retrieval"),
    ("U2OS_compound", "replicate_retrieval"),
    ("A549_crispr", "replicate_retrieval"),
    ("U2OS_crispr", "replicate_retrieval"),
    ("A549_orf", "replicate_retrieval"),
    ("U2OS_orf", "replicate_retrieval"),
    ("A549_compound_to_crispr", "cross_modality_matching"),
    ("A549_compound_to_orf", "cross_modality_matching"),
    ("U2OS_compound_to_crispr", "cross_modality_matching"),
    ("U2OS_compound_to_orf", "cross_modality_matching"),
]


def read_run(metrics_root: Path, run_key: str, label: str, relative_path: str) -> pd.DataFrame:
    path = metrics_root / relative_path
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame.insert(0, "run", run_key)
    frame.insert(1, "run_label", label)
    return frame


def build_key_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition, metric in KEY_CONDITIONS:
        for run_key, (label, _) in RUNS.items():
            match = summary[
                (summary["run"] == run_key)
                & (summary["condition"] == condition)
                & (summary["metric"] == metric)
            ]
            if match.empty:
                value = float("nan")
                n_queries = 0
            else:
                value = float(match["mean_ap"].iloc[0])
                n_queries = int(match["n_queries"].iloc[0])
            rows.append(
                {
                    "condition": condition,
                    "metric": metric,
                    "run": run_key,
                    "run_label": label,
                    "mean_ap": value,
                    "n_queries": n_queries,
                }
            )
    return pd.DataFrame(rows)


def write_markdown(summary: pd.DataFrame, key_table: pd.DataFrame, output_dir: Path) -> None:
    pivot = key_table.pivot(index=["condition", "metric"], columns="run", values="mean_ap").reset_index()
    pivot = pivot.rename(
        columns={
            "frozen_B_plate_zscore": "frozen_B_plate_zscore_AP",
            "sample_proxy": "sample_proxy_AP",
            "bio_target_proxy": "bio_target_proxy_AP",
        }
    )
    for col in pivot.columns:
        if col.endswith("_AP"):
            pivot[col] = pivot[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    table_lines = [
        "| " + " | ".join(pivot.columns) + " |",
        "| " + " | ".join(["---"] * len(pivot.columns)) + " |",
    ]
    for _, row in pivot.iterrows():
        table_lines.append("| " + " | ".join(str(row[col]) for col in pivot.columns) + " |")

    lines = [
        "# 20-Plate Projection-Head Result Summary",
        "",
        "This table compares the strongest frozen DINOv2-B/14 baseline with two projection-head adaptations.",
        "",
        "- Sample Proxy-CE uses exact perturbation/sample identifiers as labels and is intended to improve replicate retrieval.",
        "- Bio-target Proxy-CE uses compound target genes and ORF/CRISPR perturbation genes as labels. It is an annotation-supervised upper bound for cross-modality matching, not a label-free baseline.",
        "",
        "## Key Metrics",
        "",
        "\n".join(table_lines),
        "",
        "## Interpretation",
        "",
        "- Sample Proxy-CE strongly improves compound and CRISPR replicate retrieval, but does not improve cross-modality matching.",
        "- Bio-target Proxy-CE strongly improves cross-modality matching because it directly trains on shared target/gene labels.",
        "- These two heads answer different questions: perturbation identity supervision versus biological target supervision.",
        "",
    ]
    (output_dir / "20plate_projection_head_results_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-root", default="st/outputs/metrics")
    parser.add_argument("--output-dir", default="st/reports/experiment_tables")
    args = parser.parse_args()

    metrics_root = Path(args.metrics_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = pd.concat(
        [read_run(metrics_root, run_key, label, relpath) for run_key, (label, relpath) in RUNS.items()],
        ignore_index=True,
    )
    key_table = build_key_table(summary)

    summary.to_csv(output_dir / "20plate_projection_head_summary_long.csv", index=False)
    key_table.to_csv(output_dir / "20plate_projection_head_key_metrics.csv", index=False)
    write_markdown(summary, key_table, output_dir)
    print(f"wrote {output_dir / '20plate_projection_head_results_summary.md'}")


if __name__ == "__main__":
    main()
