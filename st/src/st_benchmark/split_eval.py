"""Split- and time-aware retrieval summaries."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluate import merge_features_with_metadata
from .metrics import MetricResult, negcon_challenge, replicate_retrieval, summarize_metric


def _series_equals(df: pd.DataFrame, column: str, value: object) -> np.ndarray:
    if column not in df.columns:
        return np.zeros(len(df), dtype=bool)
    return (df[column].to_numpy() == value)


def _add_summary_row(scope: str, metric_name: str, result: MetricResult) -> dict[str, object]:
    row = summarize_metric(metric_name, result)
    return {"scope": scope, **row}


def retrieval_scopes(df: pd.DataFrame) -> list[tuple[str, np.ndarray | None, np.ndarray | None]]:
    """Return standard query/candidate masks for 8-plate reporting."""
    scopes: list[tuple[str, np.ndarray | None, np.ndarray | None]] = [("all_queries", None, None)]

    if "Metadata_split" in df.columns:
        for split in ("train", "val", "test"):
            scopes.append((f"{split}_queries", _series_equals(df, "Metadata_split", split), None))

    if "Metadata_Time" in df.columns:
        for time_value in sorted(pd.Series(df["Metadata_Time"]).dropna().unique()):
            scopes.append(
                (
                    f"within_time_{time_value}",
                    _series_equals(df, "Metadata_Time", time_value),
                    _series_equals(df, "Metadata_Time", time_value),
                )
            )

        if set(pd.Series(df["Metadata_Time"]).dropna().unique()) >= {24, 48}:
            scopes.extend(
                [
                    (
                        "cross_time_24_to_48",
                        _series_equals(df, "Metadata_Time", 24),
                        _series_equals(df, "Metadata_Time", 48),
                    ),
                    (
                        "cross_time_48_to_24",
                        _series_equals(df, "Metadata_Time", 48),
                        _series_equals(df, "Metadata_Time", 24),
                    ),
                ]
            )
    return scopes


def evaluate_split_retrieval(
    features: pd.DataFrame,
    metadata: pd.DataFrame,
    min_positive_count: int = 1,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Evaluate replicate and negcon retrieval on standard query/candidate scopes."""
    df = merge_features_with_metadata(features, metadata)
    summary_rows: list[dict[str, object]] = []
    query_tables: dict[str, pd.DataFrame] = {}

    for scope, query_mask, candidate_mask in retrieval_scopes(df):
        replicate = replicate_retrieval(
            df,
            min_positive_count=min_positive_count,
            query_mask=query_mask,
            candidate_mask=candidate_mask,
        )
        negcon = negcon_challenge(
            df,
            min_positive_count=min_positive_count,
            query_mask=query_mask,
            candidate_mask=candidate_mask,
        )
        summary_rows.append(_add_summary_row(scope, "replicate_retrieval", replicate))
        summary_rows.append(_add_summary_row(scope, "negcon_challenge", negcon))
        query_tables[f"{scope}_replicate_query_ap"] = replicate.query_scores
        query_tables[f"{scope}_negcon_query_ap"] = negcon.query_scores

    return pd.DataFrame(summary_rows), query_tables
