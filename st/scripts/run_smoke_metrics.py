#!/usr/bin/env python
"""Run benchmark metrics on synthetic features for a local smoke test."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.metadata import build_subset_metadata, load_config
from st_benchmark.metrics import (
    artifact_sensitivity,
    negcon_challenge,
    replicate_retrieval,
    summarize_metric,
    target_retrieval,
)
from st_benchmark.synthetic import generate_synthetic_features


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"wrote {path} ({len(df)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="st/outputs/metrics/smoke")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    output_dir = repo_root / args.output_dir
    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    features = generate_synthetic_features(metadata, config["smoke"])

    write_csv(features, output_dir / "synthetic_features.csv")

    replicate = replicate_retrieval(
        features,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )
    negcon = negcon_challenge(
        features,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )
    target = target_retrieval(
        features,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )
    artifact = artifact_sensitivity(features)

    write_csv(replicate.query_scores, output_dir / "replicate_query_ap.csv")
    write_csv(replicate.aggregate_scores, output_dir / "replicate_map.csv")
    write_csv(negcon.query_scores, output_dir / "negcon_query_ap.csv")
    write_csv(negcon.aggregate_scores, output_dir / "negcon_map.csv")
    write_csv(target.query_scores, output_dir / "target_query_ap.csv")
    write_csv(target.aggregate_scores, output_dir / "target_map.csv")
    write_csv(artifact, output_dir / "artifact_sensitivity.csv")

    summary = pd.DataFrame(
        [
            summarize_metric("replicate_retrieval", replicate),
            summarize_metric("negcon_challenge", negcon),
            summarize_metric("target_retrieval", target),
        ]
    )
    write_csv(summary, output_dir / "summary.csv")
    print(summary.to_string(index=False))
    print(artifact.to_string(index=False))


if __name__ == "__main__":
    main()

