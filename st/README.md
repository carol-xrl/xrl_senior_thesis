# ST CPJUMP1 Subset Benchmark

This folder contains the active code and planning artifacts for the compact CPJUMP1 subset benchmark.

The current benchmark target is the 4-plate U2OS 48h compound subset:

- `BR00117010`
- `BR00117011`
- `BR00117012`
- `BR00117013`

All new code for this project should live under `st/`.

## Local Smoke Test

The Mac should only run lightweight checks. Do not download full CPJUMP1 image plates locally.

Build subset metadata:

```bash
python st/scripts/make_subset_metadata.py \
  --config st/configs/subset_u2os_compound_4plate.yaml \
  --repo-root .
```

Run smoke metrics with synthetic features:

```bash
python st/scripts/run_smoke_metrics.py \
  --config st/configs/subset_u2os_compound_4plate.yaml \
  --repo-root .
```

The smoke test validates:

- selected plate filtering;
- plate split assignment;
- well-level metadata construction;
- replicate retrieval metric;
- negative-control challenge metric;
- target retrieval metric;
- artifact sensitivity and same-well confounding diagnostics.

The current metric set is intentionally close to the cleaned original benchmark in `../cpjump1_benchmark`: compact replicability, negative-control challenge, and compound/target matching are implemented first. Cross-modality matching is a stretch goal because the primary 4-plate subset is compound-only.

Generated outputs are written under `st/outputs/` and ignored by git.

## Server Pilot Flow

After renting a GPU server and pulling branch `st`, first resolve the S3 image locations and create download commands:

```bash
python st/scripts/prepare_download_manifest.py \
  --config st/configs/subset_u2os_compound_4plate.yaml \
  --repo-root . \
  --image-root /workspace/data/cpjump1/images \
  --resolve-s3 \
  --wells A01 A02 \
  --dryrun
```

Remove `--dryrun` for the tiny pilot download. Remove `--wells A01 A02` for the full fluorescent-channel subset download.

On the current RunPod pod, use `/workspace/data/cpjump1/images` for full downloads. The `/data` path is only a small container overlay and is not large enough for full plates.

After an encoder writes a feature table with columns `Metadata_Plate`, `Metadata_Well`, and `feature_*`, evaluate it:

```bash
python st/scripts/evaluate_features.py \
  --features st/outputs/features/example_encoder.csv \
  --config st/configs/subset_u2os_compound_4plate.yaml \
  --repo-root . \
  --output-dir st/outputs/metrics/example_encoder \
  --prefix example_encoder
```

Plot the summary metrics:

```bash
python st/scripts/plot_metric_summary.py \
  --summary st/outputs/metrics/example_encoder/example_encoder_summary.csv \
  --artifact st/outputs/metrics/example_encoder/example_encoder_artifact_sensitivity.csv \
  --output-dir st/outputs/figures/example_encoder \
  --prefix example_encoder
```

## Remote Experiment Rule

The Mac owns code and reports. The GPU server owns raw images, large features, checkpoints, and long-running compute.

Use git for code synchronization and `rsync` or `scp` for selected results. See `remote_execution_plan.md`.
