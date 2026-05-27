#!/usr/bin/env python
"""Fast DINOv2 feature extraction with parallel TIFF decoding."""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.imaging import discover_sites, find_plate_image_dir
from st_benchmark.metadata import build_subset_metadata, load_config, selected_plates


def wait_or_lock(output: Path, timeout_seconds: int = 86400) -> Path | None:
    """Create a lock for this output, or return None if it is already done."""
    done_path = output.with_suffix(output.suffix + ".done")
    lock_path = output.with_suffix(output.suffix + ".lock")
    if done_path.exists() and output.exists():
        print(f"output already complete: {output}", flush=True)
        return None

    start = time.time()
    while lock_path.exists():
        if done_path.exists() and output.exists():
            print(f"output completed by another process: {output}", flush=True)
            return None
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for lock: {lock_path}")
        print(f"waiting for lock: {lock_path}", flush=True)
        time.sleep(30)

    output.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("x", encoding="utf-8") as handle:
        handle.write(f"pid={os.getpid()}\n")
    return lock_path


def parse_wells(values: list[str] | None) -> set[str] | None:
    """Normalize optional well filters."""
    if not values:
        return None
    return {value.strip().upper() for value in values if value.strip()}


def build_site_index(
    *,
    config: dict,
    repo_root: Path,
    image_root: Path,
    plates: list[str],
    wells_filter: set[str] | None,
) -> list[dict]:
    """Build a flat site-level index for selected plates and wells."""
    metadata = build_subset_metadata(config, repo_root)
    metadata = metadata[metadata["Metadata_Plate"].isin(plates)].copy()
    rows: list[dict] = []

    for plate in plates:
        plate_meta = metadata[metadata["Metadata_Plate"] == plate]
        if plate_meta.empty:
            continue
        batch = str(plate_meta["Metadata_Batch"].iloc[0])
        allowed_wells = set(plate_meta["Metadata_Well"].astype(str))
        if wells_filter is not None:
            allowed_wells &= wells_filter

        plate_dir = find_plate_image_dir(image_root, batch, plate)
        sites = discover_sites(plate_dir, wells=allowed_wells)
        complete_keys = sorted(key for key, paths in sites.items() if len(paths) >= 5)
        for well, field in complete_keys:
            rows.append(
                {
                    "plate": str(plate),
                    "well": str(well),
                    "field": int(field),
                    "paths": [sites[(well, field)][channel] for channel in (1, 2, 3, 4, 5)],
                }
            )
        print(f"{plate}: indexed {len(complete_keys)} complete sites", flush=True)
    return rows


def normalize_channel(channel: np.ndarray, sample_stride: int) -> np.ndarray:
    """Fast percentile normalization using a strided sample for percentile estimates."""
    channel = channel.astype(np.float32, copy=False)
    sample = channel[::sample_stride, ::sample_stride]
    lo, hi = np.percentile(sample, [0.1, 99.9])
    if hi <= lo:
        return np.zeros_like(channel, dtype=np.float32)
    return np.clip((channel - lo) / (hi - lo), 0.0, 1.0)


def resize_group(group: np.ndarray, size: int) -> np.ndarray:
    """Resize a normalized 3xHxW group to 3xSxS."""
    image = (group.transpose(1, 2, 0) * 255.0).clip(0, 255).astype(np.uint8)
    resized = Image.fromarray(image).resize((size, size), Image.BILINEAR)
    return np.asarray(resized, dtype=np.float32).transpose(2, 0, 1) / 255.0


class CellPaintingSiteDataset(Dataset):
    """Site-level Cell Painting dataset returning two DINO RGB groups per site."""

    def __init__(self, sites: list[dict], image_size: int, sample_stride: int):
        self.sites = sites
        self.image_size = image_size
        self.sample_stride = sample_stride

    def __len__(self) -> int:
        return len(self.sites)

    def __getitem__(self, idx: int) -> dict:
        import tifffile

        item = self.sites[idx]
        channels = [normalize_channel(tifffile.imread(path), self.sample_stride) for path in item["paths"]]
        image = np.stack(channels, axis=0)
        group_a = resize_group(image[[0, 1, 4]], self.image_size)
        group_b = resize_group(image[[2, 3, 4]], self.image_size)
        groups = np.stack([group_a, group_b], axis=0).astype(np.float32)
        return {
            "plate": item["plate"],
            "well": item["well"],
            "groups": torch.from_numpy(groups),
        }


def collate_sites(batch: list[dict]) -> dict:
    """Collate site dictionaries while preserving plate/well ids."""
    return {
        "plate": [item["plate"] for item in batch],
        "well": [item["well"] for item in batch],
        "groups": torch.stack([item["groups"] for item in batch], dim=0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_4plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--image-root", default="/workspace/data/cpjump1/images")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-name", default="dinov2_vits14")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=64, help="Number of sites per batch; DINO sees 2x this many RGB images")
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--sample-stride", type=int, default=8)
    parser.add_argument("--plates", nargs="*", default=None)
    parser.add_argument("--wells", nargs="*", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    if args.force:
        output.with_suffix(output.suffix + ".done").unlink(missing_ok=True)
        output.with_suffix(output.suffix + ".lock").unlink(missing_ok=True)
    lock_path = wait_or_lock(output)
    if lock_path is None:
        return

    try:
        repo_root = Path(args.repo_root)
        config = load_config(args.config)
        plates = args.plates or selected_plates(config)
        sites = build_site_index(
            config=config,
            repo_root=repo_root,
            image_root=Path(args.image_root),
            plates=plates,
            wells_filter=parse_wells(args.wells),
        )
        if not sites:
            raise SystemExit("No complete sites found")

        device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
        model = torch.hub.load("facebookresearch/dinov2", args.model_name).to(device)
        model.eval()
        feature_dim = int(model.embed_dim) * 2
        print(
            f"encoder=dinov2 model={args.model_name} sites={len(sites)} feature_dim={feature_dim} "
            f"batch_size={args.batch_size} workers={args.num_workers}",
            flush=True,
        )

        dataset = CellPaintingSiteDataset(sites, image_size=224, sample_stride=args.sample_stride)
        loader = DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=(device.type == "cuda"),
            persistent_workers=args.num_workers > 0,
            collate_fn=collate_sites,
        )
        mean = torch.tensor([0.485, 0.456, 0.406], dtype=torch.float32, device=device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], dtype=torch.float32, device=device).view(1, 3, 1, 1)

        sums: dict[tuple[str, str], np.ndarray] = {}
        counts: dict[tuple[str, str], int] = defaultdict(int)
        processed = 0
        start = time.time()

        with torch.inference_mode():
            for batch_idx, batch in enumerate(loader, start=1):
                groups = batch["groups"]
                n_sites = groups.shape[0]
                pixels = groups.reshape(n_sites * 2, 3, 224, 224).to(device, non_blocking=True)
                pixels = (pixels - mean) / std
                encoded = model(pixels).detach().cpu().numpy().astype(np.float32)
                paired = encoded.reshape(n_sites, 2, -1)
                features = np.concatenate([paired[:, 0, :], paired[:, 1, :]], axis=1)
                norms = np.linalg.norm(features, axis=1, keepdims=True)
                features = features / np.maximum(norms, 1e-12)

                for plate, well, feature in zip(batch["plate"], batch["well"], features, strict=True):
                    key = (plate, well)
                    if key not in sums:
                        sums[key] = np.zeros_like(feature, dtype=np.float64)
                    sums[key] += feature
                    counts[key] += 1

                processed += n_sites
                if batch_idx == 1 or batch_idx % 10 == 0:
                    elapsed = max(time.time() - start, 1e-6)
                    print(
                        f"processed {processed}/{len(sites)} sites "
                        f"({processed / elapsed:.2f} sites/s)",
                        flush=True,
                    )

        rows = []
        for plate, well in sorted(sums):
            feature = (sums[(plate, well)] / counts[(plate, well)]).astype(np.float32)
            row = {"Metadata_Plate": plate, "Metadata_Well": well, "n_sites": counts[(plate, well)]}
            row.update({f"feature_{idx}": float(value) for idx, value in enumerate(feature)})
            rows.append(row)

        frame = pd.DataFrame(rows)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        output.with_suffix(output.suffix + ".done").write_text("ok\n", encoding="utf-8")
        print(f"saved {output} rows={len(frame)} features={feature_dim}", flush=True)
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
