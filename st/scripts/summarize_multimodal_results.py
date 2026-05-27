#!/usr/bin/env python
"""Summarize multimodal 20-plate benchmark outputs into report tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


RUN_MARKER = "_multimodal_short_20plate_multimodal_"


def parse_run(directory_name: str) -> tuple[str, str]:
    """Parse model and transform from the standard 20-plate output directory."""
    if RUN_MARKER not in directory_name:
        return directory_name, ""
    model, transform = directory_name.split(RUN_MARKER, maxsplit=1)
    return model.replace("_", "-"), transform


def markdown_table(df: pd.DataFrame, float_digits: int = 4) -> str:
    if df.empty:
        return "_No completed multimodal result rows yet._"
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


def collect_summaries(metrics_root: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(metrics_root.glob("*multimodal_short_20plate_multimodal_*/*_summary.csv")):
        model, transform = parse_run(path.parent.name)
        frame = pd.read_csv(path)
        frame.insert(0, "model", model)
        frame.insert(1, "input_transform", transform)
        frame.insert(2, "run_dir", path.parent.name)
        rows.append(frame)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def compact_cross_modality(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    cross = summary[
        (summary["task"] == "cross_modality_matching")
        & (summary["metric"] == "cross_modality_matching")
    ].copy()
    keep = ["model", "input_transform", "condition", "cell", "modality", "mean_ap", "median_ap", "n_queries"]
    return cross[keep].sort_values(["model", "input_transform", "condition"]).reset_index(drop=True)


def compact_retrieval(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    retrieval = summary[
        (summary["task"] == "perturbation_retrieval")
        & (summary["metric"].isin(["replicate_retrieval", "negcon_challenge"]))
    ].copy()
    pivot = retrieval.pivot_table(
        index=["model", "input_transform", "condition", "cell", "modality"],
        columns="metric",
        values="mean_ap",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    return pivot.sort_values(["model", "input_transform", "condition"]).reset_index(drop=True)


def compact_within(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    within = summary[
        (summary["task"] == "within_modality_matching")
        & (summary["metric"] == "within_modality_matching")
    ].copy()
    keep = ["model", "input_transform", "condition", "cell", "modality", "mean_ap", "median_ap", "n_queries"]
    return within[keep].sort_values(["model", "input_transform", "condition"]).reset_index(drop=True)


def write_report(output_dir: Path, summary: pd.DataFrame) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "20plate_multimodal_summary_long.csv", index=False)

    cross = compact_cross_modality(summary)
    retrieval = compact_retrieval(summary)
    within = compact_within(summary)
    cross.to_csv(output_dir / "20plate_cross_modality_summary.csv", index=False)
    retrieval.to_csv(output_dir / "20plate_retrieval_summary.csv", index=False)
    within.to_csv(output_dir / "20plate_within_modality_summary.csv", index=False)

    report = "\n\n".join(
        [
            "# 20-Plate Multimodal Result Summary",
            "This report is generated from `evaluate_multimodal_features.py` outputs. It updates automatically when completed 20-plate runs are present under `st/outputs/metrics`.",
            "## Cross-Modality Matching",
            markdown_table(cross),
            "## Perturbation Retrieval",
            markdown_table(retrieval),
            "## Within-Modality Matching",
            markdown_table(within),
        ]
    )
    (output_dir / "20plate_multimodal_results_summary.md").write_text(report + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-root", default="st/outputs/metrics")
    parser.add_argument("--output-dir", default="st/reports/experiment_tables")
    args = parser.parse_args()

    summary = collect_summaries(Path(args.metrics_root))
    write_report(Path(args.output_dir), summary)
    print(f"multimodal rows: {len(summary)}")
    print(f"wrote {Path(args.output_dir) / '20plate_multimodal_results_summary.md'}")


if __name__ == "__main__":
    main()
