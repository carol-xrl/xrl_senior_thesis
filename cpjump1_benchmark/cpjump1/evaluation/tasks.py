"""Three evaluation tasks: replicability, matching, cross-modality matching.

Each function takes profiles + config, returns (mAP_df, fraction_retrieved).
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from ..utils import get_metadata, get_featuredata
from .metrics import run_pipeline, calculate_mAP, calculate_fraction_retrieved
from .consensus import build_consensus


@dataclass
class EvalResult:
    """Result of a single evaluation task."""
    mAP_df: pd.DataFrame         # per-perturbation/target mAP
    fraction_retrieved: float    # fraction above corrected p threshold
    raw_result: pd.DataFrame     # run_pipeline raw output


def evaluate_replicability(
    profiles: pd.DataFrame,
    config,
    pos_sameby: list = None,
    pos_diffby: list = None,
) -> EvalResult:
    """Evaluate replicability: can we retrieve replicates of the same perturbation?

    Args:
        profiles: Well-level profiles with Metadata_negcon column.
        config: Config object with batch_size, null_size, q_threshold.
        pos_sameby: Positive pair definition (default: ["Metadata_broad_sample"]).
        pos_diffby: Additional positive constraint (default: []).

    Returns:
        EvalResult with mAP per perturbation and fraction retrieved.
    """
    if pos_sameby is None:
        pos_sameby = ["Metadata_broad_sample"]
    if pos_diffby is None:
        pos_diffby = []

    neg_sameby = ["Metadata_Plate"]
    neg_diffby = ["Metadata_negcon"]

    meta = get_metadata(profiles)
    feats = get_featuredata(profiles).values

    result = run_pipeline(
        meta, feats,
        pos_sameby=pos_sameby,
        pos_diffby=pos_diffby,
        neg_sameby=neg_sameby,
        neg_diffby=neg_diffby,
        anti_match=False,
        batch_size=config.batch_size,
        null_size=config.null_size,
    )

    # Remove negcon rows from results
    result = result.query("Metadata_negcon == 0").reset_index(drop=True)

    mAP_df = calculate_mAP(result, pos_sameby, config.q_threshold)
    fr = calculate_fraction_retrieved(mAP_df)

    return EvalResult(mAP_df=mAP_df, fraction_retrieved=fr, raw_result=result)


def evaluate_matching(
    consensus_df: pd.DataFrame,
    config,
    anti_match: bool = True,
    multilabel: bool = True,
) -> EvalResult:
    """Evaluate within-modality matching: do perturbations targeting the same gene cluster?

    Args:
        consensus_df: Consensus profiles with Metadata_matching_target column.
        config: Config object.
        anti_match: Use absolute cosine similarity (default True for compounds).
        multilabel: Whether matching_target is a list (True for compounds).

    Returns:
        EvalResult with mAP per target gene and fraction retrieved.
    """
    pos_sameby = ["Metadata_matching_target"]
    pos_diffby = []
    neg_sameby = []
    neg_diffby = ["Metadata_matching_target"]

    meta = get_metadata(consensus_df)
    feats = get_featuredata(consensus_df).values

    multilabel_col = "Metadata_matching_target" if multilabel else None

    result = run_pipeline(
        meta, feats,
        pos_sameby=pos_sameby,
        pos_diffby=pos_diffby,
        neg_sameby=neg_sameby,
        neg_diffby=neg_diffby,
        anti_match=anti_match,
        batch_size=config.batch_size,
        null_size=config.null_size,
        multilabel_col=multilabel_col,
    )

    mAP_df = calculate_mAP(result, pos_sameby, config.q_threshold)
    fr = calculate_fraction_retrieved(mAP_df)

    return EvalResult(mAP_df=mAP_df, fraction_retrieved=fr, raw_result=result)


def evaluate_cross_modality(
    compound_consensus: pd.DataFrame,
    gene_consensus: pd.DataFrame,
    config,
) -> EvalResult:
    """Evaluate cross-modality matching: do compounds and gene perturbations
    targeting the same gene cluster together?

    Args:
        compound_consensus: Compound consensus profiles with Metadata_matching_target (list).
        gene_consensus: Gene perturbation consensus profiles with Metadata_matching_target (str).
        config: Config object.

    Returns:
        EvalResult with mAP per target gene and fraction retrieved.
    """
    # Drop rows without a matching target (residual negcon/empty)
    gene_consensus = gene_consensus.dropna(
        subset=["Metadata_matching_target"]
    ).reset_index(drop=True).copy()

    # Ensure gene matching_target is a list (for multilabel matcher compatibility)
    gene_consensus["Metadata_matching_target"] = gene_consensus[
        "Metadata_matching_target"
    ].apply(lambda x: [x] if isinstance(x, str) else x)

    # Filter compound targets to only genes perturbed by this gene modality
    perturbed_genes = list(set(
        g for targets in gene_consensus.Metadata_matching_target for g in targets
    ))

    filtered_targets = (
        compound_consensus[["Metadata_broad_sample", "Metadata_matching_target"]]
        .copy()
        .explode("Metadata_matching_target")
        .query("Metadata_matching_target == @perturbed_genes")
        .reset_index(drop=True)
        .groupby("Metadata_broad_sample")
        .Metadata_matching_target.apply(list)
        .reset_index()
    )

    compound_filtered = compound_consensus.drop(
        columns=["Metadata_matching_target"]
    ).merge(filtered_targets, on="Metadata_broad_sample", how="inner")

    # Concatenate compound + gene profiles
    combined = pd.concat(
        [compound_filtered, gene_consensus], ignore_index=True, join="inner"
    )

    pos_sameby = ["Metadata_matching_target"]
    pos_diffby = ["Metadata_modality"]
    neg_sameby = []
    neg_diffby = ["Metadata_matching_target", "Metadata_modality"]

    meta = get_metadata(combined)
    feats = get_featuredata(combined).values

    result = run_pipeline(
        meta, feats,
        pos_sameby=pos_sameby,
        pos_diffby=pos_diffby,
        neg_sameby=neg_sameby,
        neg_diffby=neg_diffby,
        anti_match=True,
        batch_size=config.batch_size,
        null_size=config.null_size,
        multilabel_col="Metadata_matching_target",
    )

    mAP_df = calculate_mAP(result, pos_sameby, config.q_threshold)
    fr = calculate_fraction_retrieved(mAP_df)

    return EvalResult(mAP_df=mAP_df, fraction_retrieved=fr, raw_result=result)


# --- Helper functions for building consensus with proper filtering ---

def build_replicable_consensus(
    profiles: pd.DataFrame,
    rep_result: EvalResult,
    group_by: str = "Metadata_broad_sample",
) -> pd.DataFrame:
    """Build consensus from replicable perturbations only.

    1. Remove negcon and empty wells
    2. Keep only replicable perturbations (above_q_threshold)
    3. Compute median consensus
    """
    # Remove negcon + empty
    df = (
        profiles.query('Metadata_control_type != "negcon"')
        .dropna(subset=["Metadata_broad_sample"])
        .reset_index(drop=True)
    )

    # Filter to replicable only
    replicable = list(
        rep_result.mAP_df[rep_result.mAP_df.above_q_threshold == True][group_by]
    )
    df = df.query(f"{group_by} == @replicable").reset_index(drop=True)

    return build_consensus(df, group_by)


def add_compound_targets(
    consensus_df: pd.DataFrame,
    annotations: pd.DataFrame,
) -> pd.DataFrame:
    """Merge compound -> target gene annotations onto consensus profiles."""
    return (
        consensus_df
        .merge(annotations, on="Metadata_broad_sample", how="left")
        .assign(Metadata_matching_target=lambda x: x.Metadata_target_list.str.split("|"))
        .drop(columns=["Metadata_target_list"])
    )


def filter_sister_guides(consensus_df: pd.DataFrame) -> pd.DataFrame:
    """Remove genes that have only one guide/reagent (no sister)."""
    gene_counts = consensus_df.Metadata_gene.value_counts().reset_index()
    genes_without_sister = gene_counts.query("Metadata_gene == 1")["index"].to_list()
    return (
        consensus_df
        .query("Metadata_gene != @genes_without_sister")
        .reset_index(drop=True)
    )
