#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(pwd)}"
IMAGE_ROOT="${IMAGE_ROOT:-/workspace/data/cpjump1/images}"
DOWNLOAD_SESSION="${DOWNLOAD_SESSION:-st_download_full}"
EXPECTED_FILES="${EXPECTED_FILES:-69000}"
DINO_MODEL="${DINO_MODEL:-dinov2_vits14}"
DINO_BATCH_SIZE="${DINO_BATCH_SIZE:-32}"

cd "$REPO_ROOT"
mkdir -p \
  st/outputs/features \
  st/outputs/logs \
  st/outputs/metrics/intensity_full \
  st/outputs/metrics/dinov2_vits14_full

while tmux has-session -t "$DOWNLOAD_SESSION" 2>/dev/null; do
  date
  echo "waiting_for_${DOWNLOAD_SESSION}"
  sleep 60
done

files="$(find "$IMAGE_ROOT" -type f | wc -l | tr -d ' ')"
echo "downloaded_files=${files}" | tee st/outputs/logs/st_extract_full.log
if [ "$files" -lt "$EXPECTED_FILES" ]; then
  echo "DOWNLOAD_INCOMPLETE expected_at_least=${EXPECTED_FILES}" | tee -a st/outputs/logs/st_extract_full.log
  exit 1
fi

python st/scripts/extract_features.py \
  --encoder intensity \
  --repo-root . \
  --image-root "$IMAGE_ROOT" \
  --output st/outputs/features/intensity_full.csv \
  2>&1 | tee st/outputs/logs/intensity_full_extract.log

python st/scripts/evaluate_features.py \
  --features st/outputs/features/intensity_full.csv \
  --repo-root . \
  --output-dir st/outputs/metrics/intensity_full \
  --prefix intensity_full \
  2>&1 | tee st/outputs/logs/intensity_full_eval.log

python st/scripts/extract_features.py \
  --encoder dinov2 \
  --model-name "$DINO_MODEL" \
  --device cuda \
  --batch-size "$DINO_BATCH_SIZE" \
  --repo-root . \
  --image-root "$IMAGE_ROOT" \
  --output st/outputs/features/dinov2_vits14_full.csv \
  2>&1 | tee st/outputs/logs/dinov2_vits14_full_extract.log

python st/scripts/evaluate_features.py \
  --features st/outputs/features/dinov2_vits14_full.csv \
  --repo-root . \
  --output-dir st/outputs/metrics/dinov2_vits14_full \
  --prefix dinov2_vits14_full \
  2>&1 | tee st/outputs/logs/dinov2_vits14_full_eval.log

cat st/outputs/metrics/intensity_full/intensity_full_summary.csv
cat st/outputs/metrics/dinov2_vits14_full/dinov2_vits14_full_summary.csv
