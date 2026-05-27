# Smoke Benchmark Report

## Purpose

This smoke test validates the compact benchmark scaffold before downloading large CPJUMP1 images or renting a GPU server.

It uses real CPJUMP1 metadata and synthetic features. Therefore, the numeric metric values are only sanity checks. They are not biological results.

## Subset

| Field | Value |
| --- | --- |
| Batch | `2020_11_04_CPJUMP1` |
| Modality | compound |
| Cell type | U2OS |
| Time | 48h |
| Plates | `BR00117010`, `BR00117011`, `BR00117012`, `BR00117013` |

Metadata summary:

| Item | Count |
| --- | ---: |
| Wells | 1536 |
| Plates | 4 |
| Treatment wells | 1280 |
| Negative-control wells | 256 |
| Unique broad samples | 307 |
| Annotated treatment wells | 1280 |

## Metrics Implemented

The current smoke scaffold implements the common benchmark metrics we need first:

1. Replicate retrieval: same compound across different plates.
2. Negative-control challenge: same-compound replicates ranked against DMSO/negative controls.
3. Compound target matching: different compounds with overlapping target annotations.
4. Artifact sensitivity: same-plate, same-well, negcon same-well, and same-well confounding diagnostics.

These correspond to the practical subset version of the original CPJUMP1 benchmark ideas: replicability, matching, and negative-control challenge.

## Smoke Results

Synthetic features intentionally contain compound signal, weaker target signal, plate signal, well-position signal, and noise.

| Metric | Mean AP | Median AP | Queries | Groups |
| --- | ---: | ---: | ---: | ---: |
| Replicate retrieval | 0.980 | 1.000 | 1280 | 306 |
| Negcon challenge | 0.996 | 1.000 | 1280 | 306 |
| Target retrieval | 0.107 | 0.048 | 302 | 302 |

Interpretation:

- Replicate and negcon metrics are high because the synthetic generator includes strong compound signal.
- Target retrieval is lower because target signal is intentionally weaker and target-list matching is noisier.
- The smoke test validates metric plumbing rather than model quality.

## Key Caveat Found

The artifact diagnostic found:

| Diagnostic | Value |
| --- | ---: |
| Same-well same-compound fraction | 1.000 |
| Negcon same-well artifact score | 0.507 |
| Same-compound biology score | 0.564 |

This means the 4 selected compound plates reuse the same plate map: a same-compound cross-plate replicate is also a same-well-position pair. Replicate retrieval is still a standard and useful metric, but it can be inflated by well-position artifacts.

For the paper, we must report this confounding explicitly. Target matching and negative-control challenge should be reported alongside replicate retrieval.

## Next Implementation Step

Connect this scaffold to real features:

1. Add image download manifest generation for the selected plates.
2. Add encoder feature extraction into the same feature CSV/parquet schema.
3. Add real-feature evaluation script that reuses the smoke metrics.
4. Run a tiny remote smoke test on the GPU server before launching full plate jobs.

