#!/usr/bin/env python
"""Evaluate feature tables on condition-aware multimodal CPJUMP1 metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.evaluate import read_table, write_table
from st_benchmark.metadata import build_subset_metadata, load_config
from st_benchmark.multimodal import evaluate_multimodal_feature_dataframe
from st_benchmark.transforms import transformed_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True)
    parser.add_argument("--config", default="st/configs/subset_multimodal_short_20plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="features")
    parser.add_argument("--input-transform", default="raw_l2")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    features = read_table(args.features)
    if args.input_transform:
        features = transformed_features(features, metadata, args.input_transform)

    results = evaluate_multimodal_feature_dataframe(
        features,
        metadata,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )
    for name, table in results.items():
        if name == "merged_features":
            continue
        write_table(table, output_dir / f"{args.prefix}_{name}.csv")

    print(results["summary"].to_string(index=False), flush=True)
    print(f"outputs: {output_dir}", flush=True)


if __name__ == "__main__":
    main()
