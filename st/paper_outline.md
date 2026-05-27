# Paper Outline

## Working Title

Low-cost biological representation learning for Cell Painting: a compact CPJUMP1 subset benchmark and encoder study

## Core Thesis

High-content Cell Painting images contain perturbation-level biological signal, but common visual encoders are not optimized to recover that signal under realistic experimental constraints. We build a compact, reproducible CPJUMP1 subset benchmark that can be run in roughly 2.5 days and use it to compare generic vision encoders, cell morphology baselines, and lightweight self-supervised training strategies.

The paper should not claim to build a full-scale foundation model. The stronger and more defensible claim is:

> A carefully designed 1-4 plate CPJUMP1 benchmark can reveal whether image representations preserve perturbation identity, target-level biology, and control separation; bio-aware preprocessing and training choices can improve these retrieval signals under limited compute.

## Target Contribution

1. A compact CPJUMP1-subset benchmark with clear metrics, fixed splits, and reproducible scripts.
2. A fair comparison of affordable encoders for Cell Painting images.
3. A practical study of training choices: channel handling, augmentations, aggregation, normalization, and contrastive or self-supervised objectives.
4. An analysis that explains when representations capture biology versus plate, well-position, or staining artifacts.

## 1. Introduction

High-content screening enables large-scale measurement of cellular responses to chemical and genetic perturbations. Cell Painting is especially useful because it captures rich morphology across multiple fluorescent channels. However, extracting biologically meaningful representations from these images remains difficult.

Generic encoders such as ImageNet ViTs, CLIP, and DINOv2 are visually powerful, but they are trained on natural images and may emphasize texture, intensity, or acquisition artifacts instead of perturbation effects. Classical CellProfiler features remain a strong morphology-aware baseline, while recent biological image models such as OpenPhenom suggest that domain-specific training can matter.

This work studies a practical question: given a modest budget, can we build and evaluate a useful bio-visual encoder on public HCS data?

The introduction should end with three claims:

1. We introduce a compact CPJUMP1-subset benchmark designed for fast iteration.
2. We evaluate several visual representations under the same retrieval-style biological metrics.
3. We identify training and preprocessing choices that improve perturbation-aware representations.

## 2. Related Work

This section should be short and focused.

- Cell Painting and high-content screening: morphology profiles, perturbation similarity, target matching.
- Hand-engineered morphology representations: CellProfiler and pycytominer.
- Generic visual foundation models: ImageNet, CLIP, DINOv2.
- Biological image representation models: DeepProfiler, OpenPhenom, self-supervised microscopy models.
- Benchmarking biological representation: replicate retrieval, matching, average precision, control separation.

The goal is to position the paper as a practical benchmark and training study, not as a claim of beating every large model.

## 3. CPJUMP1-Subset Benchmark

This is the main technical contribution.

### 3.1 Dataset Subset

Use CPJUMP1, starting from one high-value subset:

- Batch: `2020_11_04_CPJUMP1`
- Modality: compound
- Cell type: U2OS
- Time: 48h
- Density: 100
- Antibiotics: absent
- Plates: `BR00117010`, `BR00117011`, `BR00117012`, `BR00117013`

These four plates are attractive because they share condition and plate map, giving repeated perturbations across plates. This supports retrieval metrics without requiring the full CPJUMP1 download.

### 3.2 Data Unit

The benchmark should define three levels:

- Image channel: five fluorescent channels, excluding brightfield for the first version.
- Site-level representation: encoder feature for each field of view.
- Well-level representation: aggregation of site features, usually mean or median.

Primary reporting should use well-level representations, because CPJUMP1 benchmark metrics are well-level.

### 3.3 Metrics

The benchmark should contain four metrics:

1. Replicate retrieval mAP: wells with the same `Metadata_broad_sample` across plates should retrieve each other.
2. Negcon challenge mAP: treatment wells should rank their true replicates above negative controls.
3. Target retrieval mAP: compounds sharing the same annotated target or target list should be closer than unrelated compounds.
4. Artifact sensitivity: measure whether feature similarity is explained by same plate or same well position rather than same perturbation.

The first two metrics are mandatory. The third depends on enough target annotations after filtering. The fourth is important for credibility.

### 3.4 Splits

Default split:

- Train: two plates.
- Validation: one plate.
- Test: one plate.

Evaluation should primarily report held-out plate performance. For baselines that do not train, all plates can be encoded, but metrics should still be computed using held-out queries where possible.

### 3.5 Why This Benchmark Is Valid

The paper should explicitly defend the subset:

- It preserves biological replicate structure.
- It is cheap enough to run repeatedly.
- It has enough negative controls and compound annotations for retrieval analysis.
- It exposes common failure modes: plate effects, well-position effects, and target ambiguity.

## 4. Methods

### 4.1 Preprocessing

- Load TIFF images.
- Use the five fluorescent channels: AGP, Mito, RNA, ER, DNA.
- Normalize per channel with percentile clipping.
- Resize to encoder input size.
- Use either direct 5-channel models or two pseudo-RGB channel groups:
  - Group A: AGP, Mito, DNA.
  - Group B: RNA, ER, DNA.

### 4.2 Baselines

The baseline table should include 4-5 rows if feasible:

- CellProfiler features, as the morphology-aware classical baseline.
- DINOv2, generic self-supervised natural-image ViT.
- CLIP, generic vision-language representation.
- OpenPhenom, biological image foundation model.
- A small ImageNet ResNet or ViT, if setup time permits.

### 4.3 Our Training Variants

Use one affordable backbone rather than many expensive training runs. The likely default is DINOv2/ViT or ResNet-style feature extractor with lightweight projection head.

Candidate variants:

- SSL baseline: SimCLR-style contrastive loss across augmented views of the same site.
- Well-aware positive pairs: different sites from the same well as positives.
- Perturbation-aware weak positives: wells with the same compound across training plates as positives, if using labels is acceptable for one supervised contrastive variant.
- Channel-aware augmentations: intensity jitter per channel, mild blur, crop, rotation/flip, but avoid augmentations that destroy morphology.
- Plate normalization: compare raw feature aggregation vs plate-wise z-scoring or robust normalization.

The paper should present these as ablations, not as a single opaque recipe.

## 5. Experiments

### 5.1 Experimental Setup

Report:

- Plates used.
- Number of wells, sites, images, channels.
- GPU type, runtime, storage, and approximate cost.
- Encoders and feature dimensions.
- Aggregation method.
- All metric definitions.

### 5.2 Baseline Comparison

Main result table:

| Method | Replicate mAP | Negcon challenge | Target mAP | Artifact score | Runtime |
| --- | ---: | ---: | ---: | ---: | ---: |

This table is likely the main paper table.

### 5.3 Training Ablations

A second table should isolate method choices:

- Channel grouping.
- Augmentations.
- Loss function.
- Site-to-well aggregation.
- Plate normalization.

### 5.4 Analysis

Include at least three analysis figures:

1. UMAP or PCA colored by compound, plate, and control type.
2. Replicate retrieval curve or per-compound mAP distribution.
3. Artifact analysis: similarity by same perturbation, same plate, and same well position.

Use generated or schematic figures only for conceptual diagrams. Experimental plots must come from real results.

## 6. Discussion

Discuss:

- Why generic encoders may fail or succeed.
- Whether biological pretrained models help.
- Which tricks improve perturbation signal.
- Why subset benchmark results should be interpreted cautiously.
- How the benchmark can scale to more plates or genetic perturbations.

## 7. Conclusion

The conclusion should be concrete:

We construct a low-cost CPJUMP1-subset benchmark for perturbation-aware representation learning, evaluate several accessible visual encoders, and identify lightweight training and normalization choices that improve biological retrieval under limited compute. This provides a practical stepping stone toward larger HCS foundation-model training.

## Figure And Table Plan

Figure 1: Overview schematic.

- CPJUMP1 subset.
- Multi-channel image encoder.
- Site-to-well aggregation.
- Four retrieval/artifact metrics.

Figure 2: Benchmark data composition.

- Plates, wells, controls, compounds, target annotation coverage.

Figure 3: Main result table or bar plot.

- Baseline and trained variants across the four metrics.

Figure 4: Representation visualization.

- UMAP/PCA colored by perturbation, plate, and control.

Figure 5: Ablation analysis.

- Loss and augmentation effects.

Table 1: Dataset subset summary.

Table 2: Baseline comparison.

Table 3: Ablation comparison.

Table 4: Compute and cost summary.

## Acceptance Bar For The Paper Draft

The paper is only credible if it includes:

- A frozen subset definition.
- A documented train/validation/test split.
- At least four baselines or three baselines plus one trained variant.
- At least four metrics, with artifact analysis included.
- Runtime and cost accounting.
- Failure analysis, not only positive results.

