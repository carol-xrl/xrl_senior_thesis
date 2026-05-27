#!/usr/bin/env python
"""Plot summary and artifact metric CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.plots import plot_artifact, plot_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--output-dir", default="st/outputs/figures")
    parser.add_argument("--prefix", default="features")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    summary_path = plot_summary(args.summary, output_dir / f"{args.prefix}_summary.png")
    artifact_path = plot_artifact(args.artifact, output_dir / f"{args.prefix}_artifact.png")
    print(f"summary figure: {summary_path}")
    print(f"artifact figure: {artifact_path}")


if __name__ == "__main__":
    main()

