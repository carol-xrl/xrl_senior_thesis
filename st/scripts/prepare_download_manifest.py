#!/usr/bin/env python
"""Prepare S3 image download manifest and AWS sync commands for the selected subset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.downloads import build_download_commands, build_manifest, write_manifest_and_commands
from st_benchmark.metadata import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--image-root", default=None, help="Remote image root, e.g. /data/cpjump1/images")
    parser.add_argument("--resolve-s3", action="store_true", help="Use AWS CLI to resolve timestamped S3 plate dirs")
    parser.add_argument("--dryrun", action="store_true", help="Add --dryrun to generated aws sync commands")
    parser.add_argument("--wells", nargs="*", default=None, help="Optional well IDs for tiny pilot download, e.g. A01 A02")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    config = load_config(args.config)
    manifest = build_manifest(config, image_root=args.image_root, resolve_s3=args.resolve_s3)
    commands = build_download_commands(
        manifest,
        channels=[int(ch) for ch in config["images"]["fluorescent_channels"]],
        wells=args.wells,
        dryrun=args.dryrun,
    )
    manifest_path, commands_path = write_manifest_and_commands(
        manifest,
        commands,
        repo_root / config["paths"]["download_manifest_output"],
        repo_root / config["paths"]["download_commands_output"],
    )
    print(f"manifest: {manifest_path}")
    print(f"commands: {commands_path}")
    print(manifest.to_string(index=False))
    print("\n".join(commands))


if __name__ == "__main__":
    main()

