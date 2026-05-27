#!/usr/bin/env python
"""Plot feature-normalization ablations from transform comparison CSVs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))


METRIC_LABELS = {
    "replicate_retrieval": "Replicate",
    "negcon_challenge": "Negcon",
    "target_retrieval": "Target",
}

VARIANT_LABELS = {
    "raw_l2": "Raw L2",
    "global_zscore_l2": "Global z",
    "plate_center_l2": "Plate center",
    "plate_zscore_l2": "Plate z",
    "negcon_center_l2": "Negcon center",
    "negcon_zscore_l2": "Negcon z",
}


def prepare_matplotlib_cache(output_path: Path) -> None:
    """Keep matplotlib cache inside the output tree."""
    cache_dir = output_path.parent / ".matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))


def plot_transform_comparison(comparison_csv: Path, output_png: Path) -> Path:
    """Create a grouped bar chart of mean AP by transform variant."""
    prepare_matplotlib_cache(output_png)
    import matplotlib.pyplot as plt
    import numpy as np

    frame = pd.read_csv(comparison_csv)
    frame = frame[frame["metric"].isin(METRIC_LABELS)].copy()
    frame["metric_label"] = frame["metric"].map(METRIC_LABELS)
    frame["variant_label"] = frame["variant"].map(VARIANT_LABELS).fillna(frame["variant"])

    ordered_variants = [variant for variant in VARIANT_LABELS if variant in set(frame["variant"])]
    ordered_metrics = [metric for metric in METRIC_LABELS if metric in set(frame["metric"])]
    pivot = (
        frame.pivot(index="variant", columns="metric", values="mean_ap")
        .reindex(index=ordered_variants, columns=ordered_metrics)
        .rename(index=VARIANT_LABELS, columns=METRIC_LABELS)
    )

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(pivot.index))
    width = 0.24
    colors = ["#4C78A8", "#54A24B", "#E45756"]
    offsets = np.linspace(-width, width, len(pivot.columns))

    for offset, metric, color in zip(offsets, pivot.columns, colors, strict=True):
        values = pivot[metric].to_numpy(dtype=float)
        bars = ax.bar(x + offset, values, width=width, label=metric, color=color)
        for bar, value in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.008,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    ax.set_ylim(0, max(0.55, float(pivot.max().max()) + 0.08))
    ax.set_ylabel("Mean AP")
    ax.set_xlabel("")
    ax.set_title("DINOv2 feature-normalization ablation")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=25, ha="right")
    ax.legend(frameon=False, ncols=3, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_png, dpi=220)
    plt.close(fig)
    return output_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_path = plot_transform_comparison(Path(args.comparison), Path(args.output))
    print(f"transform comparison figure: {output_path}")


if __name__ == "__main__":
    main()
