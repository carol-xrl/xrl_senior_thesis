#!/usr/bin/env python
"""Build benchmark subset metadata from repository metadata files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.metadata import load_config, summarize_metadata, write_subset_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    config = load_config(args.config)
    metadata_path, split_path, metadata = write_subset_metadata(config, args.repo_root)
    print(f"metadata: {metadata_path}")
    print(f"splits:   {split_path}")
    print(summarize_metadata(metadata).to_string(index=False))


if __name__ == "__main__":
    main()

