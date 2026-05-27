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
