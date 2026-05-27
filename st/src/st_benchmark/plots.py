"""Small plotting helpers for ST benchmark metric outputs."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def _prepare_matplotlib_cache(output_path: Path) -> None:
    cache_dir = output_path.parent / ".matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))


def plot_summary(summary_csv: str | Path, output_png: str | Path) -> Path:
    """Plot mean AP summary bars."""
    output_png = Path(output_png)
    _prepare_matplotlib_cache(output_png)
    import matplotlib.pyplot as plt

    summary = pd.read_csv(summary_csv)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(summary["metric"], summary["mean_ap"], color=["#4C78A8", "#54A24B", "#E45756"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Mean AP")
    ax.set_xlabel("")
    ax.set_title("ST benchmark metric summary")
    ax.tick_params(axis="x", rotation=20)
    for idx, row in summary.iterrows():
        if pd.notna(row["mean_ap"]):
            ax.text(idx, row["mean_ap"] + 0.02, f"{row['mean_ap']:.3f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)
    return output_png


def plot_artifact(artifact_csv: str | Path, output_png: str | Path) -> Path:
    """Plot artifact category mean similarities."""
    output_png = Path(output_png)
    _prepare_matplotlib_cache(output_png)
    import matplotlib.pyplot as plt

    artifact = pd.read_csv(artifact_csv)
    plot_df = artifact.dropna(subset=["n_pairs"]).copy()
    output_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(plot_df["category"], plot_df["mean_similarity"], color="#F58518")
    ax.set_ylabel("Mean cosine similarity")
    ax.set_xlabel("")
    ax.set_title("Artifact sensitivity categories")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)
    return output_png
