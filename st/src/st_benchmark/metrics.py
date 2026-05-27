"""Pure numpy/pandas benchmark metrics for well-level CPJUMP1 features."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MetricResult:
    query_scores: pd.DataFrame
    aggregate_scores: pd.DataFrame


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Return feature columns using the local unified convention."""
    return [col for col in df.columns if col.startswith("feature_")]


def cosine_similarity_matrix(features: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Compute cosine similarity for all rows."""
    values = features.astype(np.float64, copy=False)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    normalized = values / np.clip(norms, eps, None)
    return normalized @ normalized.T


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    """Compute average precision for binary labels and continuous scores."""
    labels = labels.astype(bool)
    n_pos = int(labels.sum())
    if n_pos == 0:
        return np.nan
    order = np.argsort(-scores, kind="mergesort")
    sorted_labels = labels[order]
    ranks = np.arange(1, len(sorted_labels) + 1)
    precision_at_k = np.cumsum(sorted_labels) / ranks
    return float(precision_at_k[sorted_labels].mean())


def _base_query_frame(df: pd.DataFrame, query_idx: int) -> dict[str, object]:
    row = df.iloc[query_idx]
    return {
        "query_index": query_idx,
        "Metadata_Plate": row["Metadata_Plate"],
        "Metadata_Well": row["Metadata_Well"],
        "Metadata_split": row.get("Metadata_split", ""),
        "Metadata_broad_sample": row["Metadata_broad_sample"],
        "Metadata_control_type": row["Metadata_control_type"],
        "Metadata_target_list": row.get("Metadata_target_list", np.nan),
    }


def _aggregate_query_scores(query_scores: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if query_scores.empty:
        return pd.DataFrame(columns=[group_col, "mean_average_precision", "n_queries"])
    return (
        query_scores.groupby(group_col, dropna=False)
        .agg(mean_average_precision=("average_precision", "mean"), n_queries=("average_precision", "size"))
        .reset_index()
        .sort_values("mean_average_precision", ascending=False)
    )


def _normalize_mask(df: pd.DataFrame, mask: object | None, name: str) -> np.ndarray:
    """Normalize an optional row mask to a boolean numpy array."""
    if mask is None:
        return np.ones(len(df), dtype=bool)
    values = np.asarray(mask, dtype=bool)
    if values.shape != (len(df),):
        raise ValueError(f"{name} must have length {len(df)}, got shape {values.shape}")
    return values


def replicate_retrieval(
    df: pd.DataFrame,
    min_positive_count: int = 1,
    query_mask: object | None = None,
    candidate_mask: object | None = None,
) -> MetricResult:
    """Cross-plate replicate retrieval using same compound as the positive label."""
    feats = df[feature_columns(df)].to_numpy()
    sim = cosine_similarity_matrix(feats)
    samples = df["Metadata_broad_sample"].to_numpy()
    plates = df["Metadata_Plate"].to_numpy()
    controls = df["Metadata_control_type"].to_numpy()
    query_allowed = _normalize_mask(df, query_mask, "query_mask")
    candidate_allowed = _normalize_mask(df, candidate_mask, "candidate_mask")

    records: list[dict[str, object]] = []
    for i in range(len(df)):
        if controls[i] == "negcon" or not query_allowed[i]:
            continue
        row_candidate_mask = (plates != plates[i]) & (controls != "negcon") & candidate_allowed
        positive_mask = row_candidate_mask & (samples == samples[i])
        if int(positive_mask.sum()) < min_positive_count:
            continue
        labels = positive_mask[row_candidate_mask]
        scores = sim[i, row_candidate_mask]
        record = _base_query_frame(df, i)
        record.update(
            metric="replicate_retrieval",
            average_precision=average_precision(labels, scores),
            n_candidates=int(row_candidate_mask.sum()),
            n_positives=int(positive_mask.sum()),
        )
        records.append(record)

    query_scores = pd.DataFrame(records)
    aggregate = _aggregate_query_scores(query_scores, "Metadata_broad_sample")
    return MetricResult(query_scores=query_scores, aggregate_scores=aggregate)


def negcon_challenge(
    df: pd.DataFrame,
    min_positive_count: int = 1,
    query_mask: object | None = None,
    candidate_mask: object | None = None,
) -> MetricResult:
    """Rank true treatment replicates against negative controls on other plates."""
    feats = df[feature_columns(df)].to_numpy()
    sim = cosine_similarity_matrix(feats)
    samples = df["Metadata_broad_sample"].to_numpy()
    plates = df["Metadata_Plate"].to_numpy()
    controls = df["Metadata_control_type"].to_numpy()
    query_allowed = _normalize_mask(df, query_mask, "query_mask")
    candidate_allowed = _normalize_mask(df, candidate_mask, "candidate_mask")

    records: list[dict[str, object]] = []
    for i in range(len(df)):
        if controls[i] == "negcon" or not query_allowed[i]:
            continue
        base_candidate_mask = (plates != plates[i]) & candidate_allowed
        positive_mask = base_candidate_mask & (samples == samples[i]) & (controls != "negcon")
        negcon_mask = base_candidate_mask & (controls == "negcon")
        row_candidate_mask = positive_mask | negcon_mask
        if int(positive_mask.sum()) < min_positive_count or int(negcon_mask.sum()) == 0:
            continue
        labels = positive_mask[row_candidate_mask]
        scores = sim[i, row_candidate_mask]
        record = _base_query_frame(df, i)
        record.update(
            metric="negcon_challenge",
            average_precision=average_precision(labels, scores),
            n_candidates=int(row_candidate_mask.sum()),
            n_positives=int(positive_mask.sum()),
            n_negcons=int(negcon_mask.sum()),
            mean_positive_similarity=float(sim[i, positive_mask].mean()),
            mean_negcon_similarity=float(sim[i, negcon_mask].mean()),
        )
        records.append(record)

    query_scores = pd.DataFrame(records)
    aggregate = _aggregate_query_scores(query_scores, "Metadata_broad_sample")
    return MetricResult(query_scores=query_scores, aggregate_scores=aggregate)


def parse_targets(value: object) -> set[str]:
    """Parse a target-list cell into a set of target names."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {part for part in text.split("|") if part}


def compound_consensus(df: pd.DataFrame) -> pd.DataFrame:
    """Build one median feature vector per treatment compound."""
    feat_cols = feature_columns(df)
    trt = df[df["Metadata_control_type"] != "negcon"].copy()
    if trt.empty:
        return trt
    feature_part = trt.groupby("Metadata_broad_sample", as_index=False)[feat_cols].median()
    meta_cols = [col for col in trt.columns if col.startswith("Metadata_") and col not in feat_cols]
    meta_part = trt[meta_cols].drop_duplicates("Metadata_broad_sample")
    return meta_part.merge(feature_part, on="Metadata_broad_sample", how="inner")


def target_retrieval(df: pd.DataFrame, min_positive_count: int = 1) -> MetricResult:
    """Compound-level target retrieval based on overlapping target lists."""
    consensus = compound_consensus(df)
    consensus = consensus[consensus["Metadata_target_list"].notna()].reset_index(drop=True)
    if consensus.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    feats = consensus[feature_columns(consensus)].to_numpy()
    sim = cosine_similarity_matrix(feats)
    targets = [parse_targets(value) for value in consensus["Metadata_target_list"]]
    samples = consensus["Metadata_broad_sample"].to_numpy()

    records: list[dict[str, object]] = []
    for i in range(len(consensus)):
        if not targets[i]:
            continue
        candidate_mask = samples != samples[i]
        positive = np.array(
            [bool(targets[i].intersection(targets[j])) for j in range(len(consensus))],
            dtype=bool,
        )
        positive_mask = candidate_mask & positive
        if int(positive_mask.sum()) < min_positive_count:
            continue
        labels = positive_mask[candidate_mask]
        scores = sim[i, candidate_mask]
        record = _base_query_frame(consensus, i)
        record.update(
            metric="target_retrieval",
            average_precision=average_precision(labels, scores),
            n_candidates=int(candidate_mask.sum()),
            n_positives=int(positive_mask.sum()),
        )
        records.append(record)

    query_scores = pd.DataFrame(records)
    aggregate = _aggregate_query_scores(query_scores, "Metadata_broad_sample")
    return MetricResult(query_scores=query_scores, aggregate_scores=aggregate)


def artifact_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize similarity categories that reveal biological and artifact signal."""
    feats = df[feature_columns(df)].to_numpy()
    sim = cosine_similarity_matrix(feats)
    samples = df["Metadata_broad_sample"].to_numpy()
    plates = df["Metadata_Plate"].to_numpy()
    wells = df["Metadata_Well"].to_numpy()
    controls = df["Metadata_control_type"].to_numpy()

    upper = np.triu(np.ones_like(sim, dtype=bool), k=1)
    same_sample = samples[:, None] == samples[None, :]
    same_plate = plates[:, None] == plates[None, :]
    same_well = wells[:, None] == wells[None, :]
    both_negcon = (controls[:, None] == "negcon") & (controls[None, :] == "negcon")
    both_trt = (controls[:, None] != "negcon") & (controls[None, :] != "negcon")

    categories = {
        "same_compound_diff_plate": upper & both_trt & same_sample & ~same_plate,
        "different_compound_same_plate": upper & both_trt & ~same_sample & same_plate,
        "different_compound_diff_plate": upper & both_trt & ~same_sample & ~same_plate,
        "same_well_diff_plate_all": upper & same_well & ~same_plate,
        "same_compound_same_well_diff_plate": upper & both_trt & same_sample & same_well & ~same_plate,
        "different_compound_same_well_diff_plate": upper & both_trt & ~same_sample & same_well & ~same_plate,
        "negcon_same_well_diff_plate": upper & both_negcon & same_well & ~same_plate,
    }

    rows = []
    for name, mask in categories.items():
        values = sim[mask]
        rows.append(
            {
                "category": name,
                "n_pairs": int(values.size),
                "mean_similarity": float(np.nanmean(values)) if values.size else np.nan,
                "median_similarity": float(np.nanmedian(values)) if values.size else np.nan,
            }
        )

    result = pd.DataFrame(rows)
    lookup = result.set_index("category")["mean_similarity"].to_dict()
    same_well_mask = categories["same_well_diff_plate_all"]
    same_well_n = int(same_well_mask.sum())
    same_well_same_sample_n = int((same_well_mask & same_sample).sum())
    same_well_confound_fraction = (
        same_well_same_sample_n / same_well_n if same_well_n else np.nan
    )
    artifact_score = lookup.get("negcon_same_well_diff_plate", np.nan) - lookup.get(
        "different_compound_diff_plate", np.nan
    )
    biology_score = lookup.get("same_compound_diff_plate", np.nan) - lookup.get(
        "different_compound_diff_plate", np.nan
    )
    result = pd.concat(
        [
            result,
            pd.DataFrame(
                [
                    {
                        "category": "artifact_score_negcon_same_well_minus_random",
                        "n_pairs": np.nan,
                        "mean_similarity": artifact_score,
                        "median_similarity": np.nan,
                    },
                    {
                        "category": "biology_score_same_compound_minus_random",
                        "n_pairs": np.nan,
                        "mean_similarity": biology_score,
                        "median_similarity": np.nan,
                    },
                    {
                        "category": "same_well_same_compound_fraction",
                        "n_pairs": same_well_n,
                        "mean_similarity": same_well_confound_fraction,
                        "median_similarity": np.nan,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    return result


def summarize_metric(name: str, result: MetricResult) -> dict[str, object]:
    """Return one row for a high-level metric summary."""
    if result.query_scores.empty:
        return {"metric": name, "mean_ap": np.nan, "n_queries": 0, "n_groups": 0}
    return {
        "metric": name,
        "mean_ap": float(result.query_scores["average_precision"].mean()),
        "median_ap": float(result.query_scores["average_precision"].median()),
        "n_queries": int(len(result.query_scores)),
        "n_groups": int(result.aggregate_scores.shape[0]),
    }
