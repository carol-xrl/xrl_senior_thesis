# Experiment Plan

## Goal

Run a compact but paper-quality study on the CPJUMP1 4-plate U2OS 48h compound subset.

The experimental goal is not to train the largest possible model. The goal is to answer:

1. Which accessible visual encoders produce useful Cell Painting representations?
2. Which training objectives improve perturbation-level biological retrieval?
3. Which preprocessing or training tricks reduce artifacts and improve mechanism-oriented matching?

The plan is designed for:

- 2.5 days total runtime for experiment, plots, and analysis.
- Approximately 100 USD GPU budget.
- One rented GPU server.
- Raw images stored only on the GPU server.

## Benchmark Metrics

The experiment will report four metric families:

1. Replicate retrieval.
2. Negative-control challenge.
3. Compound target matching.
4. Artifact sensitivity.

Primary ranking should emphasize target matching and artifact-aware replicate retrieval. Negative-control challenge is a sanity check, not a main model-selection metric.

## Dataset

Primary subset:

| Field | Value |
| --- | --- |
| Batch | `2020_11_04_CPJUMP1` |
| Modality | compound |
| Cell type | U2OS |
| Time | 48h |
| Plates | `BR00117010`, `BR00117011`, `BR00117012`, `BR00117013` |

Train/validation/test split:

| Split | Plates |
| --- | --- |
| Train | `BR00117010`, `BR00117011` |
| Validation | `BR00117012` |
| Test | `BR00117013` |

Use five fluorescent channels only: AGP, Mito, RNA, ER, DNA.

## Baselines

The baseline set should cover classical morphology, generic natural-image SSL, recent frontier SSL, biomedical vision-language, and microscopy-specific models.

### Baseline Priority

| Priority | Method | Why It Is Representative | Feasibility | Expected Role |
| --- | --- | --- | --- | --- |
| Required | CellProfiler | Classical hand-engineered morphology baseline from the original CPJUMP1 pipeline | Easy if Git LFS profiles are available; no GPU needed | Strong non-deep baseline |
| Required | DINOv2 ViT-B/14 | Stable open-source self-supervised vision foundation model | Easy via torch hub / HF / local repo | Generic SSL baseline |
| Required | DINOv3 ViT-S/16 or ViT-B/16 | Newer frontier self-supervised vision backbone with open weights | Feasible if Transformers/PyTorch versions work | Modern SOTA-ish generic SSL baseline |
| Required if install succeeds | OpenPhenom-S/16 | Microscopy / Cell Painting foundation model trained on RxRx3 and JUMP-CP style data | Feasible via Hugging Face, but dependency risk | Most biologically relevant pretrained baseline |
| Optional | BioMedCLIP or CLIP | Vision-language representation; BioMedCLIP is biomedical but not microscopy-specific | Feasible via HF/open_clip | Contrast against language-supervised encoders |
| Fallback | ResNet50 ImageNet | Old but reliable CNN baseline | Very easy via torchvision/timm | Engineering fallback |

### Baseline Rationale

CellProfiler is essential because it is the historical morphology baseline. If a new encoder cannot beat or complement CellProfiler, the paper must explain why.

DINOv2 is essential because it is a strong, stable, generic SSL vision model and already appears in the cleaned benchmark code.

DINOv3 is included because it is newer and more representative of current frontier generic SSL encoders. Use a small/base model, not the largest model.

OpenPhenom is included because it is trained for microscopy / Cell Painting-like data and is the most relevant domain-specific pretrained model. If it fails to install quickly, mark it as attempted and move on.

BioMedCLIP or CLIP is optional. It is useful as a contrastive language-supervised model, but biomedical image-text pretraining does not guarantee Cell Painting morphology quality.

## Feature Extraction Protocol

For 3-channel encoders:

- Encode two pseudo-RGB groups:
  - Group A: AGP, Mito, DNA.
  - Group B: RNA, ER, DNA.
- Concatenate features from the two groups.

For 5-channel-capable encoders:

- Use all fluorescent channels directly if supported.

Site-to-well aggregation:

- Default: mean across sites.
- Ablation: median across sites.

Feature normalization:

- Default: raw well-level features.
- Ablation: plate-wise z-score or robust median/MAD normalization.

## Training Variants

We should train only a small number of variants. The best plan is to use one backbone and compare losses/tricks under a controlled setup.

Recommended backbone for training:

- DINOv2 or DINOv3 frozen backbone + trainable projection head first.
- If time allows, fine-tune the last block or adapter layers.

Do not start by full fine-tuning a large ViT. It is risky under the time and budget constraint.

## Loss Functions

### Loss 1: SimCLR / NT-Xent Self-Supervised Loss

Positive pair:

- Two augmented views of the same site.

Negatives:

- Other sites in the batch.

Why include it:

- It is a standard SSL baseline.
- It does not use compound labels.
- It tests whether generic augmentation-based SSL can improve morphology representations.

Risk:

- It may learn image-level texture/staining invariance rather than perturbation-level biology.

Priority:

- Required training baseline.

### Loss 2: Well-Aware Contrastive Loss

Positive pair:

- Different sites from the same well.

Negatives:

- Sites from different wells.

Why include it:

- A well is the natural experimental unit.
- Different fields of the same well should share perturbation and treatment context.
- This encourages site-to-well consistency.

Risk:

- It may learn well-specific artifacts or local acquisition biases.

Priority:

- Required if image loading supports multiple sites per well.

### Loss 3: Supervised Contrastive Loss By Compound

Positive pair:

- Wells/sites with the same `Metadata_broad_sample` across train plates.

Negatives:

- Different compounds.

Why include it:

- It directly optimizes perturbation retrieval.
- It is highly relevant to our benchmark.
- It is feasible because compound labels are available.

Risk:

- It may overfit to the reused plate map and same-well confounding.
- It is no longer purely self-supervised.

How to frame it:

- Call it weakly supervised or label-aware contrastive adaptation, not self-supervised.

Priority:

- Required if time allows; this is likely to produce the strongest replicate retrieval.

### Loss 4: Target-Aware Supervised Contrastive Loss

Positive pair:

- Different compounds with overlapping target annotations.

Negatives:

- Compounds with disjoint target lists.

Why include it:

- It optimizes the most mechanism-oriented metric.
- It may improve target matching, which is less likely to saturate.

Risk:

- Target annotations are noisy and polypharmacological.
- Positive pairs can be weak or biologically heterogeneous.

Priority:

- Stretch goal. Run only after the required losses are complete.

## Tricks / Ablations

### Trick 1: Channel Grouping

Compare:

- Two pseudo-RGB groups concatenated.
- Single RGB group AGP/Mito/DNA.
- Single RGB group RNA/ER/DNA.

Purpose:

- Determine which channel grouping carries more perturbation signal.

Priority:

- Required, cheap.

### Trick 2: Plate-Wise Feature Normalization

Compare:

- No normalization.
- Plate-wise z-score.
- Plate-wise robust median/MAD normalization.

Purpose:

- Reduce plate-level and intensity artifacts.

Priority:

- Required, cheap and important.

### Trick 3: Aggregation Mean vs Median

Compare:

- Mean of site features.
- Median of site features.

Purpose:

- Median may be more robust to bad fields of view or imaging artifacts.

Priority:

- Required, cheap.

### Trick 4: Artifact-Aware Sampling

Compare:

- Random batch sampling.
- Balanced sampling across plates.
- Avoid same-well positives for supervised contrastive if possible.

Purpose:

- Reduce exploitation of plate/well artifacts.

Priority:

- Important for supervised contrastive variants.

### Trick 5: Lightweight Adapter / LoRA

Compare:

- Frozen backbone + projection head.
- Frozen backbone + small adapter.
- Last block fine-tuning if time allows.

Purpose:

- Test whether small trainable capacity can adapt a generic encoder to Cell Painting.

Priority:

- Stretch goal. Only run after baseline features and loss comparisons finish.

## Minimal Experiment Matrix

This is the minimum publishable matrix.

| Group | Experiment | Metrics |
| --- | --- | --- |
| Baseline | CellProfiler | all metrics |
| Baseline | DINOv2 frozen | all metrics |
| Baseline | DINOv3 frozen | all metrics |
| Baseline | OpenPhenom frozen or fallback ResNet50 | all metrics |
| Training | DINOv2/DINOv3 + SimCLR projection | all metrics |
| Training | DINOv2/DINOv3 + well-aware contrastive | all metrics |
| Training | DINOv2/DINOv3 + compound supervised contrastive | all metrics |
| Trick | best baseline + plate normalization | all metrics |
| Trick | best baseline + median aggregation | all metrics |

If time is short, drop BioMedCLIP/CLIP first, then drop target-aware loss.

## Full Experiment Matrix

Run only if the server is fast and baselines finish early.

| Group | Experiment |
| --- | --- |
| Baseline | CellProfiler |
| Baseline | DINOv2 ViT-B/14 |
| Baseline | DINOv3 ViT-S/16 |
| Baseline | DINOv3 ViT-B/16 |
| Baseline | OpenPhenom-S/16 |
| Baseline | BioMedCLIP or CLIP |
| Loss | SimCLR |
| Loss | Well-aware contrastive |
| Loss | Compound supervised contrastive |
| Loss | Target-aware supervised contrastive |
| Trick | Channel group A only |
| Trick | Channel group B only |
| Trick | Group A+B concatenation |
| Trick | Mean aggregation |
| Trick | Median aggregation |
| Trick | Plate-wise z-score |
| Trick | Plate-wise robust normalization |

## Expected Results And Hypotheses

Hypothesis 1:

CellProfiler will be competitive on replicate retrieval because it was designed for Cell Painting morphology.

Hypothesis 2:

DINOv2/DINOv3 frozen features may be strong but may also encode non-biological texture and intensity artifacts.

Hypothesis 3:

OpenPhenom should be strong on morphology-aware metrics because it is microscopy / Cell Painting oriented.

Hypothesis 4:

Simple SimCLR may improve local consistency but may not improve target matching much.

Hypothesis 5:

Well-aware or compound-aware contrastive training should improve replicate retrieval, but must be checked carefully for artifact overfitting.

Hypothesis 6:

Plate-wise normalization and median aggregation may improve robustness and artifact metrics even if raw AP changes only slightly.

## What Makes The Paper Strong

The paper should not only report "best method wins." It should show:

1. Generic foundation models do not automatically solve biological morphology retrieval.
2. Domain-specific or bio-aware adaptations help on mechanism-oriented metrics.
3. Some improvements are actually artifact-driven, and our benchmark detects that.
4. Under constrained compute, a compact benchmark can still reveal meaningful biological representation behavior.

## 2.5-Day Execution Schedule

### Phase 0: Server Setup And Tiny Pilot

Target: first 4-6 hours.

Tasks:

1. Pull branch `st`.
2. Install environment.
3. Resolve S3 paths.
4. Download `A01 A02` wells for all 4 plates.
5. Run one frozen encoder on pilot images.
6. Run metrics on pilot feature output.

Exit criterion:

- Feature table with `Metadata_Plate`, `Metadata_Well`, `feature_*` exists.
- `evaluate_features.py` runs successfully.

### Phase 1: Full Baseline Feature Extraction

Target: Day 1.

Tasks:

1. Download full fluorescent channels for the 4 plates.
2. Extract DINOv2 features.
3. Extract DINOv3 features.
4. Extract OpenPhenom if installation succeeds.
5. Prepare CellProfiler feature baseline if Git LFS profile files are available.
6. Run all metrics and basic plots.

Exit criterion:

- At least 3 baseline rows in the main result table.

### Phase 2: Training Loss Comparison

Target: Day 2.

Tasks:

1. Train SimCLR projection variant.
2. Train well-aware contrastive variant.
3. Train compound supervised contrastive variant.
4. Evaluate all trained variants.

Exit criterion:

- At least 2 trained variants evaluated.

### Phase 3: Tricks And Final Analysis

Target: final half day.

Tasks:

1. Run mean vs median aggregation.
2. Run plate normalization.
3. Generate final figures.
4. Write experiment report.

Exit criterion:

- Final summary table.
- Artifact diagnostic table.
- At least three plots.
- Report explaining positive and negative findings.

## Kill Criteria

Stop or downgrade an experiment if:

- Model setup takes more than 2 hours.
- Feature extraction for one baseline would exceed budget.
- GPU memory issues require major engineering work.
- The method requires downloading unrelated huge datasets.

Fallback order:

1. Replace OpenPhenom with ResNet50 if OpenPhenom setup fails.
2. Replace DINOv3-B with DINOv3-S if memory is tight.
3. Use frozen features only if training is too slow.
4. Use 2 plates if full 4-plate download is too slow, but clearly label as pilot.

