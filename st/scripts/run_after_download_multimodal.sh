#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-st/configs/subset_multimodal_short_20plate.yaml}"
REPO_ROOT="${REPO_ROOT:-.}"
IMAGE_ROOT="${IMAGE_ROOT:-/workspace/data/cpjump1/images}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-300}"

mkdir -p st/outputs/features st/outputs/metrics st/outputs/logs

wait_for_downloads() {
  while true; do
    if python - "$CONFIG" "$IMAGE_ROOT" <<'PY'
import sys
from pathlib import Path

import pandas as pd

config_path = Path(sys.argv[1])
image_root = Path(sys.argv[2])

plates = pd.read_csv("st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv")[
    "Metadata_Plate"
].tolist()
incomplete = []
for plate in plates:
    path = image_root / "2020_11_04_CPJUMP1" / plate / "Images"
    count = sum(1 for _ in path.glob("*.tiff")) if path.exists() else 0
    if count < 17280:
        incomplete.append((plate, count))

if incomplete:
    print("waiting for plates:", ", ".join(f"{plate}:{count}" for plate, count in incomplete), flush=True)
    raise SystemExit(1)

print(f"all {len(plates)} plates are complete", flush=True)
PY
    then
      break
    fi
    sleep "$CHECK_INTERVAL_SECONDS"
  done
}

run_model() {
  local model_name="$1"
  local batch_size="$2"
  local prefix="$3"
  local feature_path="st/outputs/features/${prefix}.csv"

  python st/scripts/extract_dinov2_fast.py \
    --config "$CONFIG" \
    --repo-root "$REPO_ROOT" \
    --image-root "$IMAGE_ROOT" \
    --output "$feature_path" \
    --model-name "$model_name" \
    --batch-size "$batch_size" \
    --num-workers 8 \
    2>&1 | tee "st/outputs/logs/extract_${prefix}.log"

  for transform in raw_l2 plate_zscore_l2 negcon_zscore_l2; do
    python st/scripts/evaluate_multimodal_features.py \
      --features "$feature_path" \
      --config "$CONFIG" \
      --repo-root "$REPO_ROOT" \
      --output-dir "st/outputs/metrics/${prefix}_multimodal_${transform}" \
      --prefix "${prefix}_${transform}" \
      --input-transform "$transform" \
      2>&1 | tee "st/outputs/logs/eval_${prefix}_multimodal_${transform}.log"
  done
}

wait_for_downloads
run_model dinov2_vits14 64 dinov2_vits14_multimodal_short_20plate
run_model dinov2_vitb14 48 dinov2_vitb14_multimodal_short_20plate
