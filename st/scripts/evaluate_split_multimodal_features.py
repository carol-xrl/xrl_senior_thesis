#!/usr/bin/env python
"""Evaluate multimodal CPJUMP1 metrics with all/train/val/test query scopes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.evaluate import read_table, write_table
from st_benchmark.metadata import build_subset_metadata, load_config
from st_benchmark.split_multimodal import evaluate_split_multimodal_feature_dataframe
from st_benchmark.transforms import transformed_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True)
    parser.add_argument("--config", default="st/configs/subset_multimodal_short_20plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="features")
    parser.add_argument(
        "--input-transform",
        default="none",
        choices=[
            "none",
            "raw_l2",
            "global_zscore_l2",
            "plate_center_l2",
            "plate_zscore_l2",
            "negcon_center_l2",
            "negcon_zscore_l2",
        ],
    )
    parser.add_argument("--write-query-tables", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    features = read_table(args.features)
    if args.input_transform != "none":
        features = transformed_features(features, metadata, args.input_transform)

    results = evaluate_split_multimodal_feature_dataframe(
        features,
        metadata,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )
    summary_path = write_table(results["summary"], output_dir / f"{args.prefix}_split_multimodal_summary.csv")
    print(results["summary"].to_string(index=False), flush=True)
    print(f"summary: {summary_path}", flush=True)

    if args.write_query_tables:
        for name, table in results.items():
            if name in {"merged_features", "summary"}:
                continue
            write_table(table, output_dir / f"{args.prefix}_split_multimodal_{name}.csv")


if __name__ == "__main__":
    main()
