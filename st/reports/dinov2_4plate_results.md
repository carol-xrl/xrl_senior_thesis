# DINOv2 4-Plate Baseline Results

This report summarizes the first real benchmark runs on the U2OS compound 48h 4-plate subset (`BR00117010`-`BR00117013`). The subset contains 1,536 wells, 1,280 treatment wells, 256 negative-control wells, and 307 unique broad samples.

## Raw Frozen-Feature Baselines

| Encoder | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| DINOv2-S/14 | 0.2702 | 0.3803 | 0.0682 |
| DINOv2-B/14 | 0.2750 | 0.3811 | 0.0751 |

DINOv2-B/14 is only modestly better than DINOv2-S/14. The clearest gain is target retrieval, where the larger backbone improves mean AP from 0.0682 to 0.0751. Replicate retrieval and negative-control challenge are nearly unchanged under raw L2-normalized features.

## Normalization Ablation

### DINOv2-S/14

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.2702 | 0.3803 | 0.0680 |
| global_zscore_l2 | 0.2812 | 0.4168 | 0.0709 |
| plate_center_l2 | 0.2864 | 0.4235 | 0.0689 |
| plate_zscore_l2 | 0.2989 | 0.4356 | 0.0701 |
| negcon_center_l2 | 0.2765 | 0.4514 | 0.0695 |
| negcon_zscore_l2 | 0.2646 | 0.4546 | 0.0706 |

### DINOv2-B/14

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.2750 | 0.3811 | 0.0753 |
| global_zscore_l2 | 0.2875 | 0.4303 | 0.0738 |
| plate_center_l2 | 0.2959 | 0.4360 | 0.0716 |
| plate_zscore_l2 | 0.3044 | 0.4484 | 0.0719 |
| negcon_center_l2 | 0.2802 | 0.4612 | 0.0707 |
| negcon_zscore_l2 | 0.2728 | 0.4645 | 0.0708 |

## Interpretation

The benchmark is not saturated. Raw DINOv2 features produce replicate mean AP around 0.27 and target mean AP below 0.08, leaving substantial headroom for Cell Painting-specific adaptation.

Feature normalization is currently more important than simply scaling the frozen backbone. Plate z-score is best for replicate retrieval in both DINOv2-S/14 and DINOv2-B/14, while negative-control z-score is best for the negative-control challenge. This suggests the thesis should treat plate-aware or control-aware correction as a core experimental axis, not just a preprocessing detail.

The target retrieval metric is much harder than replicate retrieval and negative-control challenge. That is biologically plausible: compounds sharing an annotated target can still induce heterogeneous morphology because of potency, off-target effects, toxicity, pathway context, and annotation noise.

## Figure Artifacts

- `st/outputs/figures/dinov2_vits14_transforms/dinov2_vits14_transform_comparison.png`
- `st/outputs/figures/dinov2_vitb14_full/dinov2_vitb14_full_summary.png`
- `st/outputs/figures/dinov2_vitb14_full/dinov2_vitb14_full_artifact.png`
- `st/outputs/figures/dinov2_vitb14_transforms/dinov2_vitb14_transform_comparison.png`
