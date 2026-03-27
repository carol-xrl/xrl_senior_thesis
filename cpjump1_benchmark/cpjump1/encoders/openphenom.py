"""OpenPhenom encoder — Recursion's cell painting foundation model.

Model: MAE-based ViT, channel-agnostic, trained on JUMP-CP + RxRx3.
Input: Variable number of channels, 256x256, uint8.
Output: 384-dim embedding.
Weights: https://huggingface.co/recursionpharma/OpenPhenom
"""

import numpy as np
from .base import BaseEncoder


class OpenPhenomEncoder(BaseEncoder):
    """OpenPhenom encoder using Recursion's pretrained MAE model."""

    def __init__(self, device: str = "mps"):
        import torch
        from huggingface_hub import hf_hub_download

        self.device = torch.device(device if torch.backends.mps.is_available() else "cpu")

        # Download and load model
        model_path = hf_hub_download(
            repo_id="recursionpharma/OpenPhenom",
            filename="model.ckpt",
        )

        # OpenPhenom uses a custom MAE architecture
        # Load checkpoint and extract encoder
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)

        # The model expects a specific loading pattern
        from openphenom import MAEModel
        self.model = MAEModel.from_pretrained("recursionpharma/OpenPhenom")
        self.model = self.model.to(self.device)
        self.model.eval()

        self._torch = torch

    @property
    def input_size(self) -> int:
        return 256

    @property
    def num_channels(self) -> int:
        return 5  # channel-agnostic, but we use 5 fluorescent

    @property
    def feature_dim(self) -> int:
        return 384

    @property
    def name(self) -> str:
        return "openphenom"

    def encode_site(self, img: np.ndarray) -> np.ndarray:
        """Encode a 5-channel site image.

        Args:
            img: (5, 256, 256) float32 array in [0, 1].

        Returns:
            384-dim feature vector.
        """
        torch = self._torch

        # OpenPhenom expects uint8 input
        img_uint8 = (img * 255).clip(0, 255).astype(np.uint8)

        # Convert to tensor: (1, C, H, W)
        tensor = torch.from_numpy(img_uint8).float().unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model(tensor)  # (1, feature_dim)

        return features.cpu().numpy().flatten()
