#!/usr/bin/env python
"""Download selected CPJUMP1 plates from a resolved manifest in parallel."""

from __future__ import annotations

import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


def count_tiffs(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob("*.tiff"))


def aws_sync_command(row: pd.Series, channels: list[int], only_show_errors: bool) -> list[str]:
    cmd = [
        "aws",
        "s3",
        "sync",
        "--no-sign-request",
        str(row["s3_path"]),
        str(row["local_path"]),
        "--exclude",
        "*",
    ]
    if only_show_errors:
        cmd.append("--only-show-errors")
    for channel in channels:
        cmd.extend(["--include", f"*-ch{channel}sk1fk1fl1.tiff"])
    return cmd


def download_plate(row: pd.Series, channels: list[int], min_tiffs: int, only_show_errors: bool) -> tuple[str, int]:
    plate = str(row["Metadata_Plate"])
    local_path = Path(str(row["local_path"]))
    before = count_tiffs(local_path)
    if before >= min_tiffs:
        print(f"{plate}: already complete ({before} TIFFs)", flush=True)
        return plate, before
    if not str(row.get("s3_path", "")):
        raise RuntimeError(f"{plate}: manifest has no resolved s3_path")

    print(f"{plate}: starting sync with {before} TIFFs", flush=True)
    local_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(aws_sync_command(row, channels, only_show_errors), check=True)
    after = count_tiffs(local_path)
    print(f"{plate}: finished sync with {after} TIFFs", flush=True)
    if after < min_tiffs:
        raise RuntimeError(f"{plate}: incomplete after sync ({after} < {min_tiffs})")
    return plate, after


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv")
    parser.add_argument("--plates", nargs="*", default=None, help="Optional subset of plate barcodes to download")
    parser.add_argument("--channels", nargs="*", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--min-tiffs", type=int, default=17280)
    parser.add_argument("--show-progress", action="store_true")
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest)
    if args.plates:
        requested = set(args.plates)
        manifest = manifest[manifest["Metadata_Plate"].isin(requested)].copy()
        missing = sorted(requested - set(manifest["Metadata_Plate"]))
        if missing:
            raise SystemExit(f"plates not found in manifest: {missing}")

    rows = [row for _, row in manifest.iterrows()]
    if not rows:
        raise SystemExit("no plates selected")

    workers = max(1, min(args.parallel, len(rows)))
    print(f"selected {len(rows)} plates; parallel={workers}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                download_plate,
                row,
                args.channels,
                args.min_tiffs,
                not args.show_progress,
            )
            for row in rows
        ]
        for future in as_completed(futures):
            plate, count = future.result()
            print(f"{plate}: complete ({count} TIFFs)", flush=True)


if __name__ == "__main__":
    main()
