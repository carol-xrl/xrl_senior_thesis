"""Multimodal CPJUMP1 metrics for compound, ORF, and CRISPR subsets."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluate import merge_features_with_metadata
from .metrics import (
    MetricResult,
    average_precision,
    cosine_similarity_matrix,
    feature_columns,
    negcon_challenge,
    parse_targets,
    replicate_retrieval,
    summarize_metric,
)


def _condition_mask(df: pd.DataFrame, cell: str, modality: str) -> np.ndarray:
    return (
        (df["Metadata_Cell_type"].to_numpy() == cell)
        & (df["Metadata_modality"].to_numpy() == modality)
    )


def _target_set(row: pd.Series) -> set[str]:
    if row.get("Metadata_modality") == "compound":
        return parse_targets(row.get("Metadata_target_list"))
    gene = row.get("Metadata_gene")
    if pd.isna(gene) or str(gene).strip() == "":
        return set()
    return {str(gene).strip()}


def _consensus(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Build median consensus profiles and keep one metadata row per group."""
    feat_cols = feature_columns(df)
    trt = df[(df["Metadata_control_type"] != "negcon") & df["Metadata_broad_sample"].notna()].copy()
    if trt.empty:
        return trt

    feature_part = trt.groupby(group_cols, as_index=False)[feat_cols].median()
    meta_cols = [
        col
        for col in trt.columns
        if col.startswith("Metadata_") and col not in feat_cols and col not in group_cols
    ]
    meta_part = trt[group_cols + meta_cols].drop_duplicates(group_cols)
    consensus = meta_part.merge(feature_part, on=group_cols, how="inner")
    consensus["Metadata_matching_targets"] = consensus.apply(
        lambda row: "|".join(sorted(_target_set(row))),
        axis=1,
    )
    return consensus


def _aggregate(query_scores: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if query_scores.empty:
        return pd.DataFrame(columns=[group_col, "mean_average_precision", "n_queries"])
    return (
        query_scores.groupby(group_col, dropna=False)
        .agg(mean_average_precision=("average_precision", "mean"), n_queries=("average_precision", "size"))
        .reset_index()
        .sort_values("mean_average_precision", ascending=False)
    )


def _base_record(df: pd.DataFrame, query_idx: int) -> dict[str, object]:
    row = df.iloc[query_idx]
    return {
        "query_index": query_idx,
        "Metadata_Cell_type": row.get("Metadata_Cell_type", ""),
        "Metadata_modality": row.get("Metadata_modality", ""),
        "Metadata_broad_sample": row.get("Metadata_broad_sample", ""),
        "Metadata_gene": row.get("Metadata_gene", np.nan),
        "Metadata_matching_targets": row.get("Metadata_matching_targets", ""),
    }


def within_modality_matching(condition_df: pd.DataFrame, min_positive_count: int = 1) -> MetricResult:
    """Evaluate target/gene matching inside one cell-type and modality condition."""
    if condition_df.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    modality = str(condition_df["Metadata_modality"].iloc[0])
    if modality == "orf":
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    consensus = _consensus(
        condition_df,
        ["Metadata_Cell_type", "Metadata_modality", "Metadata_broad_sample"],
    ).reset_index(drop=True)
    if consensus.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    target_sets = [set(value.split("|")) if isinstance(value, str) and value else set() for value in consensus["Metadata_matching_targets"]]
    samples = consensus["Metadata_broad_sample"].to_numpy()
    sim = cosine_similarity_matrix(consensus[feature_columns(consensus)].to_numpy())

    records: list[dict[str, object]] = []
    for i, targets in enumerate(target_sets):
        if not targets:
            continue
        candidate_mask = samples != samples[i]
        positive_mask = np.array(
            [bool(targets.intersection(other)) for other in target_sets],
            dtype=bool,
        ) & candidate_mask
        if int(positive_mask.sum()) < min_positive_count:
            continue

        record = _base_record(consensus, i)
        record.update(
            metric="within_modality_matching",
            average_precision=average_precision(positive_mask[candidate_mask], sim[i, candidate_mask]),
            n_candidates=int(candidate_mask.sum()),
            n_positives=int(positive_mask.sum()),
        )
        records.append(record)

    query_scores = pd.DataFrame(records)
    aggregate_col = "Metadata_matching_targets" if modality == "compound" else "Metadata_gene"
    return MetricResult(query_scores=query_scores, aggregate_scores=_aggregate(query_scores, aggregate_col))


def cross_modality_matching(
    df: pd.DataFrame,
    cell: str,
    gene_modality: str,
    min_positive_count: int = 1,
) -> MetricResult:
    """Evaluate compound-to-gene-modality matching inside one cell type."""
    compound = df[_condition_mask(df, cell, "compound")]
    gene = df[_condition_mask(df, cell, gene_modality)]
    if compound.empty or gene.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    compound_consensus = _consensus(
        compound,
        ["Metadata_Cell_type", "Metadata_modality", "Metadata_broad_sample"],
    )
    gene_consensus = _consensus(
        gene,
        ["Metadata_Cell_type", "Metadata_modality", "Metadata_broad_sample"],
    )
    gene_targets = {
        target
        for value in gene_consensus["Metadata_matching_targets"]
        for target in (value.split("|") if isinstance(value, str) and value else [])
    }
    if not gene_targets:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    compound_consensus = compound_consensus.copy()
    compound_consensus["Metadata_matching_targets"] = compound_consensus["Metadata_matching_targets"].apply(
        lambda value: "|".join(sorted(set(value.split("|")).intersection(gene_targets)))
        if isinstance(value, str) and value
        else ""
    )
    compound_consensus = compound_consensus[compound_consensus["Metadata_matching_targets"] != ""]
    gene_consensus = gene_consensus[gene_consensus["Metadata_matching_targets"] != ""]
    combined = pd.concat([compound_consensus, gene_consensus], ignore_index=True, join="inner").reset_index(drop=True)
    if combined.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    target_sets = [set(value.split("|")) if isinstance(value, str) and value else set() for value in combined["Metadata_matching_targets"]]
    modalities = combined["Metadata_modality"].to_numpy()
    sim = cosine_similarity_matrix(combined[feature_columns(combined)].to_numpy())

    records: list[dict[str, object]] = []
    for i, targets in enumerate(target_sets):
        if not targets:
            continue
        candidate_mask = modalities != modalities[i]
        positive_mask = np.array(
            [bool(targets.intersection(other)) for other in target_sets],
            dtype=bool,
        ) & candidate_mask
        if int(positive_mask.sum()) < min_positive_count:
            continue

        record = _base_record(combined, i)
        record.update(
            metric="cross_modality_matching",
            gene_modality=gene_modality,
            average_precision=average_precision(positive_mask[candidate_mask], sim[i, candidate_mask]),
            n_candidates=int(candidate_mask.sum()),
            n_positives=int(positive_mask.sum()),
        )
        records.append(record)

    query_scores = pd.DataFrame(records)
    return MetricResult(query_scores=query_scores, aggregate_scores=_aggregate(query_scores, "Metadata_matching_targets"))


def evaluate_multimodal_feature_dataframe(
    features: pd.DataFrame,
    metadata: pd.DataFrame,
    min_positive_count: int = 1,
) -> dict[str, pd.DataFrame]:
    """Run condition-aware multimodal benchmark metrics."""
    df = merge_features_with_metadata(features, metadata)

    summary_rows: list[dict[str, object]] = []
    replicate_queries: list[pd.DataFrame] = []
    negcon_queries: list[pd.DataFrame] = []
    within_queries: list[pd.DataFrame] = []
    cross_queries: list[pd.DataFrame] = []
    within_maps: list[pd.DataFrame] = []
    cross_maps: list[pd.DataFrame] = []

    cells = sorted(pd.Series(df["Metadata_Cell_type"]).dropna().unique())
    modalities = ["compound", "crispr", "orf"]
    for cell in cells:
        for modality in modalities:
            mask = _condition_mask(df, cell, modality)
            if not mask.any():
                continue

            condition = f"{cell}_{modality}"
            condition_df = df[mask].copy().reset_index(drop=True)
            replicate = replicate_retrieval(condition_df, min_positive_count=min_positive_count)
            negcon = negcon_challenge(condition_df, min_positive_count=min_positive_count)
            for metric_name, result in (("replicate_retrieval", replicate), ("negcon_challenge", negcon)):
                summary_rows.append(
                    {
                        "task": "perturbation_retrieval",
                        "condition": condition,
                        "cell": cell,
                        "modality": modality,
                        **summarize_metric(metric_name, result),
                    }
                )

            for result, target in ((replicate, replicate_queries), (negcon, negcon_queries)):
                if not result.query_scores.empty:
                    table = result.query_scores.copy()
                    table.insert(0, "condition", condition)
                    table.insert(1, "cell", cell)
                    table.insert(2, "modality", modality)
                    target.append(table)

            match = within_modality_matching(condition_df, min_positive_count=min_positive_count)
            summary_rows.append(
                {
                    "task": "within_modality_matching",
                    "condition": condition,
                    "cell": cell,
                    "modality": modality,
                    **summarize_metric("within_modality_matching", match),
                }
            )
            if not match.query_scores.empty:
                table = match.query_scores.copy()
                table.insert(0, "condition", condition)
                within_queries.append(table)
                map_table = match.aggregate_scores.copy()
                map_table.insert(0, "condition", condition)
                within_maps.append(map_table)

        for gene_modality in ("crispr", "orf"):
            cross = cross_modality_matching(df, cell, gene_modality, min_positive_count=min_positive_count)
            condition = f"{cell}_compound_to_{gene_modality}"
            summary_rows.append(
                {
                    "task": "cross_modality_matching",
                    "condition": condition,
                    "cell": cell,
                    "modality": f"compound->{gene_modality}",
                    **summarize_metric("cross_modality_matching", cross),
                }
            )
            if not cross.query_scores.empty:
                table = cross.query_scores.copy()
                table.insert(0, "condition", condition)
                cross_queries.append(table)
                map_table = cross.aggregate_scores.copy()
                map_table.insert(0, "condition", condition)
                cross_maps.append(map_table)

    def concat_or_empty(tables: list[pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()

    return {
        "merged_features": df,
        "summary": pd.DataFrame(summary_rows),
        "replicate_query": concat_or_empty(replicate_queries),
        "negcon_query": concat_or_empty(negcon_queries),
        "within_matching_query": concat_or_empty(within_queries),
        "within_matching_map": concat_or_empty(within_maps),
        "cross_modality_query": concat_or_empty(cross_queries),
        "cross_modality_map": concat_or_empty(cross_maps),
    }
