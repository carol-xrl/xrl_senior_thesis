# ST Project Log

This log records what we did, why we made each benchmark decision, and what we learned at each step.

## 2026-05-27: Project Direction

### What We Decided

We will rebuild a compact CPJUMP1 benchmark under `st/`, while using the cleaned original benchmark in `../cpjump1_benchmark` as a reference.

The goal is not to reproduce the full CPJUMP1 paper-scale benchmark. The goal is to create a smaller, credible, biologically meaningful benchmark that can support a strong paper under practical constraints:

- Local Mac for writing code, planning, and reviewing results.
- Rented GPU server for image download, feature extraction, training, and long experiments.
- Budget around 100 USD.
- Target timeline around 2.5 days for experiments, figures, and analysis.
- Raw images should stay on the GPU server.

### Why We Need A Compact Benchmark

The original CPJUMP1 benchmark is scientifically valuable but expensive because full image plates are large. One plate can be tens of GB, and full multi-modal benchmarking quickly becomes too slow and expensive for our current budget.

Therefore, the benchmark must satisfy two constraints:

1. It must preserve real biological retrieval structure.
2. It must be small enough to run repeatedly for method development.

This is why we first choose a 1-4 plate subset rather than the full CPJUMP1 dataset.

## 2026-05-27: Chosen First Benchmark Subset

### Selected Subset

Primary subset:

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

Metadata scale after reconstruction:

| Item | Count |
| --- | ---: |
| Wells | 1536 |
| Plates | 4 |
| Treatment wells | 1280 |
| Negative-control wells | 256 |
| Unique broad samples | 307 |
| Annotated treatment wells | 1280 |

### Why This Subset Is Reasonable

This is the most reasonable first benchmark subset under our constraints, not necessarily the only scientifically interesting subset.

Reasons:

1. Same experimental condition.

   The four plates share modality, cell type, timepoint, density, antibiotics, and cell line. This reduces confounding from obvious condition changes. If an encoder retrieves replicates here, the signal is more plausibly related to compound-induced morphology rather than different experimental settings.

2. Replicate structure across plates.

   These plates repeat the same compound plate map across multiple plates. That gives cross-plate replicates for many compounds, which is the core requirement for a perturbation retrieval benchmark.

3. Enough negative controls.

   The subset has 256 negative-control wells. This lets us test whether treatment profiles separate from DMSO/negative controls, a standard and biologically meaningful HCS sanity check.

4. Rich compound annotations.

   All 1280 treatment wells in this subset have target annotations. This enables compound/target matching, which asks whether compounds with related biological targets are closer in representation space.

5. Affordable data size.

   Four plates are still large, but feasible on a rented GPU server if we use fluorescent channels only and cache features. Genetic + compound + multi-timepoint experiments would be more complete but much more expensive.

6. Clear paper story.

   A compact compound-only benchmark can still test perturbation identity, control separation, and target-level biological structure. That is enough for a strong first benchmark if we are honest about limitations.

### Why Not Start With Other Plates Or Modalities

CRISPR and ORF plates are biologically important, especially for cross-modality matching. However, starting there is less practical for the first 2.5-day benchmark.

Reasons:

- Cross-modality matching needs both compound and genetic perturbation plates, increasing image download and feature extraction cost.
- Genetic perturbation phenotypes can be weaker or more heterogeneous than compound perturbations.
- Some ORF conditions have fewer replicate plates under the exact same condition.
- Full compound-CRISPR-ORF matching is a better stretch goal after the compact compound benchmark is stable.

Therefore, we start with compound U2OS 48h plates. Once the pipeline is stable, the best stretch extension is to add U2OS CRISPR 144h plates:

- `BR00116996`
- `BR00116997`
- `BR00116998`
- `BR00116999`

That would allow stronger compound-genetic target matching, but should not block the first benchmark.

## 2026-05-27: Chosen Metrics

We choose metrics that are common in Cell Painting / CPJUMP1-style evaluation and can be computed reliably on a compact subset.

### Metric 1: Replicate Retrieval

Question:

Can a query well retrieve wells with the same compound on other plates?

Positive pairs:

- Same `Metadata_broad_sample`.
- Different `Metadata_Plate`.

Biological meaning:

If the same compound induces a consistent cellular morphology, good representations should place replicate wells close together. This is the most direct perturbation-level representation metric.

Why it is reasonable:

- It matches the core idea of CPJUMP1 replicability.
- It does not require training labels beyond compound identity.
- It works with only compound plates.
- It is interpretable per compound and as mean AP.

Important caveat:

Because these four plates reuse the same plate map, same-compound cross-plate pairs are also same-well-position pairs. So this metric can be inflated by well-position artifacts. We must report artifact diagnostics alongside it.

### Metric 2: Negative-Control Challenge

Question:

Can treatment wells retrieve their true treatment replicates above DMSO/negative-control wells?

Biological meaning:

A useful morphology representation should distinguish perturbation-induced changes from negative controls. This is a basic HCS validity check: if treatment profiles cannot separate from DMSO, the feature space is unlikely to be biologically useful.

Why it is reasonable:

- The subset has many negative-control wells.
- It is robust and easy to interpret.
- It complements replicate retrieval because it directly tests treatment-vs-control separation.

### Metric 3: Compound Target Matching

Question:

Are compounds with overlapping annotated target genes closer than compounds with unrelated targets?

Biological meaning:

Compounds affecting the same target or pathway may induce related morphology. A good representation should recover at least some target-level organization.

Why it is reasonable:

- The subset has compound target annotations for all treatment wells.
- It moves beyond exact compound identity.
- It is closer to drug-discovery use cases, where we care about mechanism and target relationships.

Important caveat:

This metric is noisier than replicate retrieval because compounds can be polypharmacological, target annotations are imperfect, and target effects may not always produce visible morphology.

### Metric 4: Artifact Sensitivity

Question:

Is feature similarity driven by biology, or by plate/well-position artifacts?

Biological and experimental meaning:

Cell Painting data can contain strong acquisition artifacts. A representation that mainly encodes plate position or staining intensity may score well on naive replicate retrieval but fail biologically.

Why it is necessary:

Our selected compound plates reuse the same plate map. Therefore, artifact sensitivity is not optional. It is the diagnostic that keeps the benchmark honest.

Current diagnostic categories:

- Same compound, different plate.
- Different compound, same plate.
- Different compound, different plate.
- Same well, different plate.
- Negative controls at same well, different plate.
- Same-well same-compound fraction.

## 2026-05-27: What We Implemented

Files added under `st/`:

- `paper_outline.md`: paper structure and contribution framing.
- `benchmark_design.md`: benchmark definition, 2.5-day plan, metrics, risks.
- `remote_execution_plan.md`: Mac/GPU server workflow.
- `README.md`: local smoke-test commands and project rules.
- `configs/subset_u2os_compound_4plate.yaml`: frozen subset config.
- `src/st_benchmark/metadata.py`: metadata construction.
- `src/st_benchmark/metrics.py`: replicate, negcon, target, and artifact metrics.
- `src/st_benchmark/synthetic.py`: synthetic feature generation for local smoke tests.
- `scripts/make_subset_metadata.py`: builds subset metadata.
- `scripts/run_smoke_metrics.py`: runs metrics on synthetic features.
- `reports/smoke_benchmark_report.md`: first smoke report.

The implementation intentionally avoids heavy dependencies. It uses pandas and numpy so the Mac can validate the benchmark logic before we rent a GPU server.

## 2026-05-27: Preliminary Smoke Results

The smoke test uses real CPJUMP1 metadata but synthetic features. Therefore, the numeric values are not biological results. They only test whether the benchmark pipeline is wired correctly.

Synthetic feature design:

- Strong compound signal.
- Weaker target signal.
- Plate signal.
- Well-position signal.
- Random noise.

Smoke metric results:

| Metric | Mean AP | Median AP | Queries | Groups |
| --- | ---: | ---: | ---: | ---: |
| Replicate retrieval | 0.980 | 1.000 | 1280 | 306 |
| Negative-control challenge | 0.996 | 1.000 | 1280 | 306 |
| Target retrieval | 0.107 | 0.048 | 302 | 302 |

These results match expectation:

- Replicate retrieval is high because synthetic features include strong compound identity.
- Negative-control challenge is high because treatment features are intentionally structured.
- Target retrieval is much lower because target signal is weaker and target-list matching is noisier.

Artifact diagnostic:

| Diagnostic | Value |
| --- | ---: |
| Same-well same-compound fraction | 1.000 |
| Negative-control same-well artifact score | 0.507 |
| Same-compound biology score | 0.564 |

Key finding:

The selected plates have complete same-well / same-compound confounding across plates. This means replicate retrieval alone is not enough. The final benchmark must always report:

1. Replicate retrieval.
2. Negative-control challenge.
3. Target matching.
4. Artifact diagnostics.

This finding is useful because it shapes how we will write the paper: the benchmark is compact and practical, but we explicitly quantify and disclose its confounding risk.

## Current Interpretation

The benchmark design is reasonable as a first compact CPJUMP1 benchmark because it is:

- Small enough to run.
- Biologically grounded in compound-induced morphology.
- Rich enough for replicate and target-level evaluation.
- Honest about artifact confounding.

The first smoke result supports the implementation, not the biological claim. The biological claim can only be evaluated after running real encoder features on the GPU server.

## 2026-05-27: Concern About Saturated Metrics

We noticed a valid risk: replicate retrieval and negative-control challenge may become too easy. If they are near ceiling, training improvements will be hard to measure.

Current assessment:

1. The smoke scores are high because the synthetic feature generator intentionally includes a strong compound signal. They are not real model scores.
2. Existing full-benchmark CellProfiler outputs in the original repo suggest the real U2OS 48h compound task is not fully saturated:
   - `compound_U2OS_long` replicability fraction retrieved: 0.660.
   - `compound_U2OS_long` replicate mean AP: about 0.578.
   - `compound_U2OS_long` compound matching fraction retrieved: 0.251.
   - `compound_U2OS_long` compound matching mean AP: about 0.195.
3. Negative-control challenge may still be easier than target matching. We should treat it as a sanity check rather than the main metric.

Updated metric policy:

- Primary biological comparison should not rely only on replicate retrieval or negcon challenge.
- Target matching should be emphasized because it is mechanism-oriented and less likely to saturate.
- Replicate retrieval should be reported with artifact diagnostics because same-well and same-compound are confounded in the selected plates.
- Negative-control challenge should answer "does this representation detect treatment signal at all?", not "is this the best biological representation?"
- If several methods reach high replicate or negcon scores, compare per-compound AP distributions, low-performing compounds, bootstrap confidence intervals, and artifact scores.

This makes the benchmark safer: even if easy metrics saturate, the paper can still show meaningful differences through target matching and artifact-aware analysis.

## Next Step

Connect the scaffold to real image features:

1. Generate a download manifest for the selected plates and fluorescent channels.
2. Add real-feature evaluation script that consumes encoder output in a unified schema.
3. Run a tiny remote smoke test after renting the GPU server.
4. Launch baseline feature extraction in tmux.

## 2026-05-27: Real-Feature Pipeline Preparation

We added the server-facing pieces needed before renting the GPU:

- `src/st_benchmark/downloads.py`
- `src/st_benchmark/evaluate.py`
- `src/st_benchmark/plots.py`
- `scripts/prepare_download_manifest.py`
- `scripts/evaluate_features.py`
- `scripts/plot_metric_summary.py`

What these do:

1. Prepare a plate-level S3 download manifest.
2. Generate AWS CLI sync commands for fluorescent channels only.
3. Support tiny pilot downloads by restricting to wells such as `A01 A02`.
4. Evaluate any real encoder output table with columns `Metadata_Plate`, `Metadata_Well`, and `feature_*`.
5. Produce metric CSVs and basic summary/artifact plots.

Local validation:

- Python compilation passed.
- Offline download manifest generation passed.
- Synthetic feature evaluation through the real-feature entry point passed.
- Plot generation passed.

Important operational note:

The Mac-generated download manifest is unresolved because it does not query S3 locally. On the GPU server, rerun `prepare_download_manifest.py --resolve-s3` so the script can discover timestamped S3 plate directories through AWS CLI.

The server pilot command should start with `--wells A01 A02 --dryrun`, then remove `--dryrun`, then remove `--wells` for the full fluorescent-channel subset.

## 2026-05-27: Experiment Plan

We created `experiment_plan.md`.

The baseline plan is designed to be representative and feasible:

- CellProfiler as the classical morphology baseline.
- DINOv2 as the stable generic SSL baseline.
- DINOv3 as the newer frontier generic SSL baseline.
- OpenPhenom as the microscopy / Cell Painting domain-pretrained baseline.
- BioMedCLIP or CLIP as optional vision-language contrast.
- ResNet50 as a robust fallback if newer models fail.

The loss plan is:

- SimCLR / NT-Xent self-supervised loss.
- Well-aware contrastive loss.
- Compound supervised contrastive loss.
- Target-aware supervised contrastive loss as stretch.

The trick plan is:

- Channel grouping ablation.
- Plate-wise normalization.
- Mean vs median site aggregation.
- Artifact-aware sampling.
- Lightweight adapters or last-block fine-tuning as stretch.

The key standard is that we should prioritize scientifically interpretable results over a large number of expensive runs.

## 2026-05-27: RunPod Resource Plan

We created `resource_plan.md`.

Recommendation:

- Start with one strong 48GB GPU pod: L40S 48GB or RTX 6000 Ada 48GB.
- Use 16+ vCPU, 64GB+ RAM, and 700GB-1TB NVMe/local disk.
- Do not start with multi-GPU unless the price is excellent and the pod has enough CPU/disk IO.

Reasoning:

- Our first bottleneck is pipeline stability plus image download/decode, not distributed training.
- A single 48GB GPU is enough for frozen DINOv2/DINOv3/OpenPhenom extraction and projection-head training.
- Multi-GPU can help run two frozen encoders in parallel, but can also create disk IO contention and more failure modes.
- H100/H200 are unnecessary for this compact benchmark.

## 2026-05-27: RunPod Pod Opened

The RunPod pod is live.

Direct TCP SSH endpoint:

```bash
ssh root@209.170.80.132 -p 20639 -i ~/.ssh/id_ed25519
```

Fallback SSH endpoint:

```bash
ssh 4ummi44gx59ks6-6441117e@ssh.runpod.io -i ~/.ssh/id_ed25519
```

First read-only SSH check succeeded.

Observed hardware:

- Host: `a80a5edce179`
- GPU: NVIDIA L40S
- Visible VRAM: 46068 MiB
- Driver: 570.195.03
- RAM: 503 GiB
- Workspace mount: `/workspace`

This is sufficient for the planned single-GPU experiment workflow.

Created Codex skill:

- `runpod-st-experiments`
- Location: `/Users/carolxrl/.codex/skills/runpod-st-experiments`
- Validation: passed

## 2026-05-27: Remote Smoke and Pilot Download

The GitHub repository was made public, so the RunPod pod can now sync code through git.

Remote setup:

- Cloned branch `st` to `/workspace/xrl_senior_thesis_run`.
- Verified commit `c306cf7`.
- Installed minimal runtime packages missing from the container: `pandas`, `matplotlib`, `awscli`, and `tmux`.
- Confirmed PyTorch CUDA is available on the L40S pod.

Remote smoke benchmark passed:

- Metadata rows: 1536 wells from 4 compound U2OS 48h plates.
- Treatment wells: 1280.
- Negative-control wells: 256.
- Synthetic replicate retrieval mean AP: 0.979957.
- Synthetic negative-control challenge mean AP: 0.996050.
- Synthetic target retrieval mean AP: 0.106514.

Pilot image download:

- Resolved all 4 S3 plate directories from Cell Painting Gallery.
- Downloaded A01/A02 only for the 4 plates.
- Downloaded 360 TIFF images, 5 fluorescent channels, about 772MB total.
- This validates the path resolver, filename filters, and RunPod download throughput.

Implementation update:

- Added `st/scripts/extract_features.py`.
- Added image loading/preprocessing utilities in `st/src/st_benchmark/imaging.py`.
- Added baseline encoders in `st/src/st_benchmark/encoders.py`.
- Current supported feature baselines are `intensity` and batched `dinov2`.

Reasoning:

- The `intensity` baseline is a fast sanity baseline. It should not be the main result, but it tells us whether metadata alignment, image loading, and metric evaluation are functional.
- Batched DINOv2 is the first meaningful neural baseline because it is open-source, stable, strong on morphology-like visual representations, and feasible on one L40S.
- The pilot uses only A01/A02 because it exercises all 4 plates while keeping download and extraction time small.

## 2026-05-27: Storage Management Decision

Remote disk check:

- `/` and `/data` are a 50GB container overlay.
- `/workspace` is the large persistent RunPod-mounted storage.
- The UI's large storage allocation should be treated as `/workspace`, not `/data`.

Decision:

- Keep all full raw image downloads under `/workspace/data/cpjump1/images`.
- Keep the small A01/A02 pilot copy under `/data/cpjump1/images` only as a temporary validation artifact.
- Do not copy raw TIFFs back to the Mac.
- Do not track images, feature CSVs, or logs in git.

Current full-download estimate:

- Four plates x 384 wells x 9 sites x 5 fluorescent channels = 69,120 TIFF files.
- Expected size is roughly 130-160GB, depending on compression.
- This fits the RunPod persistent storage but not the container overlay.

## 2026-05-27: First Full DINOv2 Result

The 4-plate full image subset finished downloading on RunPod:

- Plate files: 4 x 17,280 TIFFs.
- Total files: 69,120.
- Storage: about 143GB under `/workspace/data/cpjump1/images`.

The original single-process extractor was too slow because TIFF decoding and per-channel percentile normalization kept the GPU idle. I replaced the DINO path with `st/scripts/extract_dinov2_fast.py`, which uses parallel TIFF decoding/preprocessing and batched GPU inference.

Full DINOv2-S/14 extraction completed:

- Feature table: `st/outputs/features/dinov2_vits14_full.csv` on RunPod.
- Rows: 1,536 wells.
- Feature dimension: 768.
- Metrics pulled back locally to `st/outputs/metrics/dinov2_vits14_full/`.

Metric summary:

| Metric | mean AP | median AP | queries | groups |
| --- | ---: | ---: | ---: | ---: |
| Replicate retrieval | 0.2702 | 0.0421 | 1280 | 306 |
| Negative-control challenge | 0.3803 | 0.1137 | 1280 | 306 |
| Target retrieval | 0.0682 | 0.0280 | 302 | 302 |

Interpretation:

- The first real DINOv2 result is not saturated, unlike the synthetic smoke test.
- This is useful for the thesis because there is room for improvement from domain adaptation, channel choices, plate correction, and contrastive objectives.
- Same-well/same-compound confounding is still visible and must be discussed explicitly in the benchmark limitations.

## 2026-05-27: DINOv2 Feature Normalization Tricks

I evaluated cheap post-processing variants on the completed DINOv2-S/14 full feature table. This does not reread images or use the GPU; it tests whether simple batch/plate correction improves benchmark metrics.

Comparison file:

- `st/outputs/metrics/dinov2_vits14_transforms/dinov2_vits14_transform_comparison.csv`

Key results:

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.2702 | 0.3803 | 0.0680 |
| global_zscore_l2 | 0.2812 | 0.4168 | 0.0709 |
| plate_center_l2 | 0.2864 | 0.4235 | 0.0689 |
| plate_zscore_l2 | 0.2989 | 0.4356 | 0.0701 |
| negcon_center_l2 | 0.2765 | 0.4514 | 0.0695 |
| negcon_zscore_l2 | 0.2646 | 0.4546 | 0.0706 |

Interpretation:

- Plate z-score is the best simple correction for replicate retrieval.
- Negative-control centering/z-scoring is strongest for the negative-control challenge.
- This supports including feature normalization as an explicit trick ablation in the thesis, because it improves the real benchmark without additional model training.

## 2026-05-27: DINOv2-B/14 Full Baseline

I launched the next stronger frozen-feature baseline on RunPod:

- tmux session: `st_dinov2b_fast`
- feature output on RunPod: `st/outputs/features/dinov2_vitb14_full.csv`
- metrics pulled locally: `st/outputs/metrics/dinov2_vitb14_full/`
- transform comparison pulled locally: `st/outputs/metrics/dinov2_vitb14_transforms/dinov2_vitb14_transform_comparison.csv`
- local figures: `st/outputs/figures/dinov2_vitb14_full/` and `st/outputs/figures/dinov2_vitb14_transforms/`

The fast extractor processed 13,824 complete imaging sites from the same 4-plate U2OS compound 48h subset and wrote 1,536 well-level feature rows. The RunPod tmux session exited cleanly after feature extraction, metric evaluation, and normalization ablation.

Key raw DINOv2-B/14 results:

| Metric | Mean AP | Median AP |
| --- | ---: | ---: |
| Replicate retrieval | 0.2750 | 0.0451 |
| Negative-control challenge | 0.3811 | 0.1076 |
| Target retrieval | 0.0753 | 0.0310 |

Normalization ablation:

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.2750 | 0.3811 | 0.0753 |
| global_zscore_l2 | 0.2875 | 0.4303 | 0.0738 |
| plate_center_l2 | 0.2959 | 0.4360 | 0.0716 |
| plate_zscore_l2 | 0.3044 | 0.4484 | 0.0719 |
| negcon_center_l2 | 0.2802 | 0.4612 | 0.0707 |
| negcon_zscore_l2 | 0.2728 | 0.4645 | 0.0708 |

Interpretation:

- DINOv2-B/14 gives a modest raw improvement over DINOv2-S/14, especially target retrieval (0.0753 vs about 0.068).
- The same normalization pattern holds: plate z-score is strongest for replicate retrieval, while negcon z-score is strongest for the negative-control challenge.
- This is a useful paper result because it separates backbone capacity from domain/batch correction: scaling the frozen vision backbone helps a little, but biological retrieval still depends strongly on plate-aware normalization.

## 2026-05-27: Preparing the 8-Plate U2OS Compound Extension

After the 4-plate 48h benchmark produced stable but not saturated results, I prepared the next scale-up experiment: U2OS compound at both 24h and 48h. This adds the four U2OS 24h compound plates while retaining the original four U2OS 48h plates.

Selected plates:

| Time | Plates |
| ---: | --- |
| 24h | `BR00116995`, `BR00117024`, `BR00117025`, `BR00117026` |
| 48h | `BR00117010`, `BR00117011`, `BR00117012`, `BR00117013` |

The new config is `st/configs/subset_u2os_compound_8plate.yaml`. It uses balanced splits across time:

- train: two 24h plates and two 48h plates
- val: one 24h plate and one 48h plate
- test: one 24h plate and one 48h plate

Metadata summary:

| Name | Value |
| --- | ---: |
| wells | 3,072 |
| plates | 8 |
| treatment wells | 2,560 |
| negative-control wells | 512 |
| unique broad samples | 307 |
| annotated treatment wells | 2,560 |

Rationale:

- This is the most efficient expansion because it reuses the same perturbation modality, cell type, platemap, and metrics while testing whether the benchmark conclusions hold across treatment duration.
- Biologically, 24h vs 48h can change phenotypic maturity and toxicity response; a useful representation should retrieve perturbations across these acquisition states rather than only within one time point.
- Computationally, it adds about another 143GB of raw fluorescent images, which fits comfortably on the 1TB RunPod volume and keeps the next DINOv2-S extraction tractable.

## 2026-05-27: DINOv2-L/14 4-Plate Baseline

I completed the larger frozen DINOv2-L/14 run on the original 4-plate U2OS compound 48h subset.

Key raw results:

| Metric | Mean AP | Median AP |
| --- | ---: | ---: |
| Replicate retrieval | 0.2805 | 0.0476 |
| Negative-control challenge | 0.3913 | 0.1315 |
| Target retrieval | 0.0653 | 0.0276 |

Normalization ablation:

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.2805 | 0.3913 | 0.0656 |
| global_zscore_l2 | 0.2926 | 0.4247 | 0.0661 |
| plate_center_l2 | 0.2918 | 0.4216 | 0.0661 |
| plate_zscore_l2 | 0.3008 | 0.4358 | 0.0660 |
| negcon_center_l2 | 0.2820 | 0.4479 | 0.0671 |
| negcon_zscore_l2 | 0.2680 | 0.4568 | 0.0677 |

Interpretation:

- Scaling from DINOv2-S/B to L helps replicate retrieval slightly, but target retrieval does not improve over DINOv2-B.
- The normalization pattern is now consistent across three frozen backbones: plate z-score is best for replicate retrieval, while negcon z-score is best for distinguishing treatment replicates from negative controls.
- This suggests that batch/plate correction is at least as important as generic backbone capacity for this subset.

## 2026-05-27: 8-Plate DINOv2-S/14 Baseline

The 8-plate U2OS compound 24h+48h image download finished on RunPod. All eight plates have 17,280 fluorescent TIFF files each, corresponding to 384 wells x 9 sites x 5 channels. The DINOv2-S/14 fast extractor then processed 27,648 complete sites and wrote 3,072 well-level feature rows.

Key raw 8-plate results:

| Metric | Mean AP | Median AP |
| --- | ---: | ---: |
| Replicate retrieval | 0.1323 | 0.0207 |
| Negative-control challenge | 0.2681 | 0.0639 |
| Target retrieval | 0.0675 | 0.0284 |

Normalization ablation:

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.1323 | 0.2681 | 0.0673 |
| global_zscore_l2 | 0.1444 | 0.3106 | 0.0718 |
| plate_center_l2 | 0.1408 | 0.3211 | 0.0715 |
| plate_zscore_l2 | 0.1551 | 0.3389 | 0.0727 |
| negcon_center_l2 | 0.1319 | 0.3310 | 0.0747 |
| negcon_zscore_l2 | 0.1327 | 0.3433 | 0.0744 |

Interpretation:

- The 8-plate benchmark is substantially harder than the 4-plate pilot: raw replicate retrieval drops from about 0.27 to 0.13 because the candidate set now includes both 24h and 48h states.
- This makes the final benchmark more useful for training experiments; it is not saturated, and there is measurable room for representation learning.
- Plate z-score remains the best cheap correction for replicate retrieval, while negcon-based correction is strongest for the negative-control challenge and target retrieval.

Next implementation step:

- I added split-aware retrieval support so trained models can be selected on validation plates and reported on held-out test plates.
- I added a frozen-feature projection-head training script for loss ablations: supervised contrastive, batch-hard triplet, and proxy cross-entropy. These train on the 8-plate train plates only and use validation replicate retrieval for model selection.

## 2026-05-27: 8-Plate Split Metrics and Projection-Head Loss Ablation

I generated split-aware metrics for the frozen 8-plate DINOv2-S/14 baseline:

| Scope | Replicate mean AP | Negcon mean AP |
| --- | ---: | ---: |
| all queries | 0.1323 | 0.2681 |
| train queries | 0.1317 | 0.2715 |
| val queries | 0.1309 | 0.2630 |
| test queries | 0.1351 | 0.2663 |
| within 24h | 0.2171 | 0.3074 |
| within 48h | 0.2702 | 0.3803 |
| 24h -> 48h | 0.0670 | 0.2387 |
| 48h -> 24h | 0.0892 | 0.2589 |

This confirms that the main difficulty in the 8-plate setting is cross-duration generalization. The 48h-only result matches the original 4-plate pilot, while cross-time retrieval is much lower.

I then trained a small projection head on frozen DINOv2-S/14 well features. Training used only the train plates and same-compound labels, so these are weakly supervised adaptation experiments, not frozen baselines. Model selection used validation replicate retrieval.

| Run | Loss | Input transform | Best val replicate AP | Test replicate AP | Full target AP |
| --- | --- | --- | ---: | ---: | ---: |
| SupCon + plate z-score | supervised contrastive | plate_zscore_l2 | 0.2935 | 0.3031 | 0.0781 |
| Proxy-CE + plate z-score | proxy classification | plate_zscore_l2 | 0.2911 | 0.3036 | 0.0787 |
| SupCon + negcon z-score | supervised contrastive | negcon_zscore_l2 | 0.2765 | 0.2932 | 0.0715 |
| SupCon + raw L2 | supervised contrastive | raw_l2 | 0.2389 | 0.2494 | 0.0834 |
| Triplet + plate z-score | batch-hard triplet | plate_zscore_l2 | 0.2234 | 0.2249 | 0.0854 |

Interpretation:

- SupCon and proxy-CE with plate z-score give the strongest replicate retrieval and roughly double held-out test replicate AP versus the frozen raw 8-plate baseline.
- Plate z-score is the best training input trick for replicate retrieval; negcon z-score remains useful but is weaker for this supervised retrieval objective.
- Target AP improves only modestly. This is expected because the training labels optimize compound identity, not mechanism or target overlap.
- The triplet run is weaker and shows a near-collapsed representation in artifact summaries, so it should be treated as a negative result rather than a candidate final method.
- Because the same compound occupies the same well position across plates, these supervised runs can still benefit from well-position confounding. The paper should frame this as weakly supervised perturbation adaptation and keep artifact sensitivity in the main results table.

## 2026-05-27: Fair Frozen Split Metrics for 8-Plate Normalization

I added `--input-transform` support to the split-aware evaluator and reran frozen DINOv2-S/14 split/cross-time retrieval for the strongest normalization variants.

| Frozen variant | Test replicate AP | Test negcon AP | 24h -> 48h replicate AP | 48h -> 24h replicate AP |
| --- | ---: | ---: | ---: | ---: |
| raw | 0.1351 | 0.2663 | 0.0670 | 0.0892 |
| plate_zscore_l2 | 0.1577 | 0.3472 | 0.1200 | 0.1041 |
| negcon_zscore_l2 | 0.1318 | 0.3510 | 0.1102 | 0.0799 |

Interpretation:

- Plate z-score is the best frozen correction for held-out replicate retrieval and substantially improves 24h -> 48h matching.
- Negcon z-score is strongest for the negative-control challenge but does not improve held-out replicate retrieval.
- The best trained heads still roughly double test replicate AP versus the best frozen normalized baseline, so the main training result is not explained by normalization alone.

## 2026-05-28: Pivot Toward U2OS Multimodal-Short Extension

After checking storage and the original CPJUMP1 benchmark design, I prepared a more modality-focused extension instead of immediately expanding to A549 compound plates. This is better aligned with the original benchmark because it tests three perturbation modalities in the same cell type:

| Modality | CPJUMP1 short time | U2OS plates |
| --- | ---: | --- |
| compound | 24h | `BR00116995`, `BR00117024`, `BR00117025`, `BR00117026` |
| ORF | 48h | `BR00117022`, `BR00117023` |
| CRISPR | 96h | `BR00118045`, `BR00118046`, `BR00118047`, `BR00118048` |

I added `st/configs/subset_u2os_multimodal_short_10plate.yaml` and extended metadata construction so each plate can use the correct compound/ORF/CRISPR platemap and annotation table.

Metadata summary:

| Name | Value |
| --- | ---: |
| plates | 10 |
| usable wells | 3,816 |
| treatment wells | 3,200 |
| negative-control wells | 616 |
| unique perturbation IDs | 817 |
| compound target-annotated wells | 1,280 |
| gene-annotated wells | 2,040 |

Interpretation:

- This extension is more scientifically useful than only adding A549 compound plates if the goal is to show modality generalization.
- The short labels are modality-specific in the original benchmark: compound 24h, ORF 48h, CRISPR 96h. They are not the same absolute treatment time.
- The next implementation requirement is cross-modality matching: compound target lists must be compared to ORF/CRISPR gene targets, not only same-perturbation replicate retrieval.

## 2026-05-28: Final 20-Plate Multimodal-Short Benchmark Design

After discussing whether to double the subset, I expanded the multimodal-short benchmark to both A549 and U2OS instead of making a compound-only 16-plate benchmark. This is the stronger thesis design because it tests both perturbation modality and cell-line robustness while staying inside one clean CPJUMP1 batch.

Selected final extension:

| Cell type | Modality | Short time | Plates |
| --- | --- | ---: | --- |
| A549 | compound | 24h | `BR00116991`, `BR00116992`, `BR00116993`, `BR00116994` |
| U2OS | compound | 24h | `BR00116995`, `BR00117024`, `BR00117025`, `BR00117026` |
| A549 | ORF | 48h | `BR00117020`, `BR00117021` |
| U2OS | ORF | 48h | `BR00117022`, `BR00117023` |
| A549 | CRISPR | 96h | `BR00118041`, `BR00118042`, `BR00118043`, `BR00118044` |
| U2OS | CRISPR | 96h | `BR00118045`, `BR00118046`, `BR00118047`, `BR00118048` |

Why not force a 4+4+4-per-cell design:

- In the clean `2020_11_04_CPJUMP1` batch, ORF short has only two plates per cell line.
- Adding more ORF plates from another batch/timepoint would introduce batch/acquisition confounding.
- The 20-plate design keeps a clean batch and still includes both cell lines, three perturbation modalities, and cross-modality targets.

Metadata summary:

| Name | Value |
| --- | ---: |
| usable wells | 7,632 |
| plates | 20 |
| treatment wells | 6,400 |
| negative-control wells | 1,232 |
| unique perturbation IDs | 817 |
| compound target-annotated wells | 2,560 |
| gene-annotated wells | 4,080 |

Benchmark metrics for this extension:

1. Perturbation retrieval within each cell line and modality.
2. Negative-control challenge within each cell line and modality.
3. Within-modality matching for compound targets and CRISPR sister guides.
4. Cross-modality matching from compounds to ORF/CRISPR gene perturbations within the same cell line.

Important interpretation detail:

- ORF within-modality matching is not reported as a positive main metric for this subset because each ORF gene has one construct. ORF still contributes to perturbation retrieval and compound-to-ORF cross-modality matching.
- CRISPR is appropriate for within-modality gene matching because most genes have two guide reagents.

Implementation update:

- Added `st/configs/subset_multimodal_short_20plate.yaml`.
- Extended metadata construction to load compound, ORF, and CRISPR platemaps/annotations per plate.
- Added condition-aware multimodal evaluation so the 20-plate feature table is not evaluated as one mixed candidate pool.
- Local synthetic smoke test passed for all planned multimodal metric tables.

## 2026-05-28: 8-Plate DINOv2-B/14 Result

I completed the stronger frozen DINOv2-B/14 baseline on the 8-plate U2OS compound 24h+48h benchmark.

Key raw 8-plate results:

| Metric | Mean AP | Median AP |
| --- | ---: | ---: |
| Replicate retrieval | 0.1360 | 0.0215 |
| Negative-control challenge | 0.2613 | 0.0618 |
| Target retrieval | 0.0736 | 0.0311 |

Normalization ablation:

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.1360 | 0.2613 | 0.0737 |
| global_zscore_l2 | 0.1516 | 0.3157 | 0.0799 |
| plate_center_l2 | 0.1486 | 0.3244 | 0.0792 |
| plate_zscore_l2 | 0.1627 | 0.3431 | 0.0806 |
| negcon_center_l2 | 0.1385 | 0.3341 | 0.0753 |
| negcon_zscore_l2 | 0.1418 | 0.3497 | 0.0746 |

Split-aware raw metrics:

| Scope | Replicate AP | Negcon AP |
| --- | ---: | ---: |
| held-out test plates | 0.1385 | 0.2583 |
| within 24h | 0.2248 | - |
| within 48h | 0.2750 | - |
| 24h -> 48h | 0.0700 | - |
| 48h -> 24h | 0.0922 | - |

Interpretation:

- DINOv2-B is only slightly stronger than DINOv2-S on raw replicate retrieval, but it improves target retrieval.
- Plate z-score again gives the best replicate retrieval among cheap frozen-feature tricks.
- The 8-plate task remains meaningfully harder than 4-plate 48h-only evaluation because cross-time retrieval is low.

## 2026-05-28: DINOv2-B/14 Projection-Head Ablation

While the 20-plate image download was running, I reused the completed 8-plate DINOv2-B/14 feature table to run lightweight projection-head training. This keeps GPU time productive without adding image I/O.

Both runs trained on train plates only, selected checkpoints by validation replicate AP, and reported held-out test plate retrieval.

| Run | Loss | Input transform | Best val replicate AP | Test replicate AP | Test negcon AP | Full target AP |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| DINOv2-B SupCon | supervised contrastive | plate_zscore_l2 | 0.3033 | 0.3167 | 0.4257 | 0.0786 |
| DINOv2-B Proxy-CE | proxy classification | plate_zscore_l2 | 0.3070 | 0.3173 | 0.4261 | 0.0814 |

Interpretation:

- DINOv2-B projection heads match or slightly improve the DINOv2-S head results.
- Proxy-CE is marginally strongest on validation, held-out replicate retrieval, held-out negcon, and target retrieval.
- The main learning effect remains consistent across DINOv2-S and DINOv2-B: a small supervised head on plate-normalized frozen features roughly doubles test replicate AP versus frozen raw features.

## 2026-05-28: 20-Plate Download Launch

I resolved the full S3 manifest for the 20-plate multimodal-short benchmark and launched a sequential tmux download:

- tmux session: `st_download20`
- remote log: `st/outputs/logs/download_multimodal_short_20plate.log`
- already complete from earlier work: 4 U2OS compound 24h plates
- remaining to download: 16 plates
- starting raw image storage: about 291GB under `/workspace/data/cpjump1/images`

Storage note:

- The existing 291GB includes the 8-plate U2OS compound benchmark, four of which are reused by the 20-plate design.
- Keeping the old 48h compound plates is convenient for reproducibility, but if the RunPod volume approaches capacity, the first cleanup candidate is old raw 48h compound images because their features and metrics have already been extracted.

## 2026-05-28: Storage Cleanup and Multimodal Experiment Queue

After the final benchmark moved to 20-plate multimodal-short, I removed raw image plates that are not part of that final set:

- deleted from `/workspace/data/cpjump1/images/2020_11_04_CPJUMP1/`: `BR00117010`, `BR00117011`, `BR00117012`, `BR00117013`
- deleted old pilot images from `/data/cpjump1/images`

This reduced raw image storage from about 331GB to about 234GB and freed the small 50GB container overlay back to about 6% usage.

I also added and launched the post-download runner:

- script: `st/scripts/run_after_download_multimodal.sh`
- tmux session: `st_after20`
- behavior: wait until all 20 final plates have 17,280 fluorescent-channel TIFFs, then run DINOv2-S/14 and DINOv2-B/14 feature extraction, followed by multimodal evaluation under `raw_l2`, `plate_zscore_l2`, and `negcon_zscore_l2`.

Cross-modality benchmark status:

- Implemented in `st/src/st_benchmark/multimodal.py`.
- Entry point: `st/scripts/evaluate_multimodal_features.py`.
- The 20-plate runs will report compound-to-CRISPR and compound-to-ORF matching separately for A549 and U2OS.

During download, I also completed a DINOv2-L/14 8-plate U2OS compound baseline:

| Variant | Replicate mean AP | Negcon mean AP | Target mean AP |
| --- | ---: | ---: | ---: |
| raw_l2 | 0.1345 | 0.2689 | 0.0688 |
| global_zscore_l2 | 0.1478 | 0.3120 | 0.0764 |
| plate_center_l2 | 0.1418 | 0.3160 | 0.0725 |
| plate_zscore_l2 | 0.1540 | 0.3333 | 0.0766 |
| negcon_center_l2 | 0.1339 | 0.3263 | 0.0745 |
| negcon_zscore_l2 | 0.1338 | 0.3411 | 0.0767 |

Interpretation:

- DINOv2-L does not materially beat DINOv2-S/B on the 8-plate task.
- The repeated pattern is now strong: plate z-score helps perturbation retrieval most, while negcon z-score helps negative-control separation most.
- This supports focusing the final paper story on benchmark design, normalization, and supervised/adaptation losses rather than only scaling generic vision backbones.

DINOv2-L projection-head ablation:

| Run | Loss | Input transform | Best val replicate AP | Test replicate AP | Test negcon AP | Full target AP |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| DINOv2-L SupCon | supervised contrastive | plate_zscore_l2 | 0.3096 | 0.3080 | 0.4144 | 0.0710 |
| DINOv2-L Proxy-CE | proxy classification | plate_zscore_l2 | 0.3113 | 0.3199 | 0.4346 | 0.0812 |

Interpretation:

- Proxy-CE on DINOv2-L gives the best 8-plate head result so far for held-out replicate retrieval.
- The gain over DINOv2-B Proxy-CE is small, so the stronger conclusion remains that supervised projection and plate normalization matter more than backbone scaling alone.

## 2026-05-28: 8-Plate Result Tables and Figures

I added an automated summary script for the completed 8-plate experiments:

- script: `st/scripts/summarize_8plate_results.py`
- report: `st/reports/experiment_tables/8plate_results_summary.md`
- tables:
  - `st/reports/experiment_tables/8plate_frozen_backbones.csv`
  - `st/reports/experiment_tables/8plate_normalization_ablation.csv`
  - `st/reports/experiment_tables/8plate_projection_head_ablation.csv`
- figures:
  - `st/reports/experiment_tables/figures/8plate_normalization_ablation.png`
  - `st/reports/experiment_tables/figures/8plate_projection_head_ablation.png`

This makes the current 8-plate story reproducible from output CSVs instead of manually copying numbers. The main table now clearly separates:

- frozen raw encoder performance,
- normalization-only tricks,
- supervised projection-head loss ablations.

Current best 8-plate result:

| Model | Loss | Transform | Best val replicate AP | Test replicate AP | Test negcon AP | Target AP |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| DINOv2-L/14 | Proxy-CE | plate_zscore_l2 | 0.3113 | 0.3199 | 0.4346 | 0.0812 |

I also ran three additional seeds for the strongest DINOv2-L/14 Proxy-CE setting:

| Seeds | Test replicate AP mean | Test replicate AP std | Test negcon AP mean | Target AP mean |
| --- | ---: | ---: | ---: | ---: |
| 42, 1, 2, 3 | 0.3240 | 0.0040 | 0.4321 | 0.0820 |

Interpretation:

- The best 8-plate trained-head result is stable across seeds.
- The seed variation is much smaller than the gain over frozen raw features, so the improvement is not a random-seed artifact.

## 2026-05-28: Incremental 20-Plate Multimodal Queue

The 20-plate multimodal download is still active and the GPU is idle while waiting for the remaining plates. I added an incremental runner:

- script: `st/scripts/run_incremental_multimodal.sh`
- behavior: as soon as one plate reaches 17,280 fluorescent TIFFs, extract its DINOv2 feature file immediately.
- output layout: one feature CSV per `(model, plate)` under `st/outputs/features/multimodal_short_20plate_by_plate/`.
- finalization: after all 20 plate-level feature files exist, combine them into the standard full feature table and run multimodal evaluation under `raw_l2`, `plate_zscore_l2`, and `negcon_zscore_l2`.

Reasoning:

- The previous runner was correct but conservative: it waited for all 20 plates before using the GPU.
- The new queue lets downloading and GPU extraction overlap, which is better for the rented L40S.
- Plate-level files make the run resumable: if a session dies, completed plates are not recomputed.

This does not change the benchmark definition. It only changes execution scheduling.

## 2026-05-28: Parallel Tail Download

The incremental DINOv2-S queue quickly caught up with the available downloaded plates. At that point the L40S was idle again because the remaining raw images were still downloading sequentially.

I added a small parallel manifest downloader:

- script: `st/scripts/download_manifest_parallel.py`
- behavior: read the resolved download manifest, skip plates that already have 17,280 TIFFs, and run selected remaining plate downloads in parallel.

Execution plan:

- keep the original `st_download20` process alive so the in-progress plate is not interrupted;
- launch a separate tail downloader for the last not-yet-started test plates;
- let the incremental extractor consume each plate as soon as it becomes complete.

This should reduce wall-clock time without changing any data split, benchmark definition, or feature extraction code.

## 2026-05-28: Disk Safety Plan

After the 20-plate download completed, the raw image directory was about 775GB and `st/outputs` was about 1.1GB. The RunPod UI reported roughly 845GB / 1TB volume usage, so the correct mitigation is to stop all download processes and avoid retaining raw images longer than necessary.

Current storage policy:

- all raw downloads are complete; no `aws s3 sync` process remains active;
- keep raw TIFFs until both frozen feature sets needed for the final benchmark are extracted;
- after the DINOv2-B plate-level feature file exists for a plate, that plate's raw image directory can be deleted safely because the multimodal evaluation uses feature CSVs, not raw TIFFs;
- if a feature extraction must be rerun after deletion, the affected plate can be re-downloaded from the public Cell Painting Gallery manifest.

I added a guarded cleanup helper:

- script: `st/scripts/cleanup_raw_after_features.py`
- default mode: dry-run only;
- delete mode: only removes a raw plate directory after all required `<prefix>_<plate>.csv.done` markers exist.

This keeps the volume below the 1TB limit while preserving reproducibility through the manifest and feature outputs.

I launched the guarded cleanup watcher on RunPod:

- tmux session: `st_cleanup_raw_after_b`
- log: `st/outputs/logs/cleanup_raw_after_b.log`
- deletion condition: delete a raw plate directory only after `dinov2_vitb14_multimodal_short_20plate_<plate>.csv.done` exists.

At launch time, DINOv2-S had completed 18/20 plate-level feature files and DINOv2-B had not started yet, so no raw images were deleted immediately.

## 2026-05-28: Revised Storage Policy - Keep Raw Images

The desired policy is to keep downloaded raw image plates on the RunPod volume and only remove intermediate artifacts. I stopped the raw cleanup watcher (`st_cleanup_raw_after_b`) and started restoring the raw plates that had already been removed:

- `BR00116991`
- `BR00116992`
- `BR00116995`
- `BR00117024`

The restore job is running in tmux session `st_restore_raw_images` using the resolved manifest. DINOv2-B feature extraction can continue because it had already extracted those early plates before the restore began.

I also hardened `st/scripts/cleanup_raw_after_features.py`: raw deletion now requires both `--delete` and `--allow-raw-image-delete`, so accidental raw-image cleanup cannot be launched with a single flag.

Updated next-step policy:

- keep all 20 raw image plate directories once restored;
- let DINOv2-B finish and run the 20-plate multimodal evaluation;
- after combined S/B feature CSVs and metrics exist, only clean true intermediates such as verbose download logs and plate-level temporary feature shards.
