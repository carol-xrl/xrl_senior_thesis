# 8-Plate U2OS Compound Result Summary

These tables summarize completed 24h+48h U2OS compound experiments. Test metrics use held-out test plates when available; full metrics use all query wells.

## Frozen Backbones

| model | feature_type | input_transform | test_replicate_ap | test_negcon_ap | full_replicate_ap | full_negcon_ap | target_ap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DINOv2-S/14 | frozen raw | none | 0.1351 | 0.2663 | 0.1323 | 0.2681 | 0.0675 |
| DINOv2-B/14 | frozen raw | none | 0.1385 | 0.2583 | 0.1360 | 0.2613 | 0.0736 |
| DINOv2-L/14 | frozen raw | none | 0.1388 | 0.2688 | 0.1345 | 0.2689 | 0.0687 |

## Best Normalization Variants Per Backbone

| model | input_transform | full_replicate_ap | full_negcon_ap | target_ap |
| --- | --- | --- | --- | --- |
| DINOv2-B/14 | plate_zscore_l2 | 0.1627 | 0.3431 | 0.0806 |
| DINOv2-B/14 | global_zscore_l2 | 0.1516 | 0.3157 | 0.0799 |
| DINOv2-L/14 | plate_zscore_l2 | 0.1540 | 0.3333 | 0.0766 |
| DINOv2-L/14 | global_zscore_l2 | 0.1478 | 0.3120 | 0.0764 |
| DINOv2-S/14 | plate_zscore_l2 | 0.1551 | 0.3389 | 0.0727 |
| DINOv2-S/14 | global_zscore_l2 | 0.1444 | 0.3106 | 0.0718 |

## Projection-Head Ablation

| model | loss | input_transform | best_val_replicate_ap | test_replicate_ap | test_negcon_ap | full_replicate_ap | full_negcon_ap | target_ap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DINOv2-L/14 | Proxy-CE | plate_zscore_l2 | 0.3113 | 0.3199 | 0.4346 | 0.4894 | 0.5693 | 0.0812 |
| DINOv2-B/14 | Proxy-CE | plate_zscore_l2 | 0.3070 | 0.3173 | 0.4261 | 0.4843 | 0.5616 | 0.0814 |
| DINOv2-B/14 | SupCon | plate_zscore_l2 | 0.3033 | 0.3167 | 0.4257 | 0.4844 | 0.5649 | 0.0786 |
| DINOv2-L/14 | SupCon | plate_zscore_l2 | 0.3096 | 0.3080 | 0.4144 | 0.4830 | 0.5611 | 0.0710 |
| DINOv2-S/14 | Proxy-CE | plate_zscore_l2 | 0.2911 | 0.3036 | 0.4096 | 0.4738 | 0.5495 | 0.0787 |
| DINOv2-S/14 | SupCon | plate_zscore_l2 | 0.2935 | 0.3031 | 0.4163 | 0.4714 | 0.5543 | 0.0781 |
| DINOv2-S/14 | SupCon | negcon_zscore_l2 | 0.2765 | 0.2932 | 0.4107 | 0.4628 | 0.5469 | 0.0715 |
| DINOv2-S/14 | SupCon | raw_l2 | 0.2389 | 0.2494 | 0.4062 | 0.3535 | 0.4964 | 0.0834 |
| DINOv2-S/14 | Triplet | plate_zscore_l2 | 0.2234 | 0.2249 | 0.3482 | 0.2587 | 0.3749 | 0.0854 |
