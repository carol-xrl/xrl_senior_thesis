"""Shared utility functions for column splitting and profile operations."""

import pandas as pd
import numpy as np


def get_metacols(df: pd.DataFrame) -> list:
    return [c for c in df.columns if c.startswith("Metadata_")]


def get_featurecols(df: pd.DataFrame) -> list:
    return [c for c in df.columns if not c.startswith("Metadata")]


def get_metadata(df: pd.DataFrame) -> pd.DataFrame:
    return df[get_metacols(df)]


def get_featuredata(df: pd.DataFrame) -> pd.DataFrame:
    return df[get_featurecols(df)]
