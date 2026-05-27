# Paper Outline

## Working Title

A compact multimodal CPJUMP1 benchmark for Cell Painting representation learning

## Core Thesis

Cell Painting images contain perturbation-level biological signal, but generic image encoders do not automatically align compound, ORF, and CRISPR perturbations by biological mechanism. A compact 20-plate CPJUMP1 benchmark can expose three levels of representation quality:

1. whether frozen visual features retrieve exact perturbation replicates;
2. whether lightweight supervised adaptation improves identity-level retrieval;
3. whether explicit biological target/gene supervision is needed for cross-modality alignment.

The paper should not claim to train a full biological foundation model. The defensible claim is:

> With a fixed 20-plate multimodal CPJUMP1 subset, frozen DINOv2 representations recover some perturbation structure, sample-supervised heads improve replicate retrieval, and target/gene-supervised heads reveal a strong upper bound for compound-to-gene morphological alignment.

## Contributions

1. A reproducible 20-plate CPJUMP1 benchmark spanning compound, ORF, and CRISPR perturbations in A549 and U2OS.
2. A metric suite covering replicate retrieval, negative-control challenge, within-modality matching, and cross-modality matching.
3. A low-cost evaluation of DINOv2-S/14 and DINOv2-B/14 frozen features under normalization variants.
4. A projection-head study separating perturbation identity supervision from biological target/gene supervision.
5. A practical compute and storage workflow using RunPod while retaining raw images on the server.

## 1. Introduction

High-content Cell Painting assays measure cellular morphology under many chemical and genetic perturbations. These images are promising for biological representation learning because morphology can reflect perturbation identity, pathway activity, and cellular state. However, learning representations that recover biology rather than plate effects, staining variation, or acquisition artifacts remains difficult.

Generic self-supervised vision models such as DINOv2 are powerful, but they are not trained to align compounds with genes or to respect high-content screening experimental structure. Conversely, full-scale domain-specific foundation model training is expensive. This thesis studies a practical middle ground: fixed public data, frozen foundation features, feature normalization, and lightweight projection heads.

The introduction should motivate four questions:

1. Do frozen visual features retrieve repeated perturbations across plates?
2. Are compound, ORF, and CRISPR perturbations equally easy?
3. Does supervised perturbation identity training improve morphology representations?
4. What kind of supervision is needed for compound-to-gene cross-modality matching?

## 2. Related Work

Keep this concise and targeted.

- Cell Painting and high-content screening morphology profiles.
- The JUMP-Cell Painting / CPJUMP1 dataset.
- Classical morphology features and CellProfiler.
- Generic vision foundation models, especially self-supervised ViTs such as DINOv2.
- Biological image representation learning and microscopy foundation models.
- Biological benchmark metrics: replicate retrieval, mean average precision, control separation, target/gene matching.

Position the work as a benchmark and adaptation study, not as a new large model.

## 3. Benchmark

### 3.1 Dataset

Use CPJUMP1 batch `2020_11_04_CPJUMP1`.

Main subset:

| Field | Value |
| --- | --- |
| Plates | 20 |
| Cell types | A549, U2OS |
| Modalities | compound, ORF, CRISPR |
| Compound time | 24h |
| ORF time | 48h |
| CRISPR time | 96h |
| Density | 100 |
| Antibiotics | absent |
| Channels | AGP, Mito, RNA, ER, DNA |
| Total well rows | 7632 |

### 3.2 Plate Split

The split is plate-level.

Train plates:

- A549 compound: `BR00116991`, `BR00116992`
- U2OS compound: `BR00116995`, `BR00117024`
- A549 ORF: `BR00117020`
- U2OS ORF: `BR00117022`
- A549 CRISPR: `BR00118041`, `BR00118042`
- U2OS CRISPR: `BR00118045`, `BR00118046`

Validation plates:

- A549 compound: `BR00116993`
- U2OS compound: `BR00117025`
- A549 CRISPR: `BR00118043`
- U2OS CRISPR: `BR00118047`

Test plates:

- A549 compound: `BR00116994`
- U2OS compound: `BR00117026`
- A549 ORF: `BR00117021`
- U2OS ORF: `BR00117023`
- A549 CRISPR: `BR00118044`
- U2OS CRISPR: `BR00118048`

Use this language carefully:

- Frozen feature extraction sees all images but no labels.
- Projection heads train only on train plates.
- Validation plates select checkpoints.
- Test plates are reserved for final split-aware reporting.
- Current condition-level 20-plate tables aggregate all queries; final thesis should include explicit test-query tables.

### 3.3 Data Units

Raw image:

- one TIFF channel for one site.

Site:

- five fluorescent channels for one field of view.

Well:

- mean aggregation of site-level encoder features.

Perturbation:

- used for labels and retrieval positives, but primary metrics are computed at well level.

### 3.4 Metrics

Replicate retrieval:

- exact perturbation identity retrieval across plates;
- metric: mean average precision.

Negative-control challenge:

- treatment wells should retrieve true replicates over negative controls;
- metric: mean average precision.

Within-modality matching:

- compound target matching;
- CRISPR gene/sister-guide matching;
- ORF currently has no robust within-modality positive definition in this subset.

Cross-modality matching:

- compound -> CRISPR and compound -> ORF;
- within the same cell line;
- positives are shared compound target genes and perturbation genes.

### 3.5 Why This Benchmark Is Reasonable

Biological motivation:

- Compound perturbations test chemical response morphology.
- ORF perturbations test gene overexpression morphology.
- CRISPR perturbations test gene knockout morphology.
- A549 and U2OS test whether representations generalize across cell context.
- Cross-modality matching asks whether different perturbation mechanisms that touch the same gene/target produce aligned morphology.

Engineering motivation:

- 20 plates fit within a 1TB RunPod volume with fluorescent channels only.
- The benchmark can be run in a few days on one L40S.
- The subset is much richer than an 8-plate compound-only benchmark without becoming full-dataset scale.

## 4. Methods

### 4.1 Preprocessing

- Download only fluorescent channels 1-5.
- Keep all raw images on RunPod.
- Percentile-normalize each channel.
- Resize to 224 x 224.
- Form two pseudo-RGB groups:
  - AGP, Mito, DNA
  - RNA, ER, DNA
- Encode both groups with DINOv2 and concatenate embeddings.
- Average site embeddings into well features.

### 4.2 Frozen Encoders

Primary frozen baselines:

- DINOv2-S/14
- DINOv2-B/14
- DINOv2-L/14 as a smaller-scope backbone scaling reference if compute permits

Normalization variants:

- `raw_l2`
- `global_zscore_l2`
- `plate_center_l2`
- `plate_zscore_l2`
- `negcon_center_l2`
- `negcon_zscore_l2`

Write this section as post-hoc feature normalization / batch correction. These transforms are applied after frozen feature extraction and do not train model parameters.

The central biological argument:

- plate correction tests whether acquisition/batch effects can be removed without destroying perturbation signal;
- negative-control correction is especially defensible because negative controls estimate plate-specific background morphology;
- normalization should not be confused with supervised representation learning.

### 4.3 Projection Heads

Use frozen well-level features and train a small MLP projection head.

Projection-head pipeline:

`DINOv2 frozen features -> train projection head on train plates -> evaluate embedding on val/test plates`

Backbone policy:

- do not fine-tune DINOv2;
- train only the projection head;
- use train plates for optimization, validation plates for checkpoint selection, and test plates for final reporting.

Loss ablation:

- supervised contrastive loss;
- triplet margin loss;
- proxy / prototype classification loss;
- hard-negative supervised contrastive loss.

Sample Proxy-CE:

- label: exact `Metadata_broad_sample`;
- objective: improve perturbation identity / replicate retrieval;
- interpretation: identity-supervised adaptation.

Bio-target Proxy-CE:

- compound label: compound target gene;
- ORF/CRISPR label: perturbation gene;
- objective: align perturbations by biological target/gene;
- interpretation: annotation-supervised upper bound for cross-modality matching.

Important framing:

- Sample Proxy-CE and bio-target Proxy-CE answer different questions.
- Bio-target Proxy-CE should not be presented as a label-free model.
- Its value is to show that cross-modality alignment is possible when target/gene labels are made explicit.

### 4.4 Final Experiment Matrix

The final experiment design should avoid a full encoder x loss x normalization grid. The main text should use this compact matrix:

| Group | Encoder | Training | Trick |
| --- | --- | --- | --- |
| baseline | DINOv2-S/B/L | no | raw |
| frozen + trick | DINOv2-S/B | no | best normalization |
| loss ablation | DINOv2-S | yes | raw or standard L2 |
| trained + trick | best trained head | yes | best normalization |

For trained models:

- input to the projection head should be raw L2 or train-fitted global z-score;
- output embeddings should be evaluated with raw, plate-zscore, and negcon-zscore;
- `trained + negcon_zscore` can be emphasized if it is best, because it uses only each plate's negative controls rather than test treatment labels.

## 5. Experiments

### 5.1 Dataset Summary

Report:

- 20 plates;
- 7632 well-level rows;
- 6400 treatment wells;
- 1232 negative controls;
- 817 unique perturbation IDs overall;
- 306 compound IDs per cell line;
- 305 CRISPR IDs per cell line;
- 160 ORF IDs per cell line.

### 5.2 Frozen Feature Baselines

Main table:

- rows: DINOv2-S/B/L raw baselines plus DINOv2-S/B normalization variants;
- columns: replicate retrieval, negative-control challenge, within-modality matching, cross-modality matching;
- report separately by cell line and modality.

The normalization ablation should be described as frozen + trick, not training.

Key completed results:

- DINOv2-B + plate z-score:
  - A549 compound replicate AP: 0.3111
  - U2OS compound replicate AP: 0.2151
  - A549 compound -> CRISPR AP: 0.0347
  - A549 compound -> ORF AP: 0.0357
  - U2OS compound -> CRISPR AP: 0.0319
  - U2OS compound -> ORF AP: 0.0428

### 5.3 Projection-Head Adaptation

Compare:

| Method | Main expected effect |
| --- | --- |
| Frozen DINOv2-B + plate z-score | label-free baseline |
| Sample Proxy-CE | improves exact perturbation retrieval |
| Bio-target Proxy-CE | upper bound for cross-modality alignment |

Loss ablation table:

| Loss | Training label | Purpose |
| --- | --- | --- |
| SupCon | perturbation/sample ID | cluster same perturbation wells |
| Triplet margin | perturbation/sample ID | enforce positive closer than negative |
| Proxy/prototype | perturbation/sample ID or bio-target | learn class prototypes efficiently |
| Hard-negative SupCon | perturbation/sample ID | stress confusing perturbations and controls |

Training plus trick table:

- best loss without post-hoc output correction;
- best loss + plate-zscore output embedding;
- best loss + negcon-zscore output embedding.

Completed key results:

| Condition | Metric | Frozen B + plate z-score | Sample Proxy-CE | Bio-target Proxy-CE |
| --- | --- | ---: | ---: | ---: |
| A549 compound | replicate AP | 0.3111 | 0.4650 | 0.3987 |
| U2OS compound | replicate AP | 0.2151 | 0.4195 | 0.3340 |
| A549 CRISPR | replicate AP | 0.0447 | 0.2126 | 0.1691 |
| U2OS CRISPR | replicate AP | 0.0645 | 0.2468 | 0.1886 |
| A549 compound -> CRISPR | cross-modality AP | 0.0347 | 0.0311 | 0.8256 |
| A549 compound -> ORF | cross-modality AP | 0.0357 | 0.0324 | 0.8335 |
| U2OS compound -> CRISPR | cross-modality AP | 0.0319 | 0.0290 | 0.8067 |
| U2OS compound -> ORF | cross-modality AP | 0.0428 | 0.0279 | 0.8312 |

Interpretation:

- Sample identity supervision improves replicate retrieval but not cross-modality.
- Biological target/gene supervision strongly improves cross-modality.
- This supports the thesis that cross-modality alignment is not simply solved by better perturbation identity clustering.

### 5.4 Split-Aware Evaluation

This should be the next methodological cleanup before final writing.

Need to report:

- validation AP used for checkpoint selection;
- test-query AP on held-out test plates;
- condition-level all-query AP as a secondary descriptive table.

Purpose:

- avoid overclaiming from all-query aggregate tables;
- make training/test separation explicit;
- make the projection-head experiments easier to defend.

## 6. Figures And Tables

Figure 1: Benchmark schematic.

- raw images -> pseudo-RGB groups -> DINOv2 encoder -> well-level features -> metric suite.

Figure 2: Dataset composition.

- plates by split, cell line, modality, and time.

Figure 3: Frozen baseline result summary.

- DINOv2-S/B and normalization variants.

Figure 4: Projection-head comparison.

- frozen B, sample Proxy-CE, bio-target Proxy-CE.
- separate panels for replicate retrieval and cross-modality AP.

Figure 5: Interpretation schematic.

- sample labels cluster exact perturbations;
- target/gene labels align compound with gene perturbations.

Table 1: 20-plate subset definition.

Table 2: frozen baseline metrics.

Table 3: projection-head metrics.

Table 4: compute/storage summary.

## 7. Discussion

Main points:

- Frozen generic vision features are useful but incomplete for biological matching.
- Compound perturbations are easier than genetic perturbations.
- Cross-modality matching is difficult under frozen features and sample-supervised heads.
- Target/gene supervision provides a strong upper bound, suggesting that explicit biological annotations are valuable.
- The benchmark is compact enough for rapid iteration while still reflecting multimodal biological structure.

Limitations:

- 20 plates are still a subset of CPJUMP1.
- Time differs by modality: compound 24h, ORF 48h, CRISPR 96h.
- Bio-target Proxy-CE uses labels directly related to cross-modality evaluation, so it must be framed as an upper bound.
- Final reporting should include split-aware test metrics.

## 8. Conclusion

This thesis builds a compact multimodal CPJUMP1 benchmark and shows that:

1. frozen DINOv2 features recover meaningful perturbation structure;
2. sample-level supervision improves replicate retrieval;
3. target/gene supervision is needed to strongly align compound and genetic perturbation morphology;
4. a 20-plate benchmark can support a credible low-cost study of biological representation learning.

## Draft Acceptance Checklist

The paper draft should include:

- fixed 20-plate subset and plate-level split;
- metric definitions;
- frozen DINOv2-S/B baseline table;
- projection-head table;
- split-aware test-query table;
- storage and compute details;
- clear distinction between label-free baselines, sample-supervised heads, and target-supervised upper bounds.
