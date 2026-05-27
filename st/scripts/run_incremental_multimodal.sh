#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-st/configs/subset_multimodal_short_20plate.yaml}"
REPO_ROOT="${REPO_ROOT:-.}"
IMAGE_ROOT="${IMAGE_ROOT:-/workspace/data/cpjump1/images}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-180}"
MIN_TIFFS_PER_PLATE="${MIN_TIFFS_PER_PLATE:-17280}"

FEATURE_ROOT="st/outputs/features"
PLATE_FEATURE_ROOT="${FEATURE_ROOT}/multimodal_short_20plate_by_plate"
METRICS_ROOT="st/outputs/metrics"
REPORT_DIR="st/reports/experiment_tables"

mkdir -p "$FEATURE_ROOT" "$PLATE_FEATURE_ROOT" "$METRICS_ROOT" "$REPORT_DIR" st/outputs/logs

mapfile -t PLATES < <(
  python - <<'PY'
import pandas as pd

manifest = pd.read_csv("st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv")
for plate in manifest["Metadata_Plate"].drop_duplicates():
    print(plate)
PY
)

is_plate_complete() {
  local plate="$1"
  local path="${IMAGE_ROOT}/2020_11_04_CPJUMP1/${plate}/Images"
  local count=0
  if [[ -d "$path" ]]; then
    count=$(find "$path" -maxdepth 1 -type f -name "*.tiff" | wc -l | tr -d ' ')
  fi
  [[ "$count" -ge "$MIN_TIFFS_PER_PLATE" ]]
}

print_download_status() {
  local pending=()
  local complete=0
  local count path plate
  for plate in "${PLATES[@]}"; do
    path="${IMAGE_ROOT}/2020_11_04_CPJUMP1/${plate}/Images"
    count=0
    if [[ -d "$path" ]]; then
      count=$(find "$path" -maxdepth 1 -type f -name "*.tiff" | wc -l | tr -d ' ')
    fi
    if [[ "$count" -ge "$MIN_TIFFS_PER_PLATE" ]]; then
      complete=$((complete + 1))
    else
      pending+=("${plate}:${count}")
    fi
  done
  echo "download status: ${complete}/${#PLATES[@]} complete"
  if [[ "${#pending[@]}" -gt 0 ]]; then
    printf 'pending plates: %s\n' "${pending[*]}"
  fi
}

all_plate_features_done() {
  local prefix="$1"
  local plate output
  for plate in "${PLATES[@]}"; do
    output="${PLATE_FEATURE_ROOT}/${prefix}_${plate}.csv"
    if [[ ! -s "$output" || ! -f "${output}.done" ]]; then
      return 1
    fi
  done
  return 0
}

combine_plate_features() {
  local prefix="$1"
  local output="${FEATURE_ROOT}/${prefix}.csv"

  if [[ -s "$output" && -f "${output}.done" ]]; then
    echo "combined features already complete: $output"
    return 0
  fi

  python - "$prefix" "$output" <<'PY'
import sys
from pathlib import Path

import pandas as pd

prefix = sys.argv[1]
output = Path(sys.argv[2])
manifest = pd.read_csv("st/data/metadata/subset_multimodal_short_20plate_download_manifest.csv")
feature_root = Path("st/outputs/features/multimodal_short_20plate_by_plate")

frames = []
missing = []
for plate in manifest["Metadata_Plate"].drop_duplicates():
    path = feature_root / f"{prefix}_{plate}.csv"
    if not path.exists():
        missing.append(str(path))
    else:
        frames.append(pd.read_csv(path))

if missing:
    raise SystemExit("missing plate feature files: " + ", ".join(missing))

frame = pd.concat(frames, ignore_index=True)
output.parent.mkdir(parents=True, exist_ok=True)
frame.to_csv(output, index=False)
output.with_suffix(output.suffix + ".done").write_text("ok\n", encoding="utf-8")
print(f"combined {len(frames)} plate files -> {output} rows={len(frame)}")
PY
}

evaluate_model() {
  local prefix="$1"
  local feature_path="${FEATURE_ROOT}/${prefix}.csv"
  local transform

  for transform in raw_l2 plate_zscore_l2 negcon_zscore_l2; do
    local out_dir="${METRICS_ROOT}/${prefix}_multimodal_${transform}"
    local summary="${out_dir}/${prefix}_${transform}_summary.csv"
    if [[ -s "$summary" ]]; then
      echo "evaluation already complete: $summary"
      continue
    fi

    python st/scripts/evaluate_multimodal_features.py \
      --features "$feature_path" \
      --config "$CONFIG" \
      --repo-root "$REPO_ROOT" \
      --output-dir "$out_dir" \
      --prefix "${prefix}_${transform}" \
      --input-transform "$transform" \
      2>&1 | tee "st/outputs/logs/eval_${prefix}_multimodal_${transform}.log"
  done
}

summarize_results() {
  python st/scripts/summarize_multimodal_results.py \
    --metrics-root "$METRICS_ROOT" \
    --output-dir "$REPORT_DIR" \
    2>&1 | tee st/outputs/logs/summarize_multimodal_short_20plate.log
}

run_model_incremental() {
  local model_name="$1"
  local batch_size="$2"
  local prefix="$3"
  local plate output

  echo "starting incremental model: ${prefix} (${model_name})"
  while ! all_plate_features_done "$prefix"; do
    local did_work=0
    print_download_status

    for plate in "${PLATES[@]}"; do
      output="${PLATE_FEATURE_ROOT}/${prefix}_${plate}.csv"
      if [[ -s "$output" && -f "${output}.done" ]]; then
        continue
      fi
      if ! is_plate_complete "$plate"; then
        continue
      fi

      echo "extracting ${prefix} ${plate}"
      python st/scripts/extract_dinov2_fast.py \
        --config "$CONFIG" \
        --repo-root "$REPO_ROOT" \
        --image-root "$IMAGE_ROOT" \
        --output "$output" \
        --model-name "$model_name" \
        --batch-size "$batch_size" \
        --num-workers 8 \
        --plates "$plate" \
        2>&1 | tee "st/outputs/logs/extract_${prefix}_${plate}.log"
      did_work=1
    done

    if [[ "$did_work" -eq 0 ]]; then
      sleep "$CHECK_INTERVAL_SECONDS"
    fi
  done

  combine_plate_features "$prefix"
  evaluate_model "$prefix"
}

run_model_incremental dinov2_vits14 64 dinov2_vits14_multimodal_short_20plate
run_model_incremental dinov2_vitb14 48 dinov2_vitb14_multimodal_short_20plate
summarize_results
