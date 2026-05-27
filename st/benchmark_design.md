# Benchmark Design And 2.5-Day Execution Plan

## Objective

Build a compact CPJUMP1 benchmark that can be executed within 2.5 days, including data download, feature extraction, training, evaluation, plotting, and analysis.

The benchmark should answer:

1. Do visual features retrieve biological replicates across plates?
2. Do visual features separate treatments from negative controls?
3. Do features recover target-level relationships among compounds?
4. Are the measured signals biological, or are they dominated by plate/well artifacts?

## Compute Constraint

Budget target: about 100 USD.

Time target: 2.5 days end to end.

Practical implications:

- Do not start with the full CPJUMP1 dataset.
- Prefer fluorescent channels only for the first pass.
- Keep one frozen subset for all baselines.
- Run feature extraction and training in `tmux`.
- Save intermediate features aggressively so failed downstream experiments do not require re-encoding images.
- Use smoke tests before launching any full run.

## Primary Dataset Subset

Primary subset: 4 replicate compound plates.

| Field | Value |
| --- | --- |
| Batch | `2020_11_04_CPJUMP1` |
| Modality | compound |
| Cell type | U2OS |
| Time | 48h |
| Density | 100 |
| Antibiotics | absent |
| Cell line | Parental |
| Plates | `BR00117010`, `BR00117011`, `BR00117012`, `BR00117013` |

Reason:

- The four plates share the same experimental condition.
- The compound plate map gives repeated compounds across plates.
- This supports cross-plate replicate retrieval.
- It is small enough to run under the budget, especially if we download only channels 1-5.
- These plates already appear in the repo's example-image context and DeepProfiler subset plan, so they are familiar and defensible.

## Fallback Subsets

If storage, download, or GPU time becomes the bottleneck:

Fallback A: 2 plates.

- `BR00117010`, `BR00117011`
- Use for pipeline validation and preliminary results.
- Supports replicate retrieval but has weaker statistics.

Fallback B: 1 plate plus site-level pseudo-replicates.

- `BR00117010`
- Use only for smoke tests, preprocessing validation, and visual examples.
- Not acceptable as final biological benchmark unless clearly labeled as pilot.

Stretch subset:

- Add 4 CRISPR U2OS 144h plates: `BR00116996`, `BR00116997`, `BR00116998`, `BR00116999`.
- This enables stronger compound-genetic target matching, but it likely exceeds the first 2.5-day plan unless downloads are fast.

## Data Units

Raw unit:

- TIFF image, one channel, one field of view.

Site unit:

- Five fluorescent channels for one field of view.
- Shape after loading: `(5, H, W)`.

Well unit:

- Aggregate all valid site features for one well.
- Default aggregation: mean.
- Ablation aggregation: median.

Perturbation unit:

- Aggregate wells with the same compound across plates only for analysis; primary metrics should stay at well level.

## Train/Validation/Test Split

Default split for the four compound plates:

| Split | Plates | Purpose |
| --- | --- | --- |
| Train | `BR00117010`, `BR00117011` | self-supervised or weakly supervised training |
| Validation | `BR00117012` | model selection and quick ablations |
| Test | `BR00117013` | final held-out reporting |

For unsupervised baseline encoders:

- Extract features for all plates.
- Report metrics with held-out test queries where possible.
- Keep train/validation/test split metadata in output files for consistent plotting.

## Metrics

### Metric 1: Cross-Plate Replicate Retrieval mAP

Question:

Can a query well retrieve wells containing the same compound on other plates?

Positive pairs:

- Same `Metadata_broad_sample`.
- Different `Metadata_Plate`.

Negative pairs:

- Different `Metadata_broad_sample`.
- Preferably from the same split or same condition.

Report:

- Mean average precision.
- Fraction of perturbations above corrected q-value threshold if null testing is implemented.
- Per-compound mAP distribution.

This is the primary metric.

### Metric 2: Negative-Control Challenge

Question:

Can treatment features retrieve treatment replicates above DMSO or other negative controls?

Positive pairs:

- Same treatment compound across different plates.

Challenge set:

- Negative controls and unrelated treatments.

Report:

- Treatment-vs-negcon retrieval AP.
- Mean treatment-control separation score.

This protects against a representation that only learns generic plate quality or staining intensity.

Role in the benchmark:

- Treat this as a sanity-check metric, not the main optimization target.
- If a method performs poorly here, it likely fails to capture treatment signal.
- If a method performs very well here, it does not automatically mean it captures mechanism-level biology.
- Improvements should mainly be judged by replicate retrieval under artifact diagnostics and target matching.

### Metric 3: Compound Target Retrieval

Question:

Do compounds with overlapping target annotations appear closer in feature space?

Positive pairs:

- Different compounds with at least one shared target in `target_list`.

Negative pairs:

- Compounds with disjoint target lists.

Report:

- Target-level mAP.
- Coverage after filtering ambiguous or missing target annotations.

This metric may be noisier because compounds can be polypharmacological. It should be treated as secondary.

Role in the benchmark:

- This is the least likely metric to saturate.
- It is the most mechanism-oriented metric in the compound-only subset.
- It should be one of the main comparison metrics when replicate retrieval or negcon challenge are too easy.

### Metric 4: Artifact Sensitivity

Question:

Is similarity driven more by biological perturbation or by acquisition artifacts?

Measure similarity for:

- Same compound, different plate.
- Different compound, same plate.
- Different compound, same well position across plates.
- Negative controls at same well position across plates.

Report:

- Mean similarity table.
- Artifact score, e.g. same-well-position similarity minus random-position similarity.
- Plot by plate and well position.

This metric is important because small HCS subsets are vulnerable to plate and position confounding.

Important caveat for the 4-plate compound subset:

- The repeated compound plates use the same plate map.
- Therefore, same compound across plates is usually also same well position across plates.
- Replicate retrieval remains a standard and useful metric, but it can be inflated by well-position artifacts.
- We must report a confounding diagnostic: the fraction of same-well cross-plate pairs that are also same-compound pairs, plus negative-control same-well similarity.
- Target retrieval and treatment-vs-negcon challenge are needed as complementary metrics because they are less reducible to same-well replicate lookup.

Metric saturation policy:

- Do not rank methods by negative-control challenge alone.
- Report replicate retrieval as a standard CPJUMP1-style metric, but always place it next to artifact diagnostics.
- Use target matching and per-compound AP distributions as the main non-saturated biological readouts.
- If replicate retrieval is near ceiling for several models, compare robustness: bootstrap confidence intervals, low-performing compounds, and artifact-corrected diagnostics.

## Baselines

Minimum viable baseline set:

1. CellProfiler features.
2. DINOv2 ViT-B/14.
3. CLIP ViT-L/14.
4. OpenPhenom, if installation succeeds quickly.

Fallback baseline if OpenPhenom setup is slow:

- ImageNet ResNet50 or ViT from torchvision/timm.

Notes:

- CellProfiler is the biological morphology baseline.
- DINOv2 and CLIP are generic vision baselines.
- OpenPhenom is the domain-pretrained biological-image baseline.
- All baselines must output the same unified feature format.

## Training Variants

We should avoid training many large models. Use one backbone and run focused variants.

Recommended first trained model:

- Backbone: small ResNet, ViT-S, or frozen DINOv2 with trainable projection head.
- Input: two pseudo-RGB groups or five-channel first layer if easy.
- Training unit: site-level image.
- Evaluation unit: well-level feature aggregation.

Variants:

| Variant | Purpose | Expected Cost |
| --- | --- | --- |
| Frozen encoder + projection head | cheap adaptation | low |
| SimCLR site contrastive | general SSL | medium |
| Well-aware contrastive | same-well sites as positives | medium |
| Compound-aware supervised contrastive | same compound across train plates as positives | medium |
| Plate-normalized features | artifact reduction | low |

Only run all variants if smoke tests and baselines finish early.

## Preprocessing Choices

Default:

- Use fluorescent channels 1-5 only.
- Per-channel percentile normalization, e.g. 0.1 to 99.9.
- Resize to 224 for DINOv2/CLIP/ImageNet encoders.
- Resize to 256 for OpenPhenom if required.
- Encode two pseudo-RGB groups for 3-channel encoders:
  - AGP, Mito, DNA.
  - RNA, ER, DNA.
- Concatenate group features.

Augmentation candidates:

- Random crop and resize.
- Horizontal/vertical flip.
- 90-degree rotations.
- Mild per-channel intensity jitter.
- Mild Gaussian blur.

Avoid at first:

- Heavy color jitter copied from natural-image pipelines.
- CutMix/MixUp unless there is a clear biological rationale.
- Strong augmentations that can erase subcellular morphology.

## Output Artifacts

All generated files should live under `st/`.

Proposed structure:

```text
st/
  README.md
  paper_outline.md
  benchmark_design.md
  configs/
  scripts/
  src/
  data/
    metadata/
    splits/
  outputs/
    features/
    metrics/
    figures/
    logs/
  reports/
```

Do not write new project code into the root repo or `cpjump1_benchmark/`. Reuse code by importing or copying minimal adapted modules into `st/` only after we decide the final benchmark API.

## Local And Remote Execution

The Mac is the development and coordination machine. The rented GPU server is the data and compute machine.

Use git to synchronize code:

- Mac writes code under `st/`.
- Mac commits and pushes branch `st`.
- GPU server pulls branch `st`.

Do not download full CPJUMP1 images to the Mac. Raw images, model checkpoints, large feature files, and caches should live on the GPU server only. Pull back only metrics, figures, small logs, and reports.

See `remote_execution_plan.md` for the detailed SSH, tmux, git, and result-transfer workflow.

## Figure Plan

Use real experimental outputs for results figures:

1. Dataset composition plot.
2. Baseline metric comparison.
3. UMAP/PCA representation plot.
4. Per-compound replicate mAP distribution.
5. Artifact sensitivity plot.
6. Ablation table or bar plot.

Use GPT image generation only for a conceptual overview figure if needed:

- Example: HCS image stack to encoder to well-level representation to retrieval metrics.
- Do not use generated images as evidence.

## Tmux Plan

Use separate sessions:

```text
tmux new -s st_download
tmux new -s st_extract
tmux new -s st_train
tmux new -s st_eval
```

Logging convention:

```text
st/outputs/logs/YYYYMMDD_HHMM_command_name.log
```

Every long command should:

- Print environment info.
- Print config path.
- Print output path.
- Save progress and final metrics.

## 2.5-Day Schedule

### Day 0, First Half Day: Freeze Benchmark And Smoke Test

Goals:

- Create benchmark config.
- Implement metadata filtering and split creation.
- Download a tiny subset: 1-2 wells from one plate.
- Run image loading and one encoder smoke test.
- Verify feature parquet or CSV output.
- Verify metric code on toy features.

Deliverables:

- `st/README.md` draft.
- `st/configs/subset_u2os_compound_4plate.yaml`.
- Smoke-test feature file.
- Smoke-test metric file.

Exit criterion:

- One command can produce features for a small subset.
- One command can compute at least replicate retrieval on that subset.

### Day 1: Baselines

Goals:

- Download primary subset or fallback subset.
- Run CellProfiler conversion if real profiles are available.
- Extract DINOv2 features.
- Extract CLIP or ImageNet features.
- Try OpenPhenom only if dependency setup is smooth.
- Compute all four metrics for available baselines.

Deliverables:

- Feature files under `st/outputs/features/`.
- Metric CSVs under `st/outputs/metrics/`.
- Initial comparison table.

Exit criterion:

- At least three baselines have valid metric rows.

### Day 2: Training And Ablations

Goals:

- Train one lightweight SSL or contrastive variant.
- Run 2-4 ablations:
  - channel grouping.
  - aggregation mean vs median.
  - plate normalization.
  - well-aware positives or supervised contrastive.
- Evaluate all variants on the same frozen metrics.

Deliverables:

- Trained checkpoints.
- Ablation metrics.
- Runtime and cost table.

Exit criterion:

- At least one trained variant beats a generic baseline on the primary metric or gives a useful negative result.

### Day 2.5: Figures And Analysis

Goals:

- Generate all paper figures.
- Write experiment report.
- Identify best method and failure cases.
- Commit repository.

Deliverables:

- `st/reports/experiment_report.md`.
- `st/outputs/figures/`.
- Clean README with reproduction commands.
- Git commit.

Exit criterion:

- A reader can understand the benchmark, reproduce the main table, and see all figures.

## Risk Register

Risk: Full image download is too large.

Mitigation:

- Use fluorescent-only channels.
- Start with 2 plates.
- Use site subsampling.
- Cache features immediately.

Risk: OpenPhenom dependency setup takes too long.

Mitigation:

- Treat OpenPhenom as optional.
- Replace with ImageNet ResNet/ViT if blocked for more than 2 hours.

Risk: Training does not improve results.

Mitigation:

- Report rigorous negative result.
- Focus analysis on why generic or classical baselines perform better.
- Emphasize benchmark contribution and artifact analysis.

Risk: Metrics are unstable on small subset.

Mitigation:

- Bootstrap confidence intervals.
- Report per-compound distributions, not just mean.
- Keep artifact score visible.

Risk: Features learn plate identity.

Mitigation:

- Hold out one plate.
- Include artifact sensitivity metric.
- Apply plate-wise robust normalization as an ablation.

## Immediate Next Implementation Step

Implement a minimal benchmark scaffold in `st/`:

1. `st/configs/subset_u2os_compound_4plate.yaml`
2. `st/src/st_benchmark/metadata.py`
3. `st/src/st_benchmark/metrics.py`
4. `st/scripts/make_subset_metadata.py`
5. `st/scripts/run_smoke_metrics.py`

Before downloading large images, the smoke metric should run from existing metadata and synthetic features. This will validate the benchmark logic cheaply.
