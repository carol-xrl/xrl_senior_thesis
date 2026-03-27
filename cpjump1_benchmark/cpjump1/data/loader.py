"""Load experiment metadata and profile data."""

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


def load_plates(
    batch: str,
    plates: list,
    suffix: str,
    profiles_dir: str,
    root: str = ".",
    extra_columns: dict = None,
) -> pd.DataFrame:
    """Load and concatenate profiles for a list of plates."""
    dfs = []
    for plate in plates:
        pattern = os.path.join(root, profiles_dir, batch, plate, f"*_{suffix}")
        files = glob.glob(pattern)
        for f in files:
            df = pd.read_csv(f, low_memory=False)
            if extra_columns:
                for col, val in extra_columns.items():
                    df[col] = val
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True, join="inner") if dfs else pd.DataFrame()


def load_profiles(
    experiment_df: pd.DataFrame,
    config: Config,
    cell: str,
    modality: str,
    time_label: str,
    root: str = ".",
) -> pd.DataFrame:
    """Load all profiles for a (cell, modality, time_label) combination.

    Returns a DataFrame with well-level profiles, empty wells filled,
    and Metadata_negcon / Metadata_modality columns added.
    """
    hours = config.hours_for(modality, time_label)

    plates_df = experiment_df.query(
        "Cell_type == @cell and Perturbation == @modality and Time == @hours"
    )
    plates = plates_df.Assay_Plate_Barcode.unique().tolist()

    extra = {"Metadata_modality": modality}
    if modality in ("crispr", "orf"):
        extra["Metadata_matching_target"] = None  # placeholder, filled below

    df = load_plates(
        config.batch, plates, config.profile_suffix, config.profiles_dir, root, extra
    )

    if df.empty:
        return df

    # For gene modalities, set matching_target from gene column
    if modality in ("crispr", "orf"):
        df["Metadata_matching_target"] = df["Metadata_gene"]

    # Fill DMSO wells — only for compounds (original notebook behavior)
    # Gene modalities (crispr/orf) do NOT get this fill;
    # their NaN broad_sample rows are simply dropped as empty wells.
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
