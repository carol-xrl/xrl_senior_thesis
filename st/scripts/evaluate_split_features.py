#!/usr/bin/env python
"""Evaluate query-split and cross-time retrieval for a feature file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.evaluate import read_table, write_table
from st_benchmark.metadata import build_subset_metadata, load_config
from st_benchmark.split_eval import evaluate_split_retrieval


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_8plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", default="features")
    parser.add_argument("--write-query-tables", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    features = read_table(args.features)

    summary, query_tables = evaluate_split_retrieval(
        features,
        metadata,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )
    output_dir = Path(args.output_dir)
    summary_path = write_table(summary, output_dir / f"{args.prefix}_split_retrieval_summary.csv")
    print(summary.to_string(index=False), flush=True)
    print(f"summary: {summary_path}", flush=True)

    if args.write_query_tables:
        for name, table in query_tables.items():
            write_table(table, output_dir / f"{args.prefix}_{name}.csv")


if __name__ == "__main__":
    main()

