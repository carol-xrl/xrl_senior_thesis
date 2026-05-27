# Benchmark Design

## Objective

Build a compact but biologically meaningful CPJUMP1 benchmark that can be completed on one RunPod L40S while still testing more than compound-only replicate retrieval.

The current benchmark is the 20-plate multimodal subset, not the older 4-plate or 8-plate pilot.

It should answer four questions:

1. Do frozen image features retrieve exact perturbation replicates across plates?
2. Do normalization choices improve biological signal rather than only treatment/control separation?
3. Does light supervised adaptation improve replicate retrieval?
4. Can compound perturbations be aligned with gene perturbations across modality?

## Current Dataset

Config:

- `st/configs/subset_multimodal_short_20plate.yaml`

Generated metadata:

- `st/data/metadata/subset_multimodal_short_20plate_well_metadata.csv`
- `st/data/splits/subset_multimodal_short_20plate_splits.csv`
- `st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv`

Batch:

- `2020_11_04_CPJUMP1`

Scope:

| Field | Value |
| --- | --- |
| Plates | 20 |
| Cell types | A549, U2OS |
| Modalities | compound, ORF, CRISPR |
| Compound time | 24h |
| ORF time | 48h |
| CRISPR time | 96h |
| Channels | AGP, Mito, RNA, ER, DNA |
| Well rows | 7632 |
| Treatment wells | 6400 |
| Negative-control wells | 1232 |

Why this subset:

- It covers chemical perturbation, gene overexpression, and gene knockout rather than only one modality.
- It includes two cell contexts, so model behavior is not tied to U2OS only.
- It keeps the modality-specific CPJUMP1 time points as part of the protocol. Time is not the main scientific variable here; modality is.
- It fits inside a 1TB RunPod volume when we keep only fluorescent raw TIFFs and small derived outputs.

Important limitation:

- ORF has fewer plates in this selected condition than compound and CRISPR. The final design is therefore 8 compound plates, 8 CRISPR plates, and 4 ORF plates, rather than a symmetric 4+4+4 per cell-line layout.

## Plate Split

The split is plate-level. This tests held-out plate/image generalization, not held-out perturbation-identity generalization.

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

Well counts:

| Split | Wells |
| --- | ---: |
| train | 3816 |
| val | 1528 |
| test | 2288 |
| total | 7632 |

Training semantics:

- Frozen encoders run on all 20 plates without labels.
- Projection heads train only on train plates.
- Validation plates select checkpoints and hyperparameters.
- Test plates are reserved for split-aware final reporting.
- Current 20-plate summary tables aggregate all queries by condition. They are useful for method comparison, but the thesis should include held-out test-query tables.

## Data Units

Raw unit:

- one TIFF image for one channel and one site.

Site unit:

- five fluorescent channels for one field of view.

Well unit:

- mean aggregation of site-level features for one well.

Perturbation unit:

- used to define positives and labels, but evaluation is computed over well-level embeddings.

## Preprocessing And Features

Raw image policy:

- Keep raw TIFFs on RunPod under `/workspace/data/cpjump1/images`.
- Do not pull raw images back to the Mac.
- Pull back only metrics, reports, logs, and selected figures.
- Clean intermediate shards or caches only when raw image directories are protected.

Feature extraction:

- Load fluorescent channels only.
- Percentile-normalize each channel.
- Resize to 224 x 224.
- Encode two pseudo-RGB groups:
  - AGP, Mito, DNA
  - RNA, ER, DNA
- Concatenate the two encoder embeddings.
- Average site embeddings into one well-level feature.

Completed feature files:

| Encoder | Feature file |
| --- | --- |
| DINOv2-S/14 | `st/outputs/features/dinov2_vits14_multimodal_short_20plate.csv` |
| DINOv2-B/14 | `st/outputs/features/dinov2_vitb14_multimodal_short_20plate.csv` |

## Metrics

### 1. Replicate Retrieval

Question:

Can a query well retrieve wells with the same perturbation identity across other plates?

Positive pairs:

- same `Metadata_broad_sample`;
- different `Metadata_Plate`;
- same condition unless explicitly evaluating cross-condition behavior.

Metric:

- mean average precision.

Role:

- standard perturbation identity metric;
- most interpretable for compound and CRISPR;
- less stable for ORF because there are fewer ORF plates.

### 2. Negative-Control Challenge

Question:

Can a treatment query rank true perturbation replicates above negative controls?

Metric:

- mean average precision with negative controls included as distractors.

Role:

- sanity check for treatment/control separation;
- not sufficient as the main result because this metric can saturate and does not prove target-level biology.

### 3. Within-Modality Matching

Question:

Do features recover biological relationships inside one perturbation modality?

Definitions:

- compound: target-aware matching among annotated compounds;
- CRISPR: gene/sister-guide matching;
- ORF: no robust within-modality positives in the current subset, so this may be reported as missing or zero-query.

Role:

- more biological than exact replicate retrieval;
- useful when negative-control or replicate metrics are too easy.

### 4. Cross-Modality Matching

Question:

Can compound morphology align with genetic perturbation morphology for shared target/gene biology?

Definitions:

- compound -> CRISPR within the same cell line;
- compound -> ORF within the same cell line;
- compound labels use target genes;
- ORF/CRISPR labels use perturbation genes.

Metric:

- mean average precision.

Role:

- hardest and most thesis-worthy metric;
- expected to be low for frozen generic encoders;
- useful for separating exact perturbation clustering from biological mechanism alignment.

## Baselines And Adaptation

Completed frozen baselines:

- DINOv2-S/14;
- DINOv2-B/14;
- `raw_l2`;
- `plate_zscore_l2`;
- `negcon_zscore_l2`.

Completed trained heads:

- DINOv2-B + plate z-score + sample Proxy-CE;
- DINOv2-B + plate z-score + bio-target Proxy-CE.

Interpretation:

- Frozen DINOv2 is the label-free baseline.
- Sample Proxy-CE uses exact perturbation/sample labels and should mainly improve replicate retrieval.
- Bio-target Proxy-CE uses target/gene labels and should be framed as an annotation-supervised upper bound for cross-modality matching.

## Current Result Pattern

Key completed results:

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

Interpretation:

- Compound replicate retrieval is measurable but not saturated.
- CRISPR and ORF are harder, making the benchmark more informative than the original compound-only pilot.
- Sample Proxy-CE improves identity retrieval but does not solve cross-modality alignment.
- Bio-target Proxy-CE strongly improves cross-modality because it trains directly on target/gene annotations. This result is valuable but must be presented as supervised upper-bound evidence.

## Remaining Benchmark Cleanup

Priority 1:

- produce split-aware held-out test-query tables for frozen DINOv2-B, sample Proxy-CE, and bio-target Proxy-CE.

Priority 2:

- make figures for dataset composition, frozen baselines, and projection-head comparison.

Priority 3:

- report artifact diagnostics where possible, especially plate and well-position sensitivity.

Success criteria:

- exact 20-plate subset is documented;
- train/val/test plate split is explicit;
- metric definitions are clear;
- cross-modality is included as a main benchmark axis;
- label-free, sample-supervised, and target-supervised settings are separated.
