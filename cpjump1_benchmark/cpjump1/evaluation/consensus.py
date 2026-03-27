"""Build consensus profiles from well-level data."""

import pandas as pd
from ..utils import get_metacols, get_featurecols, get_metadata


def build_consensus(profiles_df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    """Compute median consensus profiles grouped by `group_by`.

    Returns one row per unique value of `group_by`, with metadata
    from the first occurrence and features as the group median.
    """
    metadata_df = get_metadata(profiles_df).drop_duplicates(subset=[group_by])
    feature_cols = [group_by] + get_featurecols(profiles_df)
    agg_df = (
        profiles_df[feature_cols]
        .groupby([group_by])
        .median()
        .reset_index()
    )
    return metadata_df.merge(agg_df, on=group_by)
