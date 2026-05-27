# 20-Plate Multimodal Result Summary

This report is generated from `evaluate_multimodal_features.py` outputs. It updates automatically when completed 20-plate runs are present under `st/outputs/metrics`.

## Cross-Modality Matching

| model | input_transform | condition | cell | modality | mean_ap | median_ap | n_queries |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dinov2-vitb14 | negcon_zscore_l2 | A549_compound_to_crispr | A549 | compound->crispr | 0.0332 | 0.0153 | 611 |
| dinov2-vitb14 | negcon_zscore_l2 | A549_compound_to_orf | A549 | compound->orf | 0.0356 | 0.0159 | 466 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_compound_to_crispr | U2OS | compound->crispr | 0.0339 | 0.0148 | 611 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_compound_to_orf | U2OS | compound->orf | 0.0399 | 0.0169 | 466 |
| dinov2-vitb14 | plate_zscore_l2 | A549_compound_to_crispr | A549 | compound->crispr | 0.0347 | 0.0155 | 611 |
| dinov2-vitb14 | plate_zscore_l2 | A549_compound_to_orf | A549 | compound->orf | 0.0357 | 0.0152 | 466 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_compound_to_crispr | U2OS | compound->crispr | 0.0319 | 0.0144 | 611 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_compound_to_orf | U2OS | compound->orf | 0.0428 | 0.0164 | 466 |
| dinov2-vitb14 | raw_l2 | A549_compound_to_crispr | A549 | compound->crispr | 0.0338 | 0.0147 | 611 |
| dinov2-vitb14 | raw_l2 | A549_compound_to_orf | A549 | compound->orf | 0.0305 | 0.0152 | 466 |
| dinov2-vitb14 | raw_l2 | U2OS_compound_to_crispr | U2OS | compound->crispr | 0.0269 | 0.0148 | 611 |
| dinov2-vitb14 | raw_l2 | U2OS_compound_to_orf | U2OS | compound->orf | 0.0354 | 0.0158 | 466 |
| dinov2-vits14 | negcon_zscore_l2 | A549_compound_to_crispr | A549 | compound->crispr | 0.0343 | 0.0151 | 611 |
| dinov2-vits14 | negcon_zscore_l2 | A549_compound_to_orf | A549 | compound->orf | 0.0366 | 0.0152 | 466 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_compound_to_crispr | U2OS | compound->crispr | 0.0355 | 0.0147 | 611 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_compound_to_orf | U2OS | compound->orf | 0.0394 | 0.0161 | 466 |
| dinov2-vits14 | plate_zscore_l2 | A549_compound_to_crispr | A549 | compound->crispr | 0.0376 | 0.0153 | 611 |
| dinov2-vits14 | plate_zscore_l2 | A549_compound_to_orf | A549 | compound->orf | 0.0364 | 0.0151 | 466 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_compound_to_crispr | U2OS | compound->crispr | 0.0357 | 0.0149 | 611 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_compound_to_orf | U2OS | compound->orf | 0.0399 | 0.0158 | 466 |
| dinov2-vits14 | raw_l2 | A549_compound_to_crispr | A549 | compound->crispr | 0.0331 | 0.0144 | 611 |
| dinov2-vits14 | raw_l2 | A549_compound_to_orf | A549 | compound->orf | 0.0307 | 0.0149 | 466 |
| dinov2-vits14 | raw_l2 | U2OS_compound_to_crispr | U2OS | compound->crispr | 0.0318 | 0.0152 | 611 |
| dinov2-vits14 | raw_l2 | U2OS_compound_to_orf | U2OS | compound->orf | 0.0331 | 0.0154 | 466 |

## Perturbation Retrieval

| model | input_transform | condition | cell | modality | negcon_challenge | replicate_retrieval |
| --- | --- | --- | --- | --- | --- | --- |
| dinov2-vitb14 | negcon_zscore_l2 | A549_compound | A549 | compound | 0.4794 | 0.2929 |
| dinov2-vitb14 | negcon_zscore_l2 | A549_crispr | A549 | crispr | 0.2129 | 0.0406 |
| dinov2-vitb14 | negcon_zscore_l2 | A549_orf | A549 | orf | 0.1875 | 0.0716 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_compound | U2OS | compound | 0.3438 | 0.1926 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.2070 | 0.0594 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_orf | U2OS | orf | 0.2900 | 0.1486 |
| dinov2-vitb14 | plate_zscore_l2 | A549_compound | A549 | compound | 0.4628 | 0.3111 |
| dinov2-vitb14 | plate_zscore_l2 | A549_crispr | A549 | crispr | 0.1837 | 0.0447 |
| dinov2-vitb14 | plate_zscore_l2 | A549_orf | A549 | orf | 0.1854 | 0.0728 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_compound | U2OS | compound | 0.3511 | 0.2151 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.2057 | 0.0645 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_orf | U2OS | orf | 0.2936 | 0.1491 |
| dinov2-vitb14 | raw_l2 | A549_compound | A549 | compound | 0.3870 | 0.2913 |
| dinov2-vitb14 | raw_l2 | A549_crispr | A549 | crispr | 0.1006 | 0.0275 |
| dinov2-vitb14 | raw_l2 | A549_orf | A549 | orf | 0.1642 | 0.0592 |
| dinov2-vitb14 | raw_l2 | U2OS_compound | U2OS | compound | 0.3111 | 0.2248 |
| dinov2-vitb14 | raw_l2 | U2OS_crispr | U2OS | crispr | 0.1712 | 0.0532 |
| dinov2-vitb14 | raw_l2 | U2OS_orf | U2OS | orf | 0.2160 | 0.1166 |
| dinov2-vits14 | negcon_zscore_l2 | A549_compound | A549 | compound | 0.4819 | 0.2895 |
| dinov2-vits14 | negcon_zscore_l2 | A549_crispr | A549 | crispr | 0.2377 | 0.0405 |
| dinov2-vits14 | negcon_zscore_l2 | A549_orf | A549 | orf | 0.2098 | 0.0766 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_compound | U2OS | compound | 0.3357 | 0.1848 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.2063 | 0.0602 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_orf | U2OS | orf | 0.2728 | 0.1380 |
| dinov2-vits14 | plate_zscore_l2 | A549_compound | A549 | compound | 0.4699 | 0.3114 |
| dinov2-vits14 | plate_zscore_l2 | A549_crispr | A549 | crispr | 0.2004 | 0.0434 |
| dinov2-vits14 | plate_zscore_l2 | A549_orf | A549 | orf | 0.2087 | 0.0774 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_compound | U2OS | compound | 0.3445 | 0.2077 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.2074 | 0.0631 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_orf | U2OS | orf | 0.2757 | 0.1358 |
| dinov2-vits14 | raw_l2 | A549_compound | A549 | compound | 0.3968 | 0.2895 |
| dinov2-vits14 | raw_l2 | A549_crispr | A549 | crispr | 0.1162 | 0.0285 |
| dinov2-vits14 | raw_l2 | A549_orf | A549 | orf | 0.1733 | 0.0552 |
| dinov2-vits14 | raw_l2 | U2OS_compound | U2OS | compound | 0.3074 | 0.2171 |
| dinov2-vits14 | raw_l2 | U2OS_crispr | U2OS | crispr | 0.1646 | 0.0522 |
| dinov2-vits14 | raw_l2 | U2OS_orf | U2OS | orf | 0.2096 | 0.1074 |

## Within-Modality Matching

| model | input_transform | condition | cell | modality | mean_ap | median_ap | n_queries |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dinov2-vitb14 | negcon_zscore_l2 | A549_compound | A549 | compound | 0.0818 | 0.0298 | 302 |
| dinov2-vitb14 | negcon_zscore_l2 | A549_crispr | A549 | crispr | 0.0590 | 0.0078 | 290 |
| dinov2-vitb14 | negcon_zscore_l2 | A549_orf | A549 | orf |  |  | 0 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_compound | U2OS | compound | 0.0726 | 0.0257 | 302 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.0517 | 0.0093 | 290 |
| dinov2-vitb14 | negcon_zscore_l2 | U2OS_orf | U2OS | orf |  |  | 0 |
| dinov2-vitb14 | plate_zscore_l2 | A549_compound | A549 | compound | 0.0858 | 0.0334 | 302 |
| dinov2-vitb14 | plate_zscore_l2 | A549_crispr | A549 | crispr | 0.0629 | 0.0078 | 290 |
| dinov2-vitb14 | plate_zscore_l2 | A549_orf | A549 | orf |  |  | 0 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_compound | U2OS | compound | 0.0747 | 0.0295 | 302 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.0517 | 0.0111 | 290 |
| dinov2-vitb14 | plate_zscore_l2 | U2OS_orf | U2OS | orf |  |  | 0 |
| dinov2-vitb14 | raw_l2 | A549_compound | A549 | compound | 0.0838 | 0.0322 | 302 |
| dinov2-vitb14 | raw_l2 | A549_crispr | A549 | crispr | 0.0454 | 0.0081 | 290 |
| dinov2-vitb14 | raw_l2 | A549_orf | A549 | orf |  |  | 0 |
| dinov2-vitb14 | raw_l2 | U2OS_compound | U2OS | compound | 0.0651 | 0.0263 | 302 |
| dinov2-vitb14 | raw_l2 | U2OS_crispr | U2OS | crispr | 0.0425 | 0.0097 | 290 |
| dinov2-vitb14 | raw_l2 | U2OS_orf | U2OS | orf |  |  | 0 |
| dinov2-vits14 | negcon_zscore_l2 | A549_compound | A549 | compound | 0.0852 | 0.0292 | 302 |
| dinov2-vits14 | negcon_zscore_l2 | A549_crispr | A549 | crispr | 0.0625 | 0.0091 | 290 |
| dinov2-vits14 | negcon_zscore_l2 | A549_orf | A549 | orf |  |  | 0 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_compound | U2OS | compound | 0.0751 | 0.0286 | 302 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.0401 | 0.0097 | 290 |
| dinov2-vits14 | negcon_zscore_l2 | U2OS_orf | U2OS | orf |  |  | 0 |
| dinov2-vits14 | plate_zscore_l2 | A549_compound | A549 | compound | 0.0875 | 0.0313 | 302 |
| dinov2-vits14 | plate_zscore_l2 | A549_crispr | A549 | crispr | 0.0629 | 0.0086 | 290 |
| dinov2-vits14 | plate_zscore_l2 | A549_orf | A549 | orf |  |  | 0 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_compound | U2OS | compound | 0.0749 | 0.0292 | 302 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_crispr | U2OS | crispr | 0.0391 | 0.0112 | 290 |
| dinov2-vits14 | plate_zscore_l2 | U2OS_orf | U2OS | orf |  |  | 0 |
| dinov2-vits14 | raw_l2 | A549_compound | A549 | compound | 0.0842 | 0.0307 | 302 |
| dinov2-vits14 | raw_l2 | A549_crispr | A549 | crispr | 0.0497 | 0.0084 | 290 |
| dinov2-vits14 | raw_l2 | A549_orf | A549 | orf |  |  | 0 |
| dinov2-vits14 | raw_l2 | U2OS_compound | U2OS | compound | 0.0679 | 0.0271 | 302 |
| dinov2-vits14 | raw_l2 | U2OS_crispr | U2OS | crispr | 0.0401 | 0.0094 | 290 |
| dinov2-vits14 | raw_l2 | U2OS_orf | U2OS | orf |  |  | 0 |
