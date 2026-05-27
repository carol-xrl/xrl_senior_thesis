"""Metadata construction for the compact CPJUMP1 subset benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load a benchmark YAML config."""
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def plate_split_map(config: dict[str, Any]) -> dict[str, str]:
    """Return mapping from plate barcode to split name."""
    mapping: dict[str, str] = {}
    for split, plates in config["subset"]["plates"].items():
        for plate in plates:
            mapping[plate] = split
    return mapping


def selected_plates(config: dict[str, Any]) -> list[str]:
    """Return selected plate barcodes in split order."""
    plates: list[str] = []
    for split in ("train", "val", "test"):
        plates.extend(config["subset"]["plates"].get(split, []))
    return plates


def _subset_filter(frame: pd.DataFrame, column: str, value: Any) -> pd.Series:
    """Return a boolean mask for a scalar or list-valued subset criterion."""
    if isinstance(value, (list, tuple, set)):
        return frame[column].isin(value)
    return frame[column] == value


def load_experiment_metadata(config: dict[str, Any], repo_root: str | Path) -> pd.DataFrame:
    """Load and filter the CPJUMP1 experiment metadata for the configured subset."""
    repo_root = Path(repo_root)
    subset = config["subset"]
    exp_path = repo_root / config["paths"]["experiment_metadata"]
    df = pd.read_csv(exp_path, sep="\t")

    filtered = df[
        _subset_filter(df, "Batch", subset["batch"])
        & _subset_filter(df, "Perturbation", subset["perturbation"])
        & _subset_filter(df, "Cell_type", subset["cell_type"])
        & _subset_filter(df, "Time", subset["time"])
        & _subset_filter(df, "Density", subset["density"])
        & _subset_filter(df, "Antibiotics", subset["antibiotics"])
        & _subset_filter(df, "Cell_line", subset["cell_line"])
        & (df["Assay_Plate_Barcode"].isin(selected_plates(config)))
    ].copy()

    split_map = plate_split_map(config)
    filtered["Metadata_split"] = filtered["Assay_Plate_Barcode"].map(split_map)
    return filtered.reset_index(drop=True)


def load_compound_annotations(config: dict[str, Any], repo_root: str | Path) -> pd.DataFrame:
    """Load compound-level annotation fields used by benchmark metrics."""
    repo_root = Path(repo_root)
    path = repo_root / config["paths"]["compound_annotations"]
    df = pd.read_csv(path, sep="\t")
    keep = [
        "broad_sample",
        "pert_iname",
        "pubchem_cid",
        "target",
        "target_list",
        "moa_list",
        "purity",
        "pert_type",
        "control_type",
        "smiles",
    ]
    keep = [col for col in keep if col in df.columns]
    return df[keep].copy()


def load_platemap(config: dict[str, Any], repo_root: str | Path) -> pd.DataFrame:
    """Load the compound plate map and normalize control wells."""
    repo_root = Path(repo_root)
    path = repo_root / config["paths"]["platemap"]
    df = pd.read_csv(path, sep="\t")
    df = df.rename(
        columns={
            "well_position": "Metadata_Well",
            "broad_sample": "Metadata_broad_sample",
            "solvent": "Metadata_solvent",
        }
    )

    sample = df["Metadata_broad_sample"].replace("", np.nan)
    is_negcon = sample.isna()
    df["Metadata_broad_sample"] = sample.fillna("DMSO")
    df["Metadata_control_type"] = np.where(is_negcon, "negcon", "trt")
    return df


def build_subset_metadata(config: dict[str, Any], repo_root: str | Path) -> pd.DataFrame:
    """Build one row per selected plate/well with perturbation annotations."""
    exp = load_experiment_metadata(config, repo_root)
    plate_map = load_platemap(config, repo_root)
    annotations = load_compound_annotations(config, repo_root).rename(
        columns={
            "broad_sample": "Metadata_broad_sample",
            "pert_iname": "Metadata_pert_iname",
            "pubchem_cid": "Metadata_pubchem_cid",
            "target": "Metadata_target",
            "target_list": "Metadata_target_list",
            "moa_list": "Metadata_moa_list",
            "purity": "Metadata_purity",
            "pert_type": "Metadata_pert_type",
            "control_type": "Metadata_annotation_control_type",
            "smiles": "Metadata_smiles",
        }
    )

    rows = []
    split_map = plate_split_map(config)
    for plate in selected_plates(config):
        plate_rows = plate_map.copy()
        plate_rows["Metadata_Plate"] = plate
        plate_rows["Metadata_split"] = split_map[plate]
        rows.append(plate_rows)
    wells = pd.concat(rows, ignore_index=True)

    merged = wells.merge(annotations, on="Metadata_broad_sample", how="left")
    merged = merged.merge(
        exp.add_prefix("Experiment_"),
        left_on="Metadata_Plate",
        right_on="Experiment_Assay_Plate_Barcode",
        how="left",
    )

    # Keep benchmark-facing names stable.
    merged["Metadata_Batch"] = merged["Experiment_Batch"]
    merged["Metadata_Cell_type"] = merged["Experiment_Cell_type"]
    merged["Metadata_Time"] = merged["Experiment_Time"]
    merged["Metadata_Perturbation"] = merged["Experiment_Perturbation"]

    ordered = [
        "Metadata_Plate",
        "Metadata_Well",
        "Metadata_split",
        "Metadata_Batch",
        "Metadata_Perturbation",
        "Metadata_Cell_type",
        "Metadata_Time",
        "Metadata_broad_sample",
        "Metadata_control_type",
        "Metadata_solvent",
        "Metadata_pert_iname",
        "Metadata_target",
        "Metadata_target_list",
        "Metadata_moa_list",
        "Metadata_purity",
        "Metadata_pert_type",
        "Metadata_pubchem_cid",
        "Metadata_smiles",
    ]
    ordered = [col for col in ordered if col in merged.columns]
    return merged[ordered].sort_values(["Metadata_Plate", "Metadata_Well"]).reset_index(drop=True)


def write_subset_metadata(
    config: dict[str, Any],
    repo_root: str | Path,
    metadata_output: str | Path | None = None,
    split_output: str | Path | None = None,
) -> tuple[Path, Path, pd.DataFrame]:
    """Build and write subset metadata and plate split files."""
    repo_root = Path(repo_root)
    metadata = build_subset_metadata(config, repo_root)

    metadata_path = repo_root / (metadata_output or config["paths"]["metadata_output"])
    split_path = repo_root / (split_output or config["paths"]["split_output"])
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.parent.mkdir(parents=True, exist_ok=True)

    metadata.to_csv(metadata_path, index=False)

    split_df = (
        metadata[["Metadata_Plate", "Metadata_split"]]
        .drop_duplicates()
        .sort_values(["Metadata_split", "Metadata_Plate"])
    )
    split_df.to_csv(split_path, index=False)
    return metadata_path, split_path, metadata


def summarize_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
    """Return a small summary table for logging."""
    rows = [
        ("wells", len(metadata)),
        ("plates", metadata["Metadata_Plate"].nunique()),
        ("treatment_wells", int((metadata["Metadata_control_type"] != "negcon").sum())),
        ("negcon_wells", int((metadata["Metadata_control_type"] == "negcon").sum())),
        ("unique_broad_samples", metadata["Metadata_broad_sample"].nunique()),
        (
            "annotated_treatment_wells",
            int(
                (
                    (metadata["Metadata_control_type"] != "negcon")
                    & metadata["Metadata_target_list"].notna()
                ).sum()
            ),
        ),
    ]
    return pd.DataFrame(rows, columns=["name", "value"])
