#!/usr/bin/env python
"""Evaluate a real encoder feature file with the ST benchmark metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.evaluate import evaluate_feature_file
from st_benchmark.metadata import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True, help="CSV/TSV/parquet with Metadata_Plate, Metadata_Well, feature_*")
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="st/outputs/metrics")
    parser.add_argument("--prefix", default="features")
    args = parser.parse_args()

    config = load_config(args.config)
    paths = evaluate_feature_file(
        args.features,
        config=config,
        repo_root=args.repo_root,
        output_dir=Path(args.repo_root) / args.output_dir,
        prefix=args.prefix,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()

