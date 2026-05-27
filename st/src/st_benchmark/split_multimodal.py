"""Split-aware multimodal CPJUMP1 evaluation."""

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
    return {str(gene).strip().upper()}


def _consensus(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Build median consensus profiles and retain one metadata row per group."""
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


def _query_record(df: pd.DataFrame, query_idx: int) -> dict[str, object]:
    row = df.iloc[query_idx]
    return {
        "query_index": query_idx,
        "Metadata_split": row.get("Metadata_split", ""),
        "Metadata_Cell_type": row.get("Metadata_Cell_type", ""),
        "Metadata_modality": row.get("Metadata_modality", ""),
        "Metadata_broad_sample": row.get("Metadata_broad_sample", ""),
        "Metadata_gene": row.get("Metadata_gene", np.nan),
        "Metadata_matching_targets": row.get("Metadata_matching_targets", ""),
    }


def _target_sets(df: pd.DataFrame) -> list[set[str]]:
    return [set(value.split("|")) if isinstance(value, str) and value else set() for value in df["Metadata_matching_targets"]]


def within_modality_matching_split(
    condition_df: pd.DataFrame,
    query_split: str | None,
    min_positive_count: int = 1,
) -> MetricResult:
    """Evaluate target/gene matching for a query split inside one modality."""
    if condition_df.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    modality = str(condition_df["Metadata_modality"].iloc[0])
    if modality == "orf":
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    candidate = _consensus(
        condition_df,
        ["Metadata_Cell_type", "Metadata_modality", "Metadata_broad_sample"],
    ).reset_index(drop=True)
    if candidate.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    if query_split is None:
        query = candidate.copy()
    else:
        query_rows = condition_df[condition_df["Metadata_split"] == query_split].copy()
        query = _consensus(
            query_rows,
            ["Metadata_Cell_type", "Metadata_modality", "Metadata_split", "Metadata_broad_sample"],
        ).reset_index(drop=True)
    if query.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    query_targets = _target_sets(query)
    candidate_targets = _target_sets(candidate)
    query_samples = query["Metadata_broad_sample"].to_numpy()
    candidate_samples = candidate["Metadata_broad_sample"].to_numpy()
    query_features = query[feature_columns(query)].to_numpy()
    candidate_features = candidate[feature_columns(candidate)].to_numpy()
    sim = cosine_similarity_matrix(np.vstack([query_features, candidate_features]))
    sim = sim[: len(query), len(query) :]

    records: list[dict[str, object]] = []
    for i, targets in enumerate(query_targets):
        if not targets:
            continue
        candidate_mask = candidate_samples != query_samples[i]
        positive_mask = np.array(
            [bool(targets.intersection(other)) for other in candidate_targets],
            dtype=bool,
        ) & candidate_mask
        if int(positive_mask.sum()) < min_positive_count:
            continue

        record = _query_record(query, i)
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


def cross_modality_matching_split(
    df: pd.DataFrame,
    cell: str,
    gene_modality: str,
    query_split: str | None,
    min_positive_count: int = 1,
) -> MetricResult:
    """Evaluate directional compound-to-gene-modality matching for a query split."""
    compound = df[_condition_mask(df, cell, "compound")]
    gene = df[_condition_mask(df, cell, gene_modality)]
    if compound.empty or gene.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    if query_split is None:
        compound_query_rows = compound
    else:
        compound_query_rows = compound[compound["Metadata_split"] == query_split]
    compound_query = _consensus(
        compound_query_rows,
        ["Metadata_Cell_type", "Metadata_modality", "Metadata_split", "Metadata_broad_sample"]
        if query_split is not None
        else ["Metadata_Cell_type", "Metadata_modality", "Metadata_broad_sample"],
    ).reset_index(drop=True)
    gene_candidate = _consensus(
        gene,
        ["Metadata_Cell_type", "Metadata_modality", "Metadata_broad_sample"],
    ).reset_index(drop=True)
    if compound_query.empty or gene_candidate.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    gene_targets = {
        target
        for value in gene_candidate["Metadata_matching_targets"]
        for target in (value.split("|") if isinstance(value, str) and value else [])
    }
    compound_query = compound_query.copy()
    compound_query["Metadata_matching_targets"] = compound_query["Metadata_matching_targets"].apply(
        lambda value: "|".join(sorted(set(value.split("|")).intersection(gene_targets)))
        if isinstance(value, str) and value
        else ""
    )
    compound_query = compound_query[compound_query["Metadata_matching_targets"] != ""].reset_index(drop=True)
    gene_candidate = gene_candidate[gene_candidate["Metadata_matching_targets"] != ""].reset_index(drop=True)
    if compound_query.empty or gene_candidate.empty:
        return MetricResult(pd.DataFrame(), pd.DataFrame())

    query_targets = _target_sets(compound_query)
    candidate_targets = _target_sets(gene_candidate)
    query_features = compound_query[feature_columns(compound_query)].to_numpy()
    candidate_features = gene_candidate[feature_columns(gene_candidate)].to_numpy()
    sim = cosine_similarity_matrix(np.vstack([query_features, candidate_features]))
    sim = sim[: len(compound_query), len(compound_query) :]

    records: list[dict[str, object]] = []
    for i, targets in enumerate(query_targets):
        if not targets:
            continue
        positive_mask = np.array(
            [bool(targets.intersection(other)) for other in candidate_targets],
            dtype=bool,
        )
        if int(positive_mask.sum()) < min_positive_count:
            continue

        record = _query_record(compound_query, i)
        record.update(
            metric="cross_modality_matching",
            gene_modality=gene_modality,
            query_modality="compound",
            candidate_modality=gene_modality,
            average_precision=average_precision(positive_mask, sim[i]),
            n_candidates=int(len(gene_candidate)),
            n_positives=int(positive_mask.sum()),
        )
        records.append(record)

    query_scores = pd.DataFrame(records)
    return MetricResult(query_scores=query_scores, aggregate_scores=_aggregate(query_scores, "Metadata_matching_targets"))


def _summary_row(
    *,
    scope: str,
    task: str,
    condition: str,
    cell: str,
    modality: str,
    metric_name: str,
    result: MetricResult,
) -> dict[str, object]:
    return {
        "scope": scope,
        "task": task,
        "condition": condition,
        "cell": cell,
        "modality": modality,
        **summarize_metric(metric_name, result),
    }


def _append_query_table(
    tables: list[pd.DataFrame],
    result: MetricResult,
    *,
    scope: str,
    condition: str,
    cell: str,
    modality: str,
) -> None:
    if result.query_scores.empty:
        return
    table = result.query_scores.copy()
    table.insert(0, "scope", scope)
    table.insert(1, "condition", condition)
    table.insert(2, "cell", cell)
    table.insert(3, "modality", modality)
    tables.append(table)


def evaluate_split_multimodal_feature_dataframe(
    features: pd.DataFrame,
    metadata: pd.DataFrame,
    min_positive_count: int = 1,
) -> dict[str, pd.DataFrame]:
    """Run condition-aware multimodal metrics with all/train/val/test query scopes."""
    df = merge_features_with_metadata(features, metadata)
    scopes: list[tuple[str, str | None]] = [("all_queries", None)]
    if "Metadata_split" in df.columns:
        scopes.extend((f"{split}_queries", split) for split in ("train", "val", "test"))

    summary_rows: list[dict[str, object]] = []
    replicate_queries: list[pd.DataFrame] = []
    negcon_queries: list[pd.DataFrame] = []
    within_queries: list[pd.DataFrame] = []
    cross_queries: list[pd.DataFrame] = []

    cells = sorted(pd.Series(df["Metadata_Cell_type"]).dropna().unique())
    modalities = ["compound", "crispr", "orf"]
    for scope, query_split in scopes:
        for cell in cells:
            for modality in modalities:
                mask = _condition_mask(df, cell, modality)
                if not mask.any():
                    continue

                condition = f"{cell}_{modality}"
                condition_df = df[mask].copy().reset_index(drop=True)
                query_mask = None if query_split is None else (condition_df["Metadata_split"].to_numpy() == query_split)
                replicate = replicate_retrieval(
                    condition_df,
                    min_positive_count=min_positive_count,
                    query_mask=query_mask,
                )
                negcon = negcon_challenge(
                    condition_df,
                    min_positive_count=min_positive_count,
                    query_mask=query_mask,
                )
                for metric_name, result in (("replicate_retrieval", replicate), ("negcon_challenge", negcon)):
                    summary_rows.append(
                        _summary_row(
                            scope=scope,
                            task="perturbation_retrieval",
                            condition=condition,
                            cell=cell,
                            modality=modality,
                            metric_name=metric_name,
                            result=result,
                        )
                    )
                _append_query_table(replicate_queries, replicate, scope=scope, condition=condition, cell=cell, modality=modality)
                _append_query_table(negcon_queries, negcon, scope=scope, condition=condition, cell=cell, modality=modality)

                within = within_modality_matching_split(condition_df, query_split, min_positive_count=min_positive_count)
                summary_rows.append(
                    _summary_row(
                        scope=scope,
                        task="within_modality_matching",
                        condition=condition,
                        cell=cell,
                        modality=modality,
                        metric_name="within_modality_matching",
                        result=within,
                    )
                )
                _append_query_table(within_queries, within, scope=scope, condition=condition, cell=cell, modality=modality)

            for gene_modality in ("crispr", "orf"):
                cross = cross_modality_matching_split(
                    df,
                    cell,
                    gene_modality,
                    query_split,
                    min_positive_count=min_positive_count,
                )
                condition = f"{cell}_compound_to_{gene_modality}"
                modality = f"compound->{gene_modality}"
                summary_rows.append(
                    _summary_row(
                        scope=scope,
                        task="cross_modality_matching",
                        condition=condition,
                        cell=cell,
                        modality=modality,
                        metric_name="cross_modality_matching",
                        result=cross,
                    )
                )
                _append_query_table(cross_queries, cross, scope=scope, condition=condition, cell=cell, modality=modality)

    def concat_or_empty(tables: list[pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()

    return {
        "merged_features": df,
        "summary": pd.DataFrame(summary_rows),
        "replicate_query": concat_or_empty(replicate_queries),
        "negcon_query": concat_or_empty(negcon_queries),
        "within_matching_query": concat_or_empty(within_queries),
        "cross_modality_query": concat_or_empty(cross_queries),
    }
