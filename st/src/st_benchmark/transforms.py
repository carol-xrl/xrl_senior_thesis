"""Feature normalization and plate-correction transforms."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import feature_columns


def l2_normalize(values: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Row-wise L2 normalization."""
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, eps)


def safe_zscore(values: np.ndarray, mean: np.ndarray, std: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Z-score with a floor on standard deviation."""
    return (values - mean) / np.maximum(std, eps)


def transformed_features(features: pd.DataFrame, metadata: pd.DataFrame, variant: str) -> pd.DataFrame:
    """Return a transformed feature table with the original metadata keys."""
    keys = ["Metadata_Plate", "Metadata_Well"]
    feat_cols = feature_columns(features)
    if not feat_cols:
        raise ValueError("No feature_* columns found")

    frame = metadata[keys + ["Metadata_control_type"]].merge(features[keys + feat_cols], on=keys, how="inner")
    values = frame[feat_cols].to_numpy(dtype=np.float64)

    if variant == "raw_l2":
        transformed = l2_normalize(values)
    elif variant == "global_zscore_l2":
        transformed = l2_normalize(safe_zscore(values, values.mean(axis=0), values.std(axis=0)))
    elif variant in {"plate_center_l2", "plate_zscore_l2", "negcon_center_l2", "negcon_zscore_l2"}:
        transformed = np.empty_like(values)
        for _, idx in frame.groupby("Metadata_Plate").groups.items():
            idx_array = np.array(list(idx), dtype=int)
            plate_values = values[idx_array]
            if variant.startswith("negcon"):
                neg_idx = idx_array[frame.loc[idx_array, "Metadata_control_type"].to_numpy() == "negcon"]
                reference = values[neg_idx] if len(neg_idx) else plate_values
            else:
                reference = plate_values

            center = reference.mean(axis=0)
            if variant.endswith("zscore_l2"):
                adjusted = safe_zscore(plate_values, center, reference.std(axis=0))
            else:
                adjusted = plate_values - center
            transformed[idx_array] = adjusted
        transformed = l2_normalize(transformed)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    output = frame[keys].reset_index(drop=True).copy()
    feature_frame = pd.DataFrame(transformed.astype(np.float32), columns=feat_cols, index=output.index)
    return pd.concat([output, feature_frame], axis=1)

