"""Core evaluation: run_pipeline, mAP, fraction_retrieved.

Wraps the copairs library for cosine similarity → AP → null distribution → p-values.
"""

import numpy as np
import pandas as pd
import itertools
from copairs.map import (
    aggregate,
    create_matcher,
    build_rank_list_multi,
    build_rank_lists,
    results_to_dframe,
)
from copairs.compute import cosine_indexed
import copairs.compute_np as backend
from copairs.matching import dict_to_dframe


def compute_similarities(pairs, feats, batch_size, anti_match=False):
    dist_df = pairs[["ix1", "ix2"]].drop_duplicates().copy()
    dist_df["dist"] = cosine_indexed(feats, dist_df.values, batch_size)
    if anti_match:
        dist_df["dist"] = np.abs(dist_df["dist"])
    return pairs.merge(dist_df, on=["ix1", "ix2"])


def run_pipeline(
    meta: pd.DataFrame,
    feats: np.ndarray,
    pos_sameby: list,
    pos_diffby: list,
    neg_sameby: list,
    neg_diffby: list,
    null_size: int,
    anti_match: bool = False,
    multilabel_col: str = None,
    batch_size: int = 20000,
) -> pd.DataFrame:
    """Core evaluation pipeline wrapping copairs.

    Computes cosine similarity, builds rank lists,
    calculates AP scores with permutation-based p-values.
    """
    meta = meta.reset_index(drop=True).copy()

    matcher = create_matcher(
        meta, pos_sameby, pos_diffby, neg_sameby, neg_diffby, multilabel_col
    )

    dict_pairs = matcher.get_all_pairs(sameby=pos_sameby, diffby=pos_diffby)
    pos_pairs = dict_to_dframe(dict_pairs, pos_sameby)
    dict_pairs = matcher.get_all_pairs(sameby=neg_sameby, diffby=neg_diffby)
    neg_pairs = set(itertools.chain.from_iterable(dict_pairs.values()))
    neg_pairs = pd.DataFrame(neg_pairs, columns=["ix1", "ix2"])

    pos_pairs = compute_similarities(pos_pairs, feats, batch_size, anti_match)
    neg_pairs = compute_similarities(neg_pairs, feats, batch_size, anti_match)

    if multilabel_col and multilabel_col in pos_sameby:
        rel_k_list = build_rank_list_multi(pos_pairs, neg_pairs, multilabel_col)
    else:
        rel_k_list = build_rank_lists(pos_pairs, neg_pairs)

    ap_scores = rel_k_list.apply(backend.compute_ap)
    ap_scores = np.concatenate(ap_scores.values)
    null_dists = backend.compute_null_dists(rel_k_list, null_size)
    p_values = backend.compute_p_values(null_dists, ap_scores, null_size)

    result = results_to_dframe(
        meta, rel_k_list.index, p_values, ap_scores, multilabel_col
    )
    return result


def calculate_mAP(result: pd.DataFrame, pos_sameby: list, threshold: float = 0.05):
    """Aggregate per-query AP into per-group mAP."""
    return aggregate(result, pos_sameby, threshold=threshold).rename(
        columns={"average_precision": "mean_average_precision"}
    )


def calculate_fraction_retrieved(mAP_df: pd.DataFrame) -> float:
    """Fraction of groups passing the corrected p-value threshold."""
    return len(mAP_df.query("above_q_threshold == True")) / len(mAP_df)
