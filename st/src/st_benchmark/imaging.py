"""Image discovery and preprocessing for CPJUMP1 Cell Painting TIFFs."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image


FLUORESCENT_CHANNELS = (1, 2, 3, 4, 5)
TIFF_PATTERN = re.compile(r"r(\d{2})c(\d{2})f(\d{2})p01-ch(\d+)sk1fk1fl1\.tiff$")


def well_from_row_col(row: int, col: int) -> str:
    """Convert 1-based row/column indices to a well id such as A01."""
    return f"{chr(64 + row)}{col:02d}"


def parse_tiff_name(path: str | Path) -> dict[str, int | str] | None:
    """Parse a CPJUMP1 TIFF filename into row, column, field, channel, and well."""
    match = TIFF_PATTERN.match(Path(path).name)
    if match is None:
        return None
    row, col, field, channel = (int(match.group(i)) for i in range(1, 5))
    return {
        "row": row,
        "col": col,
        "field": field,
        "channel": channel,
        "well": well_from_row_col(row, col),
    }


def discover_sites(image_dir: str | Path, wells: set[str] | None = None) -> dict[tuple[str, int], dict[int, Path]]:
    """Return {(well, field): {channel: path}} for fluorescent TIFFs in a plate directory."""
    image_dir = Path(image_dir)
    sites: dict[tuple[str, int], dict[int, Path]] = {}
    for path in image_dir.glob("*.tiff"):
        parsed = parse_tiff_name(path)
        if parsed is None:
            continue
        channel = int(parsed["channel"])
        if channel not in FLUORESCENT_CHANNELS:
            continue
        well = str(parsed["well"])
        if wells is not None and well not in wells:
            continue
        key = (well, int(parsed["field"]))
        sites.setdefault(key, {})[channel] = path
    return sites


def load_site(channel_paths: dict[int, Path], channels: tuple[int, ...] = FLUORESCENT_CHANNELS) -> np.ndarray:
    """Load one multi-channel site as a (C, H, W) uint16 array."""
    import tifffile

    missing = [channel for channel in channels if channel not in channel_paths]
    if missing:
        raise FileNotFoundError(f"Missing channels {missing} in site paths")
    images = [tifffile.imread(channel_paths[channel]) for channel in channels]
    return np.stack(images, axis=0)


def normalize_channels(
    image: np.ndarray,
    lower_percentile: float = 0.1,
    upper_percentile: float = 99.9,
) -> np.ndarray:
    """Percentile-normalize each channel independently to [0, 1]."""
    image = image.astype(np.float32, copy=False)
    output = np.empty_like(image, dtype=np.float32)
    for channel in range(image.shape[0]):
        lo = np.percentile(image[channel], lower_percentile)
        hi = np.percentile(image[channel], upper_percentile)
        if hi <= lo:
            output[channel] = 0.0
        else:
            output[channel] = np.clip((image[channel] - lo) / (hi - lo), 0.0, 1.0)
    return output


def resize_chw(image: np.ndarray, size: int) -> np.ndarray:
    """Resize a (C, H, W) float image to (C, size, size)."""
    resized = np.empty((image.shape[0], size, size), dtype=np.float32)
    for channel in range(image.shape[0]):
        pil_image = Image.fromarray(image[channel])
        resized[channel] = np.asarray(pil_image.resize((size, size), Image.BILINEAR), dtype=np.float32)
    return resized


def find_plate_image_dir(image_root: str | Path, batch: str, plate: str) -> Path:
    """Find the local image directory for a plate in the configured download layout."""
    image_root = Path(image_root)
    candidates = [
        image_root / batch / plate / "Images",
        image_root / batch / plate,
        image_root / plate / "Images",
        image_root / plate,
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    for candidate in image_root.rglob(f"{plate}*"):
        if candidate.is_dir() and candidate.name == "Images":
            return candidate
        images_dir = candidate / "Images"
        if images_dir.is_dir():
            return images_dir
    raise FileNotFoundError(f"Cannot find images for plate {plate} under {image_root}")
