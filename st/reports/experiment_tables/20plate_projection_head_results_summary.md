# 20-Plate Projection-Head Result Summary

This table compares the strongest frozen DINOv2-B/14 baseline with two projection-head adaptations.

- Sample Proxy-CE uses exact perturbation/sample identifiers as labels and is intended to improve replicate retrieval.
- Bio-target Proxy-CE uses compound target genes and ORF/CRISPR perturbation genes as labels. It is an annotation-supervised upper bound for cross-modality matching, not a label-free baseline.

## Key Metrics

| condition | metric | bio_target_proxy_AP | frozen_B_plate_zscore_AP | sample_proxy_AP |
| --- | --- | --- | --- | --- |
| A549_compound | replicate_retrieval | 0.3987 | 0.3111 | 0.4650 |
| A549_compound_to_crispr | cross_modality_matching | 0.8256 | 0.0347 | 0.0311 |
| A549_compound_to_orf | cross_modality_matching | 0.8335 | 0.0357 | 0.0324 |
| A549_crispr | replicate_retrieval | 0.1691 | 0.0447 | 0.2126 |
| A549_orf | replicate_retrieval | 0.0567 | 0.0728 | 0.0729 |
| U2OS_compound | replicate_retrieval | 0.3340 | 0.2151 | 0.4195 |
| U2OS_compound_to_crispr | cross_modality_matching | 0.8067 | 0.0319 | 0.0290 |
| U2OS_compound_to_orf | cross_modality_matching | 0.8312 | 0.0428 | 0.0279 |
| U2OS_crispr | replicate_retrieval | 0.1886 | 0.0645 | 0.2468 |
| U2OS_orf | replicate_retrieval | 0.1140 | 0.1491 | 0.1634 |

## Interpretation

- Sample Proxy-CE strongly improves compound and CRISPR replicate retrieval, but does not improve cross-modality matching.
- Bio-target Proxy-CE strongly improves cross-modality matching because it directly trains on shared target/gene labels.
- These two heads answer different questions: perturbation identity supervision versus biological target supervision.
