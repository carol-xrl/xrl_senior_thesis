"""
CPJUMP1 Benchmark Evaluation Script

Clean reimplementation of notebooks 1.0, 1.1, 1.2, 1.3.
Usage:
    cd <project_root>
    python -m cpjump1_benchmark.scripts.evaluate [--config configs/default.yaml]
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

# Add parent dir to path so cpjump1 package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cpjump1.config import load_config
from cpjump1.data.loader import (
    load_experiment_metadata,
    load_profiles,
    load_compound_annotations,
)
from cpjump1.evaluation.tasks import (
    evaluate_replicability,
    evaluate_matching,
    evaluate_cross_modality,
    build_replicable_consensus,
    add_compound_targets,
    filter_sister_guides,
)


def main():
    parser = argparse.ArgumentParser(description="CPJUMP1 Benchmark Evaluation")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--output", default="cpjump1_benchmark/output", help="Output directory")
    args = parser.parse_args()

    config = load_config(args.config)
    root = args.root
    output_dir = os.path.join(root, args.output)
    os.makedirs(output_dir, exist_ok=True)

    # Set random seed for reproducibility
    np.random.seed(config.random_seed)

    # Load experiment metadata and compound annotations
    experiment_df = load_experiment_metadata(config, root)
    compound_annotations = load_compound_annotations(config, root)

    # Result accumulators
    rep_rows = []       # replicability fraction retrieved
    match_rows = []     # matching fraction retrieved
    cross_rows = []     # cross-modality fraction retrieved
    rep_maps = []       # replicability mAP per perturbation
    match_maps = []     # matching mAP per target
    cross_maps = []     # cross-modality mAP per target

    # Cache: store consensus profiles to avoid recomputation
    consensus_cache = {}  # key: (modality, cell, time_label)
    rep_cache = {}        # key: (modality, cell, time_label)

    cells = experiment_df.Cell_type.unique().tolist()

    # =========================================================
    # 1. Replicability + Within-Modality Matching
    # =========================================================
    for cell in cells:
        for modality in ["compound", "crispr", "orf"]:
            for time_label in ["short", "long"]:
                key = (modality, cell, time_label)
                hours = config.hours_for(modality, time_label)
                desc = f"{modality}_{cell}_{time_label}"

                # Load profiles
                profiles = load_profiles(
                    experiment_df, config, cell, modality, time_label, root
                )
                if profiles.empty:
                    print(f"  Skipping {desc}: no data")
                    continue

                # --- Replicability ---
                print(f"Computing {desc} replicability")
                rep_result = evaluate_replicability(profiles, config)
                rep_cache[key] = rep_result

                rep_rows.append({
                    "Description": desc,
                    "Modality": modality,
                    "Cell": cell,
                    "time": time_label,
                    "timepoint": hours,
                    "fr": round(rep_result.fraction_retrieved, 3),
                })

                mAP_df = rep_result.mAP_df.copy()
                mAP_df["Description"] = desc
                mAP_df["Modality"] = modality
                mAP_df["Cell"] = cell
                mAP_df["time"] = time_label
                mAP_df["timepoint"] = hours
                rep_maps.append(mAP_df)

                # --- Build consensus ---
                consensus_df = build_replicable_consensus(profiles, rep_result)
                consensus_cache[key] = consensus_df

                # --- Within-modality matching ---
                if modality == "compound":
                    # Add target annotations (multi-label)
                    consensus_with_targets = add_compound_targets(
                        consensus_df, compound_annotations
                    )
                    consensus_cache[key] = consensus_with_targets

                    print(f"Computing {desc} matching")
                    match_result = evaluate_matching(
                        consensus_with_targets, config,
                        anti_match=True, multilabel=True,
                    )
                    match_rows.append({
                        "Description": desc,
                        "Modality": modality,
                        "Cell": cell,
                        "time": time_label,
                        "timepoint": hours,
                        "fr": round(match_result.fraction_retrieved, 3),
                    })
                    m_df = match_result.mAP_df.copy()
                    m_df["Description"] = desc
                    m_df["Modality"] = modality
                    m_df["Cell"] = cell
                    m_df["time"] = time_label
                    m_df["timepoint"] = hours
                    match_maps.append(m_df)

                elif modality == "crispr":
                    # Filter sister guides for matching
                    consensus_for_matching = filter_sister_guides(consensus_df)
                    if len(consensus_for_matching) > 0:
                        print(f"Computing {desc} matching")
                        match_result = evaluate_matching(
                            consensus_for_matching, config,
                            anti_match=False, multilabel=False,
                        )
                        match_rows.append({
                            "Description": desc,
                            "Modality": modality,
                            "Cell": cell,
                            "time": time_label,
                            "timepoint": hours,
                            "fr": round(match_result.fraction_retrieved, 3),
                        })
                        m_df = match_result.mAP_df.copy()
                        m_df["Description"] = desc
                        m_df["Modality"] = modality
                        m_df["Cell"] = cell
                        m_df["time"] = time_label
                        m_df["timepoint"] = hours
                        match_maps.append(m_df)

                # orf: no within-modality matching (no sister reagents)

    # =========================================================
    # 2. Cross-Modality Matching: compound × {crispr, orf}
    # =========================================================
    for cell in cells:
        for comp_time in ["short", "long"]:
            comp_key = ("compound", cell, comp_time)
            if comp_key not in consensus_cache:
                continue
            comp_consensus = consensus_cache[comp_key]
            comp_hours = config.hours_for("compound", comp_time)

            for gene_mod in ["crispr", "orf"]:
                for gene_time in ["short", "long"]:
                    gene_key = (gene_mod, cell, gene_time)
                    if gene_key not in consensus_cache:
                        continue
                    gene_consensus = consensus_cache[gene_key]
                    gene_hours = config.hours_for(gene_mod, gene_time)

                    desc = f"compound_{cell}_{comp_time}-{gene_mod}_{cell}_{gene_time}"
                    print(f"Computing {desc} matching")

                    cross_result = evaluate_cross_modality(
                        comp_consensus, gene_consensus, config
                    )

                    cross_rows.append({
                        "Description": desc,
                        "Modality1": f"compound_{comp_time}",
                        "Modality2": f"{gene_mod}_{gene_time}",
                        "Cell": cell,
                        "fr": round(cross_result.fraction_retrieved, 3),
                    })
                    c_df = cross_result.mAP_df.copy()
                    c_df["Description"] = desc
                    c_df["Modality1"] = f"compound_{comp_time}"
                    c_df["Modality2"] = f"{gene_mod}_{gene_time}"
                    c_df["Cell"] = cell
                    cross_maps.append(c_df)

    # =========================================================
    # 3. ORF Replicability Variants (notebooks 1.1, 1.2)
    # =========================================================
    orf_same_rows, orf_same_maps = [], []
    orf_diff_rows, orf_diff_maps = [], []

    for cell in cells:
        for time_label in ["short", "long"]:
            hours = config.hours_for("orf", time_label)
            desc = f"orf_{cell}_{time_label}"

            profiles = load_profiles(
                experiment_df, config, cell, "orf", time_label, root
            )
            if profiles.empty:
                continue

            # Same-well replicability (notebook 1.1)
            print(f"Computing {desc} replicability (same-well)")
            same_result = evaluate_replicability(
                profiles, config,
                pos_sameby=["Metadata_broad_sample", "Metadata_Well"],
            )
            orf_same_rows.append({
                "Description": desc,
                "Modality": "orf",
                "Cell": cell,
                "time": time_label,
                "timepoint": hours,
                "fr": round(same_result.fraction_retrieved, 3),
            })
            s_df = same_result.mAP_df.copy()
            s_df["Description"] = desc
            s_df["Modality"] = "orf"
            s_df["Cell"] = cell
            s_df["time"] = time_label
            s_df["timepoint"] = hours
            orf_same_maps.append(s_df)

            # Different-well replicability (notebook 1.2)
            print(f"Computing {desc} replicability (diff-well)")
            diff_result = evaluate_replicability(
                profiles, config,
                pos_sameby=["Metadata_broad_sample"],
                pos_diffby=["Metadata_Well"],
            )
            orf_diff_rows.append({
                "Description": desc,
                "Modality": "orf",
                "Cell": cell,
                "time": time_label,
                "timepoint": hours,
                "fr": round(diff_result.fraction_retrieved, 3),
            })
            d_df = diff_result.mAP_df.copy()
            d_df["Description"] = desc
            d_df["Modality"] = "orf"
            d_df["Cell"] = cell
            d_df["time"] = time_label
            d_df["timepoint"] = hours
            orf_diff_maps.append(d_df)

    # =========================================================
    # 4. Save Results
    # =========================================================
    def save(dfs, rows, map_name, fr_name):
        if dfs:
            pd.concat(dfs, ignore_index=True).to_csv(
                os.path.join(output_dir, map_name), index=False
            )
        if rows:
            pd.DataFrame(rows).to_csv(
                os.path.join(output_dir, fr_name), index=False
            )

    save(rep_maps, rep_rows,
         "cellprofiler_replicability_map.csv",
         "cellprofiler_replicability_fr.csv")
    save(match_maps, match_rows,
         "cellprofiler_matching_map.csv",
         "cellprofiler_matching_fr.csv")
    save(cross_maps, cross_rows,
         "cellprofiler_gene_compound_matching_map.csv",
         "cellprofiler_gene_compound_matching_fr.csv")
    save(orf_same_maps, orf_same_rows,
         "cellprofiler_replicability_orf_same_map.csv",
         "cellprofiler_replicability_orf_same_fr.csv")
    save(orf_diff_maps, orf_diff_rows,
         "cellprofiler_replicability_orf_different_map.csv",
         "cellprofiler_replicability_orf_different_fr.csv")

    print(f"\nResults saved to {output_dir}/")

    # Print summary
    print("\n=== Replicability FR ===")
    for r in rep_rows:
        print(f"  {r['Description']:30s} {r['fr']:.3f}")

    print("\n=== Matching FR ===")
    for r in match_rows:
        print(f"  {r['Description']:30s} {r['fr']:.3f}")

    print("\n=== Cross-Modality FR ===")
    for r in cross_rows:
        print(f"  {r['Description']:45s} {r['fr']:.3f}")


if __name__ == "__main__":
    main()
