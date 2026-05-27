"""Feature encoders used by the compact ST benchmark."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def l2_normalize(features: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """L2-normalize a 2D feature array row-wise."""
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    return features / np.maximum(norms, eps)


class IntensityEncoder:
    """Simple non-neural baseline using per-channel intensity summaries."""

    name = "intensity"
    input_size = 0

    @property
    def feature_dim(self) -> int:
        return 5 * 7

    def encode_sites(self, sites: list[np.ndarray]) -> np.ndarray:
        rows: list[np.ndarray] = []
        for image in sites:
            channel_features = []
            for channel in image:
                qs = np.percentile(channel, [1, 10, 50, 90, 99]).astype(np.float32)
                stats = np.array([channel.mean(), channel.std()], dtype=np.float32)
                channel_features.append(np.concatenate([stats, qs]))
            rows.append(np.concatenate(channel_features))
        return l2_normalize(np.stack(rows, axis=0).astype(np.float32))


@dataclass
class DINOv2Encoder:
    """Batched DINOv2 encoder with two pseudo-RGB Cell Painting channel groups."""

    model_name: str = "dinov2_vits14"
    device: str = "cuda"

    def __post_init__(self) -> None:
        import torch

        self.torch = torch
        if self.device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"
        if self.device == "mps" and not torch.backends.mps.is_available():
            self.device = "cpu"
        self.model = torch.hub.load("facebookresearch/dinov2", self.model_name)
        self.model.to(self.device)
        self.model.eval()
        self.input_size = 224
        self._single_dim = int(self.model.embed_dim)
        self.name = self.model_name

    @property
    def feature_dim(self) -> int:
        return self._single_dim * 2

    def encode_sites(self, sites: list[np.ndarray]) -> np.ndarray:
        """Encode normalized/resized 5-channel site images."""
        if not sites:
            return np.empty((0, self.feature_dim), dtype=np.float32)

        rgbs = []
        for image in sites:
            rgbs.append(image[[0, 1, 4]])
            rgbs.append(image[[2, 3, 4]])
        batch = np.stack(rgbs, axis=0).astype(np.float32)

        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
        batch = (batch - mean) / std

        torch = self.torch
        tensor = torch.from_numpy(batch).to(self.device)
        with torch.inference_mode():
            features = self.model(tensor).detach().cpu().numpy().astype(np.float32)

        paired = features.reshape(len(sites), 2, self._single_dim)
        output = np.concatenate([paired[:, 0, :], paired[:, 1, :]], axis=1)
        return l2_normalize(output)


def build_encoder(name: str, device: str = "cuda", model_name: str | None = None):
    """Create an encoder by name."""
    if name == "intensity":
        return IntensityEncoder()
    if name == "dinov2":
        return DINOv2Encoder(model_name=model_name or "dinov2_vits14", device=device)
    raise ValueError("Unknown encoder. Choose one of: intensity, dinov2")
