"""Evaluate real or synthetic feature tables with the ST benchmark metrics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .metadata import build_subset_metadata
from .metrics import (
    MetricResult,
    artifact_sensitivity,
    feature_columns,
    negcon_challenge,
    replicate_retrieval,
    summarize_metric,
    target_retrieval,
)


def read_table(path: str | Path) -> pd.DataFrame:
    """Read CSV/TSV/parquet feature tables."""
    path = Path(path)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        return pd.read_csv(path)
    if suffixes.endswith(".tsv") or suffixes.endswith(".tsv.gz"):
        return pd.read_csv(path, sep="\t")
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table format: {path}")


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    """Write CSV output with parent directory creation."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def merge_features_with_metadata(features: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Merge feature columns onto canonical subset metadata."""
    required = {"Metadata_Plate", "Metadata_Well"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"Feature table missing required columns: {sorted(missing)}")

    feat_cols = feature_columns(features)
    if not feat_cols:
        raise ValueError("Feature table has no columns named feature_*")

    slim_features = features[["Metadata_Plate", "Metadata_Well"] + feat_cols].copy()
    merged = metadata.merge(slim_features, on=["Metadata_Plate", "Metadata_Well"], how="inner")
    expected = len(metadata)
    if len(merged) != expected:
        print(f"WARNING: merged {len(merged)} rows, expected {expected} metadata rows")
    return merged


def evaluate_feature_dataframe(
    features: pd.DataFrame,
    metadata: pd.DataFrame,
    min_positive_count: int = 1,
) -> dict[str, pd.DataFrame | MetricResult]:
    """Run all current benchmark metrics on a feature table."""
    df = merge_features_with_metadata(features, metadata)
    replicate = replicate_retrieval(df, min_positive_count=min_positive_count)
    negcon = negcon_challenge(df, min_positive_count=min_positive_count)
    target = target_retrieval(df, min_positive_count=min_positive_count)
    artifact = artifact_sensitivity(df)
    summary = pd.DataFrame(
        [
            summarize_metric("replicate_retrieval", replicate),
            summarize_metric("negcon_challenge", negcon),
            summarize_metric("target_retrieval", target),
        ]
    )
    return {
        "merged_features": df,
        "replicate": replicate,
        "negcon": negcon,
        "target": target,
        "artifact": artifact,
        "summary": summary,
    }


def evaluate_feature_file(
    feature_path: str | Path,
    config: dict,
    repo_root: str | Path,
    output_dir: str | Path,
    prefix: str,
) -> dict[str, Path]:
    """Evaluate a feature file and write metric CSVs."""
    repo_root = Path(repo_root)
    output_dir = Path(output_dir)
    metadata = build_subset_metadata(config, repo_root)
    features = read_table(feature_path)
    results = evaluate_feature_dataframe(
        features,
        metadata,
        min_positive_count=int(config["metrics"].get("min_positive_count", 1)),
    )

    paths: dict[str, Path] = {}
    paths["summary"] = write_table(results["summary"], output_dir / f"{prefix}_summary.csv")
    paths["artifact"] = write_table(results["artifact"], output_dir / f"{prefix}_artifact_sensitivity.csv")

    for metric_name in ("replicate", "negcon", "target"):
        metric = results[metric_name]
        assert isinstance(metric, MetricResult)
        paths[f"{metric_name}_query"] = write_table(
            metric.query_scores,
            output_dir / f"{prefix}_{metric_name}_query_ap.csv",
        )
        paths[f"{metric_name}_map"] = write_table(
            metric.aggregate_scores,
            output_dir / f"{prefix}_{metric_name}_map.csv",
        )
    return paths

