#!/usr/bin/env python
"""Extract well-level features from downloaded CPJUMP1 images."""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.encoders import build_encoder
from st_benchmark.imaging import discover_sites, find_plate_image_dir, load_site, normalize_channels, resize_chw
from st_benchmark.metadata import build_subset_metadata, load_config, selected_plates


def wait_for_existing_run(output: Path, timeout_seconds: int) -> bool:
    """Return True when an existing completed output can be reused."""
    done_path = output.with_suffix(output.suffix + ".done")
    lock_path = output.with_suffix(output.suffix + ".lock")
    if done_path.exists() and output.exists():
        print(f"output already complete: {output}", flush=True)
        return True

    start = time.time()
    while lock_path.exists():
        if done_path.exists() and output.exists():
            print(f"output completed by another process: {output}", flush=True)
            return True
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for lock: {lock_path}")
        print(f"waiting for existing extraction lock: {lock_path}", flush=True)
        time.sleep(30)
    return False


def create_lock(output: Path) -> Path:
    """Create an extraction lock file for an output path."""
    lock_path = output.with_suffix(output.suffix + ".lock")
    try:
        with lock_path.open("x", encoding="utf-8") as handle:
            handle.write(f"pid={__import__('os').getpid()}\n")
    except FileExistsError:
        raise RuntimeError(f"Output lock already exists: {lock_path}") from None
    return lock_path


def parse_wells(values: list[str] | None) -> set[str] | None:
    """Normalize optional well filters."""
    if not values:
        return None
    return {value.strip().upper() for value in values if value.strip()}


def metadata_wells_by_plate(metadata: pd.DataFrame, wells: set[str] | None) -> dict[str, set[str]]:
    """Return allowed wells per plate from metadata and optional user filter."""
    allowed: dict[str, set[str]] = {}
    for plate, plate_df in metadata.groupby("Metadata_Plate"):
        plate_wells = set(plate_df["Metadata_Well"].astype(str))
        if wells is not None:
            plate_wells &= wells
        allowed[str(plate)] = plate_wells
    return allowed


def extract_plate(
    *,
    encoder,
    plate: str,
    batch: str,
    image_root: Path,
    wells: set[str],
    batch_size: int,
) -> pd.DataFrame:
    """Extract mean-pooled well features for one plate."""
    plate_dir = find_plate_image_dir(image_root, batch, plate)
    sites = discover_sites(plate_dir, wells=wells)
    complete_keys = sorted(key for key, paths in sites.items() if len(paths) >= 5)
    if not complete_keys:
        print(f"{plate}: no complete sites found in {plate_dir}")
        return pd.DataFrame()

    sums: dict[str, np.ndarray] = {}
    counts: dict[str, int] = defaultdict(int)
    pending_images: list[np.ndarray] = []
    pending_wells: list[str] = []

    def flush() -> None:
        if not pending_images:
            return
        features = encoder.encode_sites(pending_images)
        for well, feature in zip(pending_wells, features, strict=True):
            if well not in sums:
                sums[well] = np.zeros_like(feature, dtype=np.float64)
            sums[well] += feature
            counts[well] += 1
        pending_images.clear()
        pending_wells.clear()

    for idx, (well, field) in enumerate(complete_keys, start=1):
        raw = load_site(sites[(well, field)])
        image = normalize_channels(raw)
        if getattr(encoder, "input_size", 0):
            image = resize_chw(image, int(encoder.input_size))
        pending_images.append(image)
        pending_wells.append(well)
        if len(pending_images) >= batch_size:
            flush()
        if idx % max(batch_size * 8, 1) == 0:
            print(f"{plate}: processed {idx}/{len(complete_keys)} sites")
    flush()

    rows = []
    for well in sorted(sums):
        feature = (sums[well] / counts[well]).astype(np.float32)
        row = {"Metadata_Plate": plate, "Metadata_Well": well, "n_sites": counts[well]}
        row.update({f"feature_{idx}": float(value) for idx, value in enumerate(feature)})
        rows.append(row)
    print(f"{plate}: wrote {len(rows)} wells from {sum(counts.values())} sites")
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoder", choices=["intensity", "dinov2"], required=True)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--image-root", default="/data/cpjump1/images")
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--model-name", default=None, help="DINOv2 torch.hub model, e.g. dinov2_vits14 or dinov2_vitb14")
    parser.add_argument("--plates", nargs="*", default=None)
    parser.add_argument("--wells", nargs="*", default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lock-timeout-seconds", type=int, default=86400)
    parser.add_argument("--force", action="store_true", help="Overwrite output even if a .done marker exists")
    args = parser.parse_args()

    output = Path(args.output)
    if not args.force and wait_for_existing_run(output, args.lock_timeout_seconds):
        return
    lock_path = create_lock(output)

    repo_root = Path(args.repo_root)
    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    plates = args.plates or selected_plates(config)
    metadata = metadata[metadata["Metadata_Plate"].isin(plates)].copy()
    wells_filter = parse_wells(args.wells)
    allowed_wells = metadata_wells_by_plate(metadata, wells_filter)

    try:
        encoder = build_encoder(args.encoder, device=args.device, model_name=args.model_name)
        print(f"encoder={args.encoder} model={getattr(encoder, 'name', args.encoder)} dim={encoder.feature_dim}", flush=True)

        all_frames = []
        for plate in plates:
            plate_meta = metadata[metadata["Metadata_Plate"] == plate]
            if plate_meta.empty:
                continue
            batch = str(plate_meta["Metadata_Batch"].iloc[0])
            frame = extract_plate(
                encoder=encoder,
                plate=str(plate),
                batch=batch,
                image_root=Path(args.image_root),
                wells=allowed_wells[str(plate)],
                batch_size=args.batch_size,
            )
            if not frame.empty:
                all_frames.append(frame)

        if not all_frames:
            raise SystemExit("No features extracted")
        features = pd.concat(all_frames, ignore_index=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(output, index=False)
        output.with_suffix(output.suffix + ".done").write_text("ok\n", encoding="utf-8")
        feature_cols = [col for col in features.columns if col.startswith("feature_")]
        print(f"saved {output} rows={len(features)} features={len(feature_cols)}", flush=True)
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
