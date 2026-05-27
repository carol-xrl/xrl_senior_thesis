#!/usr/bin/env python
"""Evaluate normalization and plate-correction variants for a feature table."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.evaluate import evaluate_feature_dataframe, read_table, write_table
from st_benchmark.metadata import build_subset_metadata, load_config
from st_benchmark.transforms import transformed_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="features")
    parser.add_argument(
        "--variants",
        nargs="*",
        default=[
            "raw_l2",
            "global_zscore_l2",
            "plate_center_l2",
            "plate_zscore_l2",
            "negcon_center_l2",
            "negcon_zscore_l2",
        ],
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    output_dir = Path(args.output_dir)
    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    features = read_table(args.features)

    summary_rows = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for variant in args.variants:
        print(f"evaluating {variant}", flush=True)
        transformed = transformed_features(features, metadata, variant)
        results = evaluate_feature_dataframe(
            transformed,
            metadata,
            min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
        )
        variant_dir = output_dir / variant
        variant_dir.mkdir(parents=True, exist_ok=True)
        write_table(results["summary"], variant_dir / f"{args.prefix}_{variant}_summary.csv")
        write_table(results["artifact"], variant_dir / f"{args.prefix}_{variant}_artifact_sensitivity.csv")
        summary = results["summary"].copy()
        summary.insert(0, "variant", variant)
        summary_rows.append(summary)

    comparison = pd.concat(summary_rows, ignore_index=True)
    comparison_path = output_dir / f"{args.prefix}_transform_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    print(comparison.to_string(index=False), flush=True)
    print(f"comparison: {comparison_path}", flush=True)


if __name__ == "__main__":
    main()
