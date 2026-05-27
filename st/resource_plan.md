# RunPod Resource Plan

## Recommendation

Best default choice:

> Rent one strong 48GB GPU pod: L40S 48GB or RTX 6000 Ada 48GB.

Recommended pod shape:

| Resource | Recommendation |
| --- | --- |
| GPU | 1x L40S 48GB or 1x RTX 6000 Ada 48GB |
| vCPU | 16+ if available |
| RAM | 64GB minimum, 96GB+ preferred |
| Disk | 700GB-1TB NVMe/local volume |
| Image | PyTorch + CUDA Ubuntu template |
| Runtime | 36-60 hours |

Why this is the best first purchase:

1. 48GB VRAM is enough for frozen DINOv2/DINOv3/OpenPhenom feature extraction and projection-head training.
2. It avoids many 24GB OOM/batch-size problems from RTX 4090.
3. It is far cheaper than H100 and usually enough for our 4-plate subset.
4. One GPU keeps the pipeline simpler: download, decode, feature extraction, training, and logs are easier to manage.

## Why Not Start With Multi-GPU

Multi-GPU sounds attractive, but for this project it is not automatically more efficient.

Reasons:

1. Our first bottleneck is data and pipeline stability, not distributed training.
2. TIFF loading and decoding can bottleneck CPU/disk IO.
3. Frozen feature extraction can be parallelized, but only after the preprocessing code is stable.
4. Multi-GPU adds scheduling complexity: per-GPU jobs, CUDA device assignment, disk contention, and failure recovery.
5. We are not training a large model that needs data parallelism.

Therefore, the first pod should be a strong single-GPU pod. Use tmux to run multiple sessions, but do not run two GPU-heavy jobs at the same time on one GPU.

## When Multi-GPU Makes Sense

Use 2 GPUs only if:

- The price is close to 2x single-GPU but still within budget.
- Disk is NVMe and large enough.
- vCPU/RAM are high enough to feed both GPUs.
- We already passed the tiny pilot and full download.
- We want to run two frozen encoders in parallel.

Best 2-GPU option:

> 2x RTX 4090 or 2x RTX 6000 Ada, if available cheaply.

Use strategy:

```bash
CUDA_VISIBLE_DEVICES=0 python st/scripts/extract_features.py --encoder dinov2 ...
CUDA_VISIBLE_DEVICES=1 python st/scripts/extract_features.py --encoder dinov3 ...
```

But this requires careful IO monitoring:

```bash
nvidia-smi
iostat -xm 5
htop
df -h
```

If disk read is saturated, two GPUs will not help.

## GPU Ranking

### Tier A: Best Practical Choice

L40S 48GB or RTX 6000 Ada 48GB.

Use when:

- We want stable 2.5-day completion.
- We want to run DINOv2/DINOv3/OpenPhenom with less OOM risk.
- We want room for projection-head contrastive training.

### Tier B: Fast And Comfortable But More Expensive

A100 80GB.

Use when:

- L40S/RTX 6000 Ada availability is bad.
- We want fewer memory constraints.
- Price is still below budget for 36-48 hours.

Not necessary by default.

### Tier C: Budget Option

RTX 4090 24GB.

Use when:

- We need the cheapest option.
- We are okay reducing batch size and maybe skipping heavier baselines.

Risk:

- More OOM tuning.
- Less comfortable for DINOv3/OpenPhenom and contrastive training.

### Tier D: Avoid For This Project

H100/H200 multi-GPU.

Reason:

- Too expensive for the marginal benefit.
- Our task is not large-scale distributed training.

## Recommended Purchase Decision

Buy in this order:

1. If available: 1x L40S 48GB with 700GB-1TB disk.
2. Else: 1x RTX 6000 Ada 48GB with 700GB-1TB disk.
3. Else: 1x A100 80GB if the 48-hour cost is acceptable.
4. Else: 1x RTX 4090 24GB and downgrade batch sizes.

Do not start with 2 GPUs unless the price is clearly good and the pod has strong CPU/disk.

## How To Use tmux Efficiently On A Single GPU

Use separate sessions, but only one GPU-heavy job at a time:

```text
st_download       CPU/network heavy
st_extract        GPU heavy
st_eval           CPU light
st_train          GPU heavy
st_monitor        monitoring
```

Allowed in parallel:

- Download + metric evaluation.
- Download + plotting.
- Feature extraction + CPU plotting if disk is not saturated.

Avoid in parallel:

- DINOv2 extraction + DINOv3 extraction on one GPU.
- Feature extraction + training on one GPU.
- Two jobs reading all TIFFs at the same time.

## Expected Run Order

1. Start pod.
2. Pull repo and install environment.
3. Resolve S3 manifest.
4. Tiny pilot download: `A01 A02`.
5. Pilot feature extraction.
6. Full 4-plate fluorescent download.
7. Frozen baseline extraction:
   - DINOv2.
   - DINOv3.
   - OpenPhenom or fallback.
8. Metrics after every baseline.
9. Projection-head training on the best backbone.
10. Aggregation and normalization tricks.

## Cost Guardrail

Stop conditions:

- If setup takes more than 6 hours, downgrade model list.
- If full image download is too slow, switch to 2-plate pilot.
- If OpenPhenom setup takes more than 2 hours, replace it with ResNet50.
- If feature extraction is IO-bound, do not rent more GPUs; optimize image cache/subsampling.

