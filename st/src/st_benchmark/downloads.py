"""Download manifest helpers for CPJUMP1 image plates."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from .metadata import plate_split_map, selected_plates


def well_to_filename_prefix(well: str) -> str:
    """Convert a 384-well ID such as A01 to the CPJUMP1 filename prefix r01c01."""
    clean = well.strip().upper()
    if len(clean) < 2:
        raise ValueError(f"Invalid well ID: {well}")
    row_letter = clean[0]
    col = int(clean[1:])
    row = ord(row_letter) - ord("A") + 1
    if row < 1 or row > 16 or col < 1 or col > 24:
        raise ValueError(f"Well out of 384-well range: {well}")
    return f"r{row:02d}c{col:02d}"


def discover_s3_plate_dirs(batch: str, s3_base: str) -> dict[str, str]:
    """Discover plate timestamp directories from public S3 using AWS CLI."""
    prefix = f"{s3_base.rstrip('/')}/{batch}/images/"
    cmd = ["aws", "s3", "ls", "--no-sign-request", prefix]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    mapping: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        dirname = parts[-1].rstrip("/")
        if "__" not in dirname:
            continue
        plate = dirname.split("__", 1)[0]
        mapping[plate] = dirname
    return mapping


def build_manifest(
    config: dict[str, Any],
    image_root: str | Path | None = None,
    resolve_s3: bool = False,
) -> pd.DataFrame:
    """Build one row per selected plate with local and S3 image directories."""
    subset = config["subset"]
    images = config["images"]
    s3_base = images["s3_base"].rstrip("/")
    batch = subset["batch"]
    root = Path(image_root or images["remote_image_root"])
    splits = plate_split_map(config)
    plate_dirs = discover_s3_plate_dirs(batch, s3_base) if resolve_s3 else {}

    rows = []
    for plate in selected_plates(config):
        s3_dir = plate_dirs.get(plate, "")
        s3_path = (
            f"{s3_base}/{batch}/images/{s3_dir}/Images/"
            if s3_dir
            else ""
        )
        local_path = root / batch / plate / "Images"
        rows.append(
            {
                "Metadata_Plate": plate,
                "Metadata_split": splits[plate],
                "Batch": batch,
                "s3_plate_dir": s3_dir,
                "s3_path": s3_path,
                "local_path": str(local_path),
                "resolved": bool(s3_dir),
            }
        )
    return pd.DataFrame(rows)


def aws_sync_command(
    s3_path: str,
    local_path: str,
    channels: list[int],
    wells: list[str] | None = None,
    dryrun: bool = False,
) -> str:
    """Construct an AWS CLI sync command for fluorescent channels and optional wells."""
    if not s3_path:
        return "# unresolved S3 path; rerun with --resolve-s3 on the server"

    cmd = [
        "aws",
        "s3",
        "sync",
        "--no-sign-request",
        s3_path,
        local_path,
        "--exclude",
        "*",
    ]
    if dryrun:
        cmd.append("--dryrun")

    if wells:
        prefixes = [well_to_filename_prefix(well) for well in wells]
        for prefix in prefixes:
            for channel in channels:
                cmd.extend(["--include", f"{prefix}f*-ch{channel}sk1fk1fl1.tiff"])
    else:
        for channel in channels:
            cmd.extend(["--include", f"*-ch{channel}sk1fk1fl1.tiff"])

    return " ".join(shlex.quote(part) for part in cmd)


def build_download_commands(
    manifest: pd.DataFrame,
    channels: list[int],
    wells: list[str] | None = None,
    dryrun: bool = False,
) -> list[str]:
    """Build one AWS sync command per plate in the manifest."""
    commands = []
    for _, row in manifest.iterrows():
        commands.append(f"# {row['Metadata_Plate']} ({row['Metadata_split']})")
        commands.append(
            aws_sync_command(
                row["s3_path"],
                row["local_path"],
                channels=channels,
                wells=wells,
                dryrun=dryrun,
            )
        )
    return commands


def write_manifest_and_commands(
    manifest: pd.DataFrame,
    commands: list[str],
    manifest_path: str | Path,
    commands_path: str | Path,
) -> tuple[Path, Path]:
    """Write manifest CSV and shell command file."""
    manifest_path = Path(manifest_path)
    commands_path = Path(commands_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    commands_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(manifest_path, index=False)
    commands_path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n\n" + "\n".join(commands) + "\n")
    return manifest_path, commands_path

