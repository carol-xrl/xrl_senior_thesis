# Experiment Plan

## Current Goal

Build a thesis-quality CPJUMP1 benchmark around a fixed 20-plate multimodal subset, then use it to evaluate frozen visual representations, normalization choices, and lightweight supervised projection heads.

The current study is no longer the earlier 4-plate or 8-plate compound-only pilot. The main benchmark is:

- 20 plates from `2020_11_04_CPJUMP1`
- 2 cell types: A549 and U2OS
- 3 perturbation modalities: compound, ORF, CRISPR
- 5 fluorescent channels only: AGP, Mito, RNA, ER, DNA
- benchmark metrics include perturbation retrieval, negative-control challenge, within-modality matching, and cross-modality matching

The practical goal remains constrained: complete experiments, figures, and analysis quickly on one RunPod L40S GPU while keeping raw images on the server.

## Dataset Definition

Config file:

- `st/configs/subset_multimodal_short_20plate.yaml`

Metadata outputs:

- `st/data/metadata/subset_multimodal_short_20plate_well_metadata.csv`
- `st/data/splits/subset_multimodal_short_20plate_splits.csv`
- `st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv`

Raw image location on RunPod:

- `/workspace/data/cpjump1/images/2020_11_04_CPJUMP1/<plate>/Images`

Raw-image retention policy:

- Keep all raw image plates on RunPod.
- Do not copy raw TIFFs back to the Mac.
- Only pull back metrics, reports, logs, and selected small figures.
- Clean only intermediate artifacts, not raw image directories.

## Plate Set And Splits

The benchmark uses 20 plates. Split assignment is by plate. Projection-head training uses only train plates; validation plates select checkpoints; test plates remain held out for final split-aware checks.

| Split | Cell | Modality | Time | Plate(s) |
| --- | --- | --- | ---: | --- |
| train | A549 | compound | 24h | `BR00116991`, `BR00116992` |
| train | U2OS | compound | 24h | `BR00116995`, `BR00117024` |
| train | A549 | ORF | 48h | `BR00117020` |
| train | U2OS | ORF | 48h | `BR00117022` |
| train | A549 | CRISPR | 96h | `BR00118041`, `BR00118042` |
| train | U2OS | CRISPR | 96h | `BR00118045`, `BR00118046` |
| val | A549 | compound | 24h | `BR00116993` |
| val | U2OS | compound | 24h | `BR00117025` |
| val | A549 | CRISPR | 96h | `BR00118043` |
| val | U2OS | CRISPR | 96h | `BR00118047` |
| test | A549 | compound | 24h | `BR00116994` |
| test | U2OS | compound | 24h | `BR00117026` |
| test | A549 | ORF | 48h | `BR00117021` |
| test | U2OS | ORF | 48h | `BR00117023` |
| test | A549 | CRISPR | 96h | `BR00118044` |
| test | U2OS | CRISPR | 96h | `BR00118048` |

Current well-level metadata size:

| Split | Wells |
| --- | ---: |
| train | 3816 |
| val | 1528 |
| test | 2288 |
| total | 7632 |

Condition coverage:

| Cell | Modality | Treatment wells | Negative controls | Unique perturbation IDs |
| --- | --- | ---: | ---: | ---: |
| A549 | compound | 1280 | 256 | 306 |
| U2OS | compound | 1280 | 256 | 306 |
| A549 | CRISPR | 1280 | 240 | 305 |
| U2OS | CRISPR | 1280 | 240 | 305 |
| A549 | ORF | 640 | 120 | 160 |
| U2OS | ORF | 640 | 120 | 160 |

Important split caveat:

- Frozen encoders are run on all 20 plates because feature extraction itself uses no biological labels.
- Projection-head training uses train plates only.
- Validation AP is used to select the projection-head checkpoint.
- The current 20-plate summary tables are condition-level all-query evaluations. They are useful for method comparison, but the final thesis should also include a split-aware table that reports held-out test queries separately.

## Image And Feature Protocol

Raw input:

- 5 fluorescent TIFF channels per site.
- Brightfield is excluded.
- Expected complete raw image count per plate: 17,280 TIFFs.
- Expected sites per complete 384-well plate: 3,456 site-level 5-channel fields.

Preprocessing:

- Percentile-normalize each channel.
- Resize to 224 x 224 for DINOv2.
- Encode two pseudo-RGB groups:
  - Group A: AGP, Mito, DNA
  - Group B: RNA, ER, DNA
- Concatenate group embeddings.
- Average site embeddings into one well-level feature.

Feature files:

- DINOv2-S/14 20-plate feature table: `st/outputs/features/dinov2_vits14_multimodal_short_20plate.csv`
- DINOv2-B/14 20-plate feature table: `st/outputs/features/dinov2_vitb14_multimodal_short_20plate.csv`

Current feature dimensions:

| Encoder | Single DINO dim | Concatenated well feature dim |
| --- | ---: | ---: |
| DINOv2-S/14 | 384 | 768 |
| DINOv2-B/14 | 768 | 1536 |

## Benchmark Metrics

### 1. Perturbation / Replicate Retrieval

Question:

Can a query well retrieve wells with the same perturbation identity across different plates?

Definition:

- Query: treatment wells.
- Positives: same `Metadata_broad_sample`, different plate.
- Candidates: treatment wells from other plates in the same condition.
- Metric: mean average precision.

Role:

- Main identity-level retrieval metric.
- Especially meaningful for compound and CRISPR.
- ORF has fewer plates and positives, so it is harder and should be interpreted with caution.

### 2. Negative-Control Challenge

Question:

Can a query treatment well rank true replicates above negative controls?

Definition:

- Query: treatment wells.
- Positives: same perturbation.
- Challenge candidates include negative controls.
- Metric: mean average precision.

Role:

- Sanity check for treatment-vs-control separation.
- Not enough by itself to claim mechanism-level biology.

### 3. Within-Modality Matching

Question:

Can a representation recover known within-modality biological relationships beyond exact perturbation identity?

Definitions:

- Compound: target-aware matching among compounds with target annotations.
- CRISPR: sister-guide/gene-level matching.
- ORF: currently no robust within-modality matching positives in this subset, so reported as `NaN` or zero queries.

Role:

- More mechanism-oriented than exact replicate retrieval.
- Helps detect whether models learn target/gene structure.

### 4. Cross-Modality Matching

Question:

Can compound-induced morphology align with gene perturbation morphology for the same biological target/gene?

Definitions:

- Compound -> CRISPR within the same cell line.
- Compound -> ORF within the same cell line.
- Compound labels use target genes from compound annotations.
- ORF/CRISPR labels use perturbation genes.
- Metric: mean average precision.

Role:

- Hardest and most biologically interesting metric.
- Low frozen AP is expected and useful; this is not saturated.
- Bio-target supervised heads should be framed as an annotation-supervised upper bound, not as a label-free baseline.

## Experiments Completed

### A. 8-Plate U2OS Compound Pilot

Purpose:

- Establish pipeline correctness.
- Compare DINOv2-S/B/L.
- Test normalization and projection-head losses.

Main findings:

- Plate z-score improved replicate retrieval.
- Negative-control z-score improved negative-control challenge.
- Proxy-CE projection heads were strongest among the tested loss functions.
- DINOv2-L did not strongly outperform DINOv2-B, so B/S were sufficient for the larger 20-plate run.

Reports:

- `st/reports/experiment_tables/8plate_results_summary.md`
- `st/reports/experiment_tables/8plate_frozen_backbones.csv`
- `st/reports/experiment_tables/8plate_projection_head_ablation.csv`
- `st/reports/experiment_tables/8plate_proxy_seed_robustness.csv`

### B. 20-Plate Frozen DINOv2 Baselines

Completed:

- DINOv2-S/14
- DINOv2-B/14
- transforms: `raw_l2`, `plate_zscore_l2`, `negcon_zscore_l2`

Reports:

- `st/reports/experiment_tables/20plate_multimodal_results_summary.md`
- `st/reports/experiment_tables/20plate_multimodal_summary_long.csv`
- `st/reports/experiment_tables/20plate_retrieval_summary.csv`
- `st/reports/experiment_tables/20plate_within_modality_summary.csv`
- `st/reports/experiment_tables/20plate_cross_modality_summary.csv`

Key findings:

- Compound replicate retrieval is strong and measurable.
- CRISPR and ORF retrieval are much harder.
- Cross-modality AP is low under frozen features, which makes it a meaningful challenge.
- DINOv2-B gives modest gains on some U2OS ORF/cross-modality conditions, but backbone scaling alone is not the main story.

### C. 20-Plate Projection-Head Experiments

Completed:

- DINOv2-B + plate-zscore + sample Proxy-CE.
- DINOv2-B + plate-zscore + bio-target Proxy-CE.

Reports:

- `st/reports/experiment_tables/20plate_projection_head_results_summary.md`
- `st/reports/experiment_tables/20plate_projection_head_key_metrics.csv`
- `st/reports/experiment_tables/20plate_projection_head_summary_long.csv`

Interpretation:

- Sample Proxy-CE strongly improves replicate retrieval.
- Sample Proxy-CE does not improve cross-modality matching.
- Bio-target Proxy-CE strongly improves cross-modality matching because it directly trains on shared target/gene annotations.
- Bio-target Proxy-CE should be called an annotation-supervised upper bound.

## Current Key Results

| Condition | Metric | Frozen DINOv2-B + plate z-score | Sample Proxy-CE | Bio-target Proxy-CE |
| --- | --- | ---: | ---: | ---: |
| A549 compound | replicate AP | 0.3111 | 0.4650 | 0.3987 |
| U2OS compound | replicate AP | 0.2151 | 0.4195 | 0.3340 |
| A549 CRISPR | replicate AP | 0.0447 | 0.2126 | 0.1691 |
| U2OS CRISPR | replicate AP | 0.0645 | 0.2468 | 0.1886 |
| A549 ORF | replicate AP | 0.0728 | 0.0729 | 0.0567 |
| U2OS ORF | replicate AP | 0.1491 | 0.1634 | 0.1140 |
| A549 compound -> CRISPR | cross-modality AP | 0.0347 | 0.0311 | 0.8256 |
| A549 compound -> ORF | cross-modality AP | 0.0357 | 0.0324 | 0.8335 |
| U2OS compound -> CRISPR | cross-modality AP | 0.0319 | 0.0290 | 0.8067 |
| U2OS compound -> ORF | cross-modality AP | 0.0428 | 0.0279 | 0.8312 |

## Experiments Still Needed

Priority 1: split-aware final reporting.

- Add test-query-only tables for frozen DINOv2-B, sample Proxy-CE, and bio-target Proxy-CE.
- Keep training labels restricted to train plates.
- Report validation checkpoint selection separately from final test metrics.

Priority 2: figures for the thesis.

- Bar plots for frozen vs sample Proxy-CE vs bio-target Proxy-CE.
- Separate replicate retrieval and cross-modality figures.
- Dataset composition figure: plates by cell line, modality, split.

Priority 3: write analysis.

- Explain why cross-modality is hard.
- Explain why bio-target head is an upper bound.
- Explain why sample identity training helps replicate retrieval but not cross-modality.

Optional:

- Seed repeat for the 20-plate sample Proxy-CE head.
- A smaller DINOv2-S head if we need a compute/efficiency comparison.
- A split-aware bio-target variant that trains only on train target labels and evaluates unseen/held-out plates.

## Success Criteria

The experiment section is credible if it includes:

- exact 20-plate subset definition;
- train/val/test plate split;
- frozen baseline results for DINOv2-S and DINOv2-B;
- normalization ablation;
- at least one identity-supervised projection head;
- one annotation-supervised cross-modality upper bound;
- raw image retention and reproducibility statement;
- clear caveat that bio-target supervision is not label-free.
