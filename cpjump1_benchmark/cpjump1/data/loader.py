"""Load experiment metadata, well metadata, and feature data."""

import os
import glob
import pandas as pd
import numpy as np
from ..config import Config


def load_experiment_metadata(config: Config, root: str = ".") -> pd.DataFrame:
    """Load experiment-metadata.tsv and apply standard filters."""
    path = os.path.join(root, config.experiment_metadata)
    df = (
        pd.read_csv(path, sep="\t")
        .query("Batch == @config.batch")
        .query("Density == @config.density")
        .query("Antibiotics == @config.antibiotics")
    )
    if config.exclude_cas9_compound:
        df = df.drop(
            df[(df.Perturbation == "compound") & (df.Cell_line == "Cas9")].index
        )
    return df.reset_index(drop=True)


def load_well_metadata(root: str = ".") -> pd.DataFrame:
    """Load well-level metadata (shared across all encoders)."""
    path = os.path.join(root, "cpjump1_benchmark", "well_metadata.parquet")
    return pd.read_parquet(path)


def load_features(features_path: str) -> pd.DataFrame:
    """Load a unified feature file (parquet).

    Returns DataFrame with Metadata_Plate, Metadata_Well, feature_0, feature_1, ...
    """
    return pd.read_parquet(features_path)


def merge_features_and_metadata(
    features_df: pd.DataFrame,
    well_metadata_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge feature vectors with well-level metadata.

    Features file has: Metadata_Plate, Metadata_Well, feature_*
    Well metadata has: Metadata_Plate, Metadata_Well, Metadata_broad_sample, ...
    """
    return features_df.merge(
        well_metadata_df, on=["Metadata_Plate", "Metadata_Well"], how="left"
    )


def load_profiles(
    merged_df: pd.DataFrame,
    experiment_df: pd.DataFrame,
    config: Config,
    cell: str,
    modality: str,
    time_label: str,
) -> pd.DataFrame:
    """Filter merged profiles for a (cell, modality, time_label) combination.

    Args:
        merged_df: DataFrame with features + metadata (from merge_features_and_metadata).
        experiment_df: Filtered experiment metadata.
        config: Config object.
        cell: Cell type ("A549" / "U2OS").
        modality: Perturbation type ("compound" / "crispr" / "orf").
        time_label: Time label ("short" / "long").

    Returns:
        DataFrame ready for evaluation, with Metadata_negcon and Metadata_modality added.
    """
    hours = config.hours_for(modality, time_label)

    # Get plates for this (cell, modality, time) combination
    plates_df = experiment_df.query(
        "Cell_type == @cell and Perturbation == @modality and Time == @hours"
    )
    plates = plates_df.Assay_Plate_Barcode.unique().tolist()

    # Filter to these plates
    df = merged_df[merged_df.Metadata_Plate.isin(plates)].copy()

    if df.empty:
        return df

    # Add modality column
    df["Metadata_modality"] = modality

    # For gene modalities, set matching_target from gene column
    if modality in ("crispr", "orf"):
        df["Metadata_matching_target"] = df["Metadata_gene"]

    # Fill DMSO wells — only for compounds (original notebook behavior)
    if modality == "compound":
        df["Metadata_broad_sample"] = df["Metadata_broad_sample"].fillna("DMSO")

    # Remove empty wells (rows where broad_sample is NaN)
    df = df.dropna(subset=["Metadata_broad_sample"]).reset_index(drop=True)

    # Add negcon flag
    df["Metadata_negcon"] = np.where(
        df["Metadata_control_type"] == "negcon", 1, 0
    )

    return df


def load_compound_annotations(config: Config, root: str = ".") -> pd.DataFrame:
    """Load compound -> target gene annotations."""
    path = os.path.join(root, config.compound_annotations)
    return pd.read_csv(
        path, sep="\t", usecols=["broad_sample", "target_list"]
    ).rename(columns={
        "broad_sample": "Metadata_broad_sample",
        "target_list": "Metadata_target_list",
    })
