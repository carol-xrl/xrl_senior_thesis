"""Synthetic feature generation for local benchmark smoke tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import parse_targets


def _random_unit_vector(rng: np.random.Generator, dim: int) -> np.ndarray:
    vector = rng.normal(size=dim)
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def generate_synthetic_features(metadata: pd.DataFrame, smoke_config: dict) -> pd.DataFrame:
    """Generate features with compound, target, plate, and well-position signal."""
    dim = int(smoke_config.get("synthetic_feature_dim", 64))
    rng = np.random.default_rng(int(smoke_config.get("random_seed", 42)))
    compound_signal = float(smoke_config.get("compound_signal", 2.0))
    target_signal = float(smoke_config.get("target_signal", 0.6))
    plate_signal = float(smoke_config.get("plate_signal", 0.35))
    well_signal = float(smoke_config.get("well_position_signal", 0.15))
    noise = float(smoke_config.get("noise", 0.25))

    compounds = {
        sample: _random_unit_vector(rng, dim)
        for sample in sorted(metadata["Metadata_broad_sample"].dropna().unique())
    }
    plates = {
        plate: _random_unit_vector(rng, dim)
        for plate in sorted(metadata["Metadata_Plate"].dropna().unique())
    }
    wells = {
        well: _random_unit_vector(rng, dim)
        for well in sorted(metadata["Metadata_Well"].dropna().unique())
    }

    all_targets = sorted(
        {
            target
            for value in metadata["Metadata_target_list"].dropna().unique()
            for target in parse_targets(value)
        }
    )
    targets = {target: _random_unit_vector(rng, dim) for target in all_targets}

    rows = []
    for _, row in metadata.iterrows():
        sample = row["Metadata_broad_sample"]
        vector = compound_signal * compounds[sample]
        for target in parse_targets(row.get("Metadata_target_list")):
            vector = vector + target_signal * targets[target]
        vector = vector + plate_signal * plates[row["Metadata_Plate"]]
        vector = vector + well_signal * wells[row["Metadata_Well"]]
        vector = vector + rng.normal(scale=noise, size=dim)

        out = row.to_dict()
        for idx, value in enumerate(vector):
            out[f"feature_{idx}"] = float(value)
        rows.append(out)

    return pd.DataFrame(rows)

