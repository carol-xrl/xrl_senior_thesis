"""Load and preprocess Cell Painting TIFF images from S3 or local disk.

Image specs (CPJUMP1):
  - 1080x1080 uint16
  - 8 channels per site: ch1-ch5 fluorescent, ch6-ch8 brightfield
  - Naming: rXXcXXfXXp01-chXXsk1fk1fl1.tiff
  - r=row(1-16), c=col(1-24), f=field/site(1-16), ch=channel(1-8)
"""

import os
import re
import numpy as np
from pathlib import Path

try:
    import tifffile
except ImportError:
    tifffile = None

# Channel names for the 5 fluorescent channels
CHANNEL_NAMES = {
    1: "AGP",       # Alexa 647 (actin, golgi, plasma membrane)
    2: "Mito",      # Alexa 568 (mitochondria)
    3: "RNA",       # Alexa 488 long (RNA)
    4: "ER",        # Alexa 488 (endoplasmic reticulum)
    5: "DNA",       # Hoechst 33342 (nucleus/DNA)
}

FLUORESCENT_CHANNELS = [1, 2, 3, 4, 5]

# Regex to parse TIFF filenames
TIFF_PATTERN = re.compile(
    r"r(\d{2})c(\d{2})f(\d{2})p01-ch(\d+)sk1fk1fl1\.tiff"
)


def well_from_row_col(row: int, col: int) -> str:
    """Convert (row, col) to well name like 'A01', 'P24'."""
    return f"{chr(64 + row)}{col:02d}"


def parse_tiff_filename(filename: str) -> dict:
    """Parse rXXcXXfXXp01-chXXsk1fk1fl1.tiff into components."""
    m = TIFF_PATTERN.match(filename)
    if not m:
        return None
    row, col, field, channel = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return {
        "row": row,
        "col": col,
        "field": field,
        "channel": channel,
        "well": well_from_row_col(row, col),
    }


def discover_sites(image_dir: str) -> dict:
    """Discover all (well, field) combinations in an image directory.

    Returns:
        dict: {(well, field): {channel: filepath, ...}, ...}
    """
    sites = {}
    for fname in os.listdir(image_dir):
        parsed = parse_tiff_filename(fname)
        if parsed is None:
            continue
        if parsed["channel"] not in FLUORESCENT_CHANNELS:
            continue  # skip brightfield
        key = (parsed["well"], parsed["field"])
        if key not in sites:
            sites[key] = {}
        sites[key][parsed["channel"]] = os.path.join(image_dir, fname)
    return sites


def load_site(
    channel_paths: dict,
    channels: list = None,
) -> np.ndarray:
    """Load a multi-channel site image.

    Args:
        channel_paths: {channel_num: filepath} mapping.
        channels: Which channels to load (default: all 5 fluorescent).

    Returns:
        np.ndarray of shape (C, H, W), uint16.
    """
    if tifffile is None:
        raise ImportError("tifffile is required. Install with: pip install tifffile")

    if channels is None:
        channels = FLUORESCENT_CHANNELS

    imgs = []
    for ch in channels:
        if ch not in channel_paths:
            raise FileNotFoundError(f"Channel {ch} not found in paths: {channel_paths}")
        img = tifffile.imread(channel_paths[ch])  # (H, W), uint16
        imgs.append(img)

    return np.stack(imgs, axis=0)  # (C, H, W)


def normalize_channels(
    img: np.ndarray,
    lower_percentile: float = 0.1,
    upper_percentile: float = 99.9,
) -> np.ndarray:
    """Normalize each channel independently to [0, 1] using percentile clipping.

    Args:
        img: (C, H, W) uint16 array.
        lower_percentile: Lower percentile for clipping.
        upper_percentile: Upper percentile for clipping.

    Returns:
        (C, H, W) float32 array in [0, 1].
    """
    img = img.astype(np.float32)
    for c in range(img.shape[0]):
        lo = np.percentile(img[c], lower_percentile)
        hi = np.percentile(img[c], upper_percentile)
        if hi - lo > 0:
            img[c] = np.clip((img[c] - lo) / (hi - lo), 0, 1)
        else:
            img[c] = 0
    return img


def resize_image(img: np.ndarray, size: int) -> np.ndarray:
    """Resize (C, H, W) image to (C, size, size) using bilinear interpolation.

    Uses numpy-only implementation to avoid torch dependency at this level.
    """
    from PIL import Image

    c, h, w = img.shape
    resized = np.empty((c, size, size), dtype=img.dtype)
    for i in range(c):
        pil_img = Image.fromarray(img[i])
        pil_img = pil_img.resize((size, size), Image.BILINEAR)
        resized[i] = np.array(pil_img)
    return resized


def channels_to_rgb_groups(img: np.ndarray) -> list:
    """Convert 5-channel image to two pseudo-RGB groups for 3-channel encoders.

    Group A: ch1(AGP) + ch2(Mito) + ch5(DNA)  → morphology
    Group B: ch3(RNA) + ch4(ER) + ch5(DNA)    → staining

    Args:
        img: (5, H, W) normalized float32 array.

    Returns:
        List of two (3, H, W) arrays.
    """
    group_a = img[[0, 1, 4]]  # ch1, ch2, ch5
    group_b = img[[2, 3, 4]]  # ch3, ch4, ch5
    return [group_a, group_b]
