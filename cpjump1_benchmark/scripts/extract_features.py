"""
Extract features from Cell Painting images using a specified encoder.

Reads TIFF images from local disk, runs encoder inference, aggregates
site-level features to well-level, and outputs unified parquet format.

Usage:
    # First download images for a plate:
    aws s3 sync --no-sign-request \
      s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images/2020_11_04_CPJUMP1/images/BR00116991__2020-11-05T19_51_35-Measurement1/Images/ \
      images/BR00116991/

    # Then extract features:
    python scripts/extract_features.py \
      --encoder dinov2 \
      --image-dir images/ \
      --plates BR00116991 BR00116992 \
      --output features/dinov2.parquet
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
from tqdm import tqdm
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cpjump1.imaging.preprocessing import (
    discover_sites,
    load_site,
    normalize_channels,
    resize_image,
)


ENCODERS = {
    "dinov2": ("cpjump1.encoders.dinov2", "DINOv2Encoder"),
    "clip": ("cpjump1.encoders.clip_encoder", "CLIPEncoder"),
    "openphenom": ("cpjump1.encoders.openphenom", "OpenPhenomEncoder"),
}


def load_encoder(name: str, device: str = "mps"):
    """Dynamically load an encoder by name."""
    if name not in ENCODERS:
        raise ValueError(f"Unknown encoder: {name}. Available: {list(ENCODERS.keys())}")

    module_path, class_name = ENCODERS[name]
    import importlib
    module = importlib.import_module(module_path)
    encoder_class = getattr(module, class_name)
    return encoder_class(device=device)


def find_plate_image_dir(image_base: str, plate: str) -> str:
    """Find the image directory for a plate.

    Handles both flat layout (images/{plate}/) and S3-style layout
    (images/{plate}__timestamp/Images/).
    """
    # Try flat layout first
    flat = os.path.join(image_base, plate)
    if os.path.isdir(flat):
        # Check if TIFFs are directly here
        if any(f.endswith(".tiff") for f in os.listdir(flat)):
            return flat
        # Check for Images/ subdirectory (S3 layout)
        images_sub = os.path.join(flat, "Images")
        if os.path.isdir(images_sub):
            return images_sub

    # Try S3-style with timestamp prefix
    for d in os.listdir(image_base):
        if d.startswith(f"{plate}__") and os.path.isdir(os.path.join(image_base, d)):
            images_sub = os.path.join(image_base, d, "Images")
            if os.path.isdir(images_sub):
                return images_sub
            return os.path.join(image_base, d)

    raise FileNotFoundError(f"Cannot find image directory for plate {plate} in {image_base}")


def extract_plate(encoder, plate: str, image_dir: str) -> pd.DataFrame:
    """Extract features for all wells in a plate.

    Args:
        encoder: BaseEncoder instance.
        plate: Plate barcode.
        image_dir: Directory containing TIFF files for this plate.

    Returns:
        DataFrame with Metadata_Plate, Metadata_Well, feature_0, ...
    """
    sites = discover_sites(image_dir)

    if not sites:
        print(f"  WARNING: No sites found in {image_dir}")
        return pd.DataFrame()

    # Group sites by well
    wells = defaultdict(dict)
    for (well, field), channel_paths in sites.items():
        wells[well][field] = channel_paths

    results = []
    for well in tqdm(sorted(wells.keys()), desc=f"  {plate}", leave=False):
        site_features = []
        for field in sorted(wells[well].keys()):
            channel_paths = wells[well][field]

            # Skip sites with missing channels
            if len(channel_paths) < 5:
                continue

            # Load, normalize, resize
            img = load_site(channel_paths)  # (5, 1080, 1080) uint16
            img = normalize_channels(img)   # (5, 1080, 1080) float32 [0,1]
            img = resize_image(img, encoder.input_size)  # (5, size, size)

            # Encode
            feat = encoder.encode_site(img)
            site_features.append(feat)

        if not site_features:
            continue

        # Aggregate to well level
        well_feat = encoder.encode_well(site_features)

        row = {"Metadata_Plate": plate, "Metadata_Well": well}
        for i, v in enumerate(well_feat):
            row[f"feature_{i}"] = float(v)
        results.append(row)

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Extract features from Cell Painting images")
    parser.add_argument("--encoder", required=True, choices=list(ENCODERS.keys()),
                        help="Encoder to use")
    parser.add_argument("--image-dir", required=True,
                        help="Base directory containing plate image folders")
    parser.add_argument("--plates", nargs="+", default=None,
                        help="Plate barcodes to process (default: all found in image-dir)")
    parser.add_argument("--output", default=None,
                        help="Output parquet path (default: features/{encoder}.parquet)")
    parser.add_argument("--device", default="mps",
                        help="PyTorch device (mps/cpu/cuda)")
    args = parser.parse_args()

    # Output path
    output = args.output or f"cpjump1_benchmark/features/{args.encoder}.parquet"
    os.makedirs(os.path.dirname(output), exist_ok=True)

    # Load encoder
    print(f"Loading {args.encoder} encoder...")
    encoder = load_encoder(args.encoder, device=args.device)
    print(f"  Input: {encoder.num_channels}ch x {encoder.input_size}x{encoder.input_size}")
    print(f"  Output: {encoder.feature_dim}-dim features")

    # Find plates
    if args.plates:
        plates = args.plates
    else:
        plates = sorted([
            d.split("__")[0] for d in os.listdir(args.image_dir)
            if os.path.isdir(os.path.join(args.image_dir, d)) and d.startswith("BR")
        ])
        plates = sorted(set(plates))

    print(f"Processing {len(plates)} plates...")

    all_dfs = []
    for plate in plates:
        print(f"Plate {plate}:")
        image_dir = find_plate_image_dir(args.image_dir, plate)
        df = extract_plate(encoder, plate, image_dir)
        if not df.empty:
            all_dfs.append(df)
            print(f"  → {len(df)} wells")

    if not all_dfs:
        print("No features extracted!")
        return

    result = pd.concat(all_dfs, ignore_index=True)
    result.to_parquet(output, index=False)
    n_feats = len([c for c in result.columns if c.startswith("feature_")])
    print(f"\nSaved: {output} ({len(result)} wells, {n_feats} features)")


if __name__ == "__main__":
    main()
