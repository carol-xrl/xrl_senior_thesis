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


def _path_for_perturbation(config: dict[str, Any], key: str, perturbation: str | None = None) -> str:
    """Return a scalar or perturbation-specific configured path."""
    value = config["paths"][key]
    if isinstance(value, dict):
        if perturbation is None:
            raise ValueError(f"paths.{key} is modality-specific; perturbation is required")
        return value[perturbation]
    return value


def load_annotations(
    config: dict[str, Any],
    repo_root: str | Path,
    perturbation: str = "compound",
) -> pd.DataFrame:
    """Load perturbation-level annotation fields used by benchmark metrics."""
    repo_root = Path(repo_root)
    path_key = "annotations" if "annotations" in config["paths"] else "compound_annotations"
    path = repo_root / _path_for_perturbation(config, path_key, perturbation)
    df = pd.read_csv(path, sep="\t")
    keep = [
        "broad_sample",
        "gene",
        "pert_iname",
        "pubchem_cid",
        "target",
        "target_list",
        "moa_list",
        "purity",
        "pert_type",
        "control_type",
        "smiles",
        "target_sequence",
        "negcon_control_type",
    ]
    keep = [col for col in keep if col in df.columns]
    return df[keep].copy()


def load_compound_annotations(config: dict[str, Any], repo_root: str | Path) -> pd.DataFrame:
    """Load compound-level annotation fields used by benchmark metrics."""
    return load_annotations(config, repo_root, perturbation="compound")


def load_platemap(
    config: dict[str, Any],
    repo_root: str | Path,
    perturbation: str = "compound",
) -> pd.DataFrame:
    """Load a plate map and normalize compound DMSO controls."""
    repo_root = Path(repo_root)
    path_key = "platemaps" if "platemaps" in config["paths"] else "platemap"
    path = repo_root / _path_for_perturbation(config, path_key, perturbation)
    df = pd.read_csv(path, sep="\t")
    df = df.rename(
        columns={
            "well_position": "Metadata_Well",
            "broad_sample": "Metadata_broad_sample",
            "solvent": "Metadata_solvent",
        }
    )

    sample = df["Metadata_broad_sample"].replace("", np.nan)
    if perturbation == "compound":
        is_negcon = sample.isna()
        df["Metadata_broad_sample"] = sample.fillna("DMSO")
        df["Metadata_control_type"] = np.where(is_negcon, "negcon", "trt")
    else:
        df["Metadata_broad_sample"] = sample
    return df


def build_subset_metadata(config: dict[str, Any], repo_root: str | Path) -> pd.DataFrame:
    """Build one row per selected plate/well with perturbation annotations."""
    exp = load_experiment_metadata(config, repo_root)

    rows = []
    split_map = plate_split_map(config)
    exp_by_plate = exp.drop_duplicates("Assay_Plate_Barcode").set_index("Assay_Plate_Barcode")
    annotation_cache: dict[str, pd.DataFrame] = {}
    for plate in selected_plates(config):
        if plate not in exp_by_plate.index:
            raise ValueError(f"Selected plate is not present after subset filtering: {plate}")
        perturbation = str(exp_by_plate.loc[plate, "Perturbation"])
        if perturbation not in annotation_cache:
            annotation_cache[perturbation] = load_annotations(config, repo_root, perturbation).rename(
                columns={
                    "broad_sample": "Metadata_broad_sample",
                    "gene": "Metadata_gene",
                    "pert_iname": "Metadata_pert_iname",
                    "pubchem_cid": "Metadata_pubchem_cid",
                    "target": "Metadata_target",
                    "target_list": "Metadata_target_list",
                    "moa_list": "Metadata_moa_list",
                    "purity": "Metadata_purity",
                    "pert_type": "Metadata_pert_type",
                    "control_type": "Metadata_annotation_control_type",
                    "smiles": "Metadata_smiles",
                    "target_sequence": "Metadata_target_sequence",
                    "negcon_control_type": "Metadata_negcon_control_type",
                }
            )
        plate_map = load_platemap(config, repo_root, perturbation)
        plate_rows = plate_map.copy()
        plate_rows = plate_rows.merge(annotation_cache[perturbation], on="Metadata_broad_sample", how="left")
        if perturbation != "compound":
            plate_rows["Metadata_control_type"] = np.where(
                plate_rows["Metadata_broad_sample"].isna(),
                "empty",
                np.where(
                    plate_rows["Metadata_annotation_control_type"].eq("negcon"),
                    "negcon",
                    "trt",
                ),
            )
            plate_rows = plate_rows[plate_rows["Metadata_control_type"] != "empty"].copy()
        plate_rows["Metadata_Plate"] = plate
        plate_rows["Metadata_split"] = split_map[plate]
        plate_rows["Metadata_modality"] = perturbation
        rows.append(plate_rows)
    wells = pd.concat(rows, ignore_index=True)

    merged = wells.merge(
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
    merged["Metadata_Cell_line"] = merged["Experiment_Cell_line"]

    ordered = [
        "Metadata_Plate",
        "Metadata_Well",
        "Metadata_split",
        "Metadata_modality",
        "Metadata_Batch",
        "Metadata_Perturbation",
        "Metadata_Cell_type",
        "Metadata_Cell_line",
        "Metadata_Time",
        "Metadata_broad_sample",
        "Metadata_gene",
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
        "Metadata_target_sequence",
        "Metadata_negcon_control_type",
        "Metadata_annotation_control_type",
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
                    & metadata.get("Metadata_target_list", pd.Series(index=metadata.index, dtype=object)).notna()
                ).sum()
            ),
        ),
        (
            "annotated_gene_wells",
            int(metadata.get("Metadata_gene", pd.Series(index=metadata.index, dtype=object)).notna().sum()),
        ),
    ]
    return pd.DataFrame(rows, columns=["name", "value"])
