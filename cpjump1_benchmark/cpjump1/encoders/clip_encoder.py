"""CLIP ViT-L/14 encoder — OpenAI's vision-language model.

Model: ViT-L/14, pretrained on image-text pairs.
Input: 3-channel RGB, 224x224.
Output: 768-dim embedding per RGB group, concatenated → 1536-dim.
"""

import numpy as np
from .base import BaseEncoder


class CLIPEncoder(BaseEncoder):
    """CLIP ViT-L/14 vision encoder with channel grouping for Cell Painting."""

    def __init__(self, device: str = "mps"):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self.device = torch.device(device if torch.backends.mps.is_available() else "cpu")

        self.model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
        self.model = self.model.to(self.device)
        self.model.eval()

        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

        self._single_dim = 768  # CLIP ViT-L output dim
        self._torch = torch

    @property
    def input_size(self) -> int:
        return 224

    @property
    def num_channels(self) -> int:
        return 5

    @property
    def feature_dim(self) -> int:
        return self._single_dim * 2

    @property
    def name(self) -> str:
        return "clip"

    def _encode_rgb(self, rgb: np.ndarray) -> np.ndarray:
        """Encode a single (3, H, W) RGB image using CLIP vision encoder."""
        torch = self._torch
        from PIL import Image

        # Convert (3, H, W) float32 [0,1] → PIL Image
        img_hw3 = (rgb.transpose(1, 2, 0) * 255).clip(0, 255).astype(np.uint8)
        pil_img = Image.fromarray(img_hw3)

        # Use CLIP processor for normalization and resizing
        inputs = self.processor(images=pil_img, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)

        with torch.no_grad():
            features = self.model.get_image_features(pixel_values=pixel_values)

        return features.cpu().numpy().flatten()

    def encode_site(self, img: np.ndarray) -> np.ndarray:
        """Encode a 5-channel site image via two RGB groups.

        Args:
            img: (5, 224, 224) float32 in [0, 1].

        Returns:
            Concatenated feature vector (2 * 768 = 1536).
        """
        group_a = img[[0, 1, 4]]
        group_b = img[[2, 3, 4]]

        feat_a = self._encode_rgb(group_a)
        feat_b = self._encode_rgb(group_b)

        return np.concatenate([feat_a, feat_b])
