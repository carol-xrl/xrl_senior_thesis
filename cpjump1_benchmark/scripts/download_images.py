"""
Download Cell Painting images from S3 for specified plates.

Usage:
    # Download one plate (~68GB):
    python scripts/download_images.py --plates BR00116991 --output images/

    # Download only fluorescent channels (~42GB, skip brightfield):
    python scripts/download_images.py --plates BR00116991 --output images/ --fluorescent-only

    # Download a small subset for testing (first 2 wells only):
    python scripts/download_images.py --plates BR00116991 --output images/ --test-subset
"""

import argparse
import os
import subprocess
import sys

S3_BASE = "s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images"
BATCH = "2020_11_04_CPJUMP1"

# Mapping from plate barcode to S3 subfolder name (with timestamp)
# This needs to be discovered dynamically from S3
def find_s3_plate_dir(plate: str, batch: str = BATCH) -> str:
    """Find the S3 directory for a plate by listing the batch folder."""
    cmd = [
        "aws", "s3", "ls", "--no-sign-request",
        f"{S3_BASE}/{batch}/images/"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.strip().split("\n"):
        # Lines look like: "                           PRE BR00116991__2020-11-05T19_51_35-Measurement1/"
        parts = line.strip().split()
        if len(parts) >= 2:
            dirname = parts[-1].rstrip("/")
            if dirname.startswith(f"{plate}__"):
                return dirname
    raise FileNotFoundError(f"Cannot find S3 directory for plate {plate}")


def download_plate(plate: str, output_dir: str, fluorescent_only: bool = False, test_subset: bool = False):
    """Download images for a plate from S3."""
    print(f"Finding S3 path for {plate}...")
    s3_dirname = find_s3_plate_dir(plate)
    s3_path = f"{S3_BASE}/{BATCH}/images/{s3_dirname}/Images/"
    local_path = os.path.join(output_dir, plate)
    os.makedirs(local_path, exist_ok=True)

    cmd = [
        "aws", "s3", "sync", "--no-sign-request",
        s3_path, local_path
    ]

    if fluorescent_only:
        # Only download ch1-ch5 (skip ch6-ch8 brightfield)
        for ch in [6, 7, 8]:
            cmd.extend(["--exclude", f"*-ch{ch}sk1fk1fl1.tiff"])

    if test_subset:
        # Only download first 2 wells (r01c01, r01c02), all fields
        cmd.extend(["--exclude", "*"])
        for well in ["r01c01", "r01c02"]:
            cmd.extend(["--include", f"{well}*"])

    print(f"Downloading: {s3_path}")
    print(f"  → {local_path}")
    if fluorescent_only:
        print("  (fluorescent channels only)")
    if test_subset:
        print("  (test subset: 2 wells only)")

    subprocess.run(cmd, check=True)
    print(f"Done: {plate}")


def main():
    parser = argparse.ArgumentParser(description="Download Cell Painting images from S3")
    parser.add_argument("--plates", nargs="+", required=True, help="Plate barcodes")
    parser.add_argument("--output", default="images", help="Output directory")
    parser.add_argument("--fluorescent-only", action="store_true",
                        help="Skip brightfield channels (saves ~37%% disk)")
    parser.add_argument("--test-subset", action="store_true",
                        help="Download only 2 wells for testing")
    args = parser.parse_args()

    for plate in args.plates:
        download_plate(plate, args.output, args.fluorescent_only, args.test_subset)


if __name__ == "__main__":
    main()
