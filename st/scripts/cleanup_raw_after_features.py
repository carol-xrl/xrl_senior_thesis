#!/usr/bin/env python
"""Delete raw plate images after required plate-level feature files exist."""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv")
    parser.add_argument("--image-root", default="/workspace/data/cpjump1/images")
    parser.add_argument("--batch", default="2020_11_04_CPJUMP1")
    parser.add_argument("--feature-root", default="st/outputs/features/multimodal_short_20plate_by_plate")
    parser.add_argument(
        "--required-prefix",
        action="append",
        required=True,
        help="Feature prefix that must have <prefix>_<plate>.csv.done before deleting raw images. Repeatable.",
    )
    parser.add_argument("--check-interval-seconds", type=int, default=120)
    parser.add_argument("--delete", action="store_true", help="Actually delete raw images. Without this flag, only log actions.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    return parser.parse_args()


def plate_size_gb(path: Path) -> float:
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    return total / 1024**3


def features_ready(feature_root: Path, prefixes: list[str], plate: str) -> bool:
    return all((feature_root / f"{prefix}_{plate}.csv.done").exists() for prefix in prefixes)


def main() -> None:
    args = parse_args()
    manifest = pd.read_csv(args.manifest)
    plates = manifest["Metadata_Plate"].drop_duplicates().astype(str).tolist()
    image_root = Path(args.image_root)
    feature_root = Path(args.feature_root)

    mode = "DELETE" if args.delete else "DRY-RUN"
    print(f"cleanup mode={mode}; plates={len(plates)}; required_prefixes={args.required_prefix}", flush=True)

    while True:
        remaining = []
        for plate in plates:
            plate_dir = image_root / args.batch / plate
            if not plate_dir.exists():
                continue
            if not features_ready(feature_root, args.required_prefix, plate):
                remaining.append(plate)
                continue

            size_gb = plate_size_gb(plate_dir)
            if args.delete:
                shutil.rmtree(plate_dir)
                print(f"deleted {plate_dir} ({size_gb:.1f} GiB)", flush=True)
            else:
                print(f"would delete {plate_dir} ({size_gb:.1f} GiB)", flush=True)

        if args.once:
            break
        if not remaining:
            print("all eligible raw plate directories are gone", flush=True)
            break
        print(f"waiting for required features: {', '.join(remaining)}", flush=True)
        time.sleep(args.check_interval_seconds)


if __name__ == "__main__":
    main()
