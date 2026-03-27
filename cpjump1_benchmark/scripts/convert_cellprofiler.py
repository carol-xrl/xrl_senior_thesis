"""
Convert CellProfiler profile CSVs to unified feature format.

Produces two files:
1. well_metadata.parquet — metadata for all wells (shared across encoders)
2. features/cellprofiler.parquet — CellProfiler features in unified format

Usage:
    python scripts/convert_cellprofiler.py --root /path/to/project
"""

import argparse
import os
import sys
import glob
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cpjump1.config import load_config


METADATA_COLS = [
    "Metadata_Plate",
    "Metadata_Well",
    "Metadata_broad_sample",
    "Metadata_control_type",
    "Metadata_gene",
    "Metadata_pert_type",
    "Metadata_pert_iname",
    "Metadata_solvent",
    "Metadata_InChIKey",
    "Metadata_pubchem_cid",
    "Metadata_smiles",
    "Metadata_target_sequence",
    "Metadata_negcon_control_type",
]


def convert(root: str, config):
    batch = config.batch
    profiles_dir = os.path.join(root, config.profiles_dir, batch)
    suffix = config.profile_suffix

    plates = sorted([
        d for d in os.listdir(profiles_dir)
        if os.path.isdir(os.path.join(profiles_dir, d))
    ])

    all_meta = []
    all_features = []

    for plate in tqdm(plates, desc="Converting plates"):
        pattern = os.path.join(profiles_dir, plate, f"*_{suffix}")
        files = glob.glob(pattern)
        for f in files:
            df = pd.read_csv(f, low_memory=False)

            # Split metadata and features
            meta_cols = [c for c in METADATA_COLS if c in df.columns]
            feat_cols = [c for c in df.columns if not c.startswith("Metadata")]

            meta = df[meta_cols].copy()
            feats = df[["Metadata_Plate", "Metadata_Well"] + feat_cols].copy()

            # Rename feature columns to feature_0, feature_1, ...
            feat_rename = {old: f"feature_{i}" for i, old in enumerate(feat_cols)}
            feats = feats.rename(columns=feat_rename)

            all_meta.append(meta)
            all_features.append(feats)

    # Concatenate all plates
    meta_df = pd.concat(all_meta, ignore_index=True)
    features_df = pd.concat(all_features, ignore_index=True)

    # Save well metadata (shared across all encoders)
    meta_path = os.path.join(root, "cpjump1_benchmark", "well_metadata.parquet")
    meta_df.to_parquet(meta_path, index=False)
    print(f"Saved well metadata: {meta_path} ({len(meta_df)} wells)")

    # Save CellProfiler features
    features_dir = os.path.join(root, "cpjump1_benchmark", "features")
    os.makedirs(features_dir, exist_ok=True)
    features_path = os.path.join(features_dir, "cellprofiler.parquet")
    features_df.to_parquet(features_path, index=False)
    n_feats = len([c for c in features_df.columns if c.startswith("feature_")])
    print(f"Saved CellProfiler features: {features_path} ({len(features_df)} wells, {n_feats} features)")

    # Also save a feature name mapping for reference
    mapping_path = os.path.join(features_dir, "cellprofiler_feature_names.csv")
    feat_cols_orig = [c for c in pd.read_csv(
        glob.glob(os.path.join(profiles_dir, plates[0], f"*_{suffix}"))[0],
        nrows=0, low_memory=False
    ).columns if not c.startswith("Metadata")]
    pd.DataFrame({
        "feature_id": [f"feature_{i}" for i in range(len(feat_cols_orig))],
        "original_name": feat_cols_orig,
    }).to_csv(mapping_path, index=False)
    print(f"Saved feature name mapping: {mapping_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert CellProfiler profiles to unified format")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--config", default=None, help="Config YAML path")
    args = parser.parse_args()

    config = load_config(args.config)
    convert(args.root, config)


if __name__ == "__main__":
    main()
