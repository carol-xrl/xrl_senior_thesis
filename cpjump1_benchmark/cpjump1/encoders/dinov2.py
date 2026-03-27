"""DINOv2 encoder — Meta's self-supervised ViT.

Model: ViT-B/14, pretrained on LVD-142M.
Input: 3-channel RGB, 224x224.
Output: 768-dim embedding (ViT-B) per RGB group, concatenated → 1536-dim.
"""

import numpy as np
from .base import BaseEncoder


class DINOv2Encoder(BaseEncoder):
    """DINOv2 ViT-B/14 encoder with channel grouping for Cell Painting."""

    def __init__(self, model_name: str = "dinov2_vitb14", device: str = "mps"):
        import torch

        self.device = torch.device(device if torch.backends.mps.is_available() else "cpu")

        self.model = torch.hub.load("facebookresearch/dinov2", model_name)
        self.model = self.model.to(self.device)
        self.model.eval()

        # Get feature dim from model
        self._single_dim = self.model.embed_dim  # 768 for ViT-B
        self._torch = torch

    @property
    def input_size(self) -> int:
        return 224

    @property
    def num_channels(self) -> int:
        return 5  # we handle grouping internally

    @property
    def feature_dim(self) -> int:
        return self._single_dim * 2  # two RGB groups concatenated

    @property
    def name(self) -> str:
        return "dinov2"

    def _encode_rgb(self, rgb: np.ndarray) -> np.ndarray:
        """Encode a single (3, 224, 224) RGB image."""
        torch = self._torch

        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
        std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)
        rgb = (rgb - mean) / std

        tensor = torch.from_numpy(rgb).float().unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model(tensor)  # (1, embed_dim)

        return features.cpu().numpy().flatten()

    def encode_site(self, img: np.ndarray) -> np.ndarray:
        """Encode a 5-channel site image via two RGB groups.

        Args:
            img: (5, 224, 224) float32 in [0, 1].

        Returns:
            Concatenated feature vector (2 * embed_dim).
        """
        # Group A: ch1(AGP) + ch2(Mito) + ch5(DNA)
        group_a = img[[0, 1, 4]]
        # Group B: ch3(RNA) + ch4(ER) + ch5(DNA)
        group_b = img[[2, 3, 4]]

        feat_a = self._encode_rgb(group_a)
        feat_b = self._encode_rgb(group_b)

        return np.concatenate([feat_a, feat_b])
