"""Base encoder interface for cell painting feature extraction."""

from abc import ABC, abstractmethod
import numpy as np


class BaseEncoder(ABC):
    """Abstract base class for all encoders.

    Subclasses must implement:
        - encode_site(): takes a multi-channel image, returns a feature vector
        - input_size: expected spatial resolution
        - num_channels: expected number of input channels (3 or 5)
    """

    @property
    @abstractmethod
    def input_size(self) -> int:
        """Expected spatial resolution (e.g. 224, 256)."""

    @property
    @abstractmethod
    def num_channels(self) -> int:
        """Number of input channels (3 for RGB encoders, 5 for native multi-channel)."""

    @property
    @abstractmethod
    def feature_dim(self) -> int:
        """Output feature dimensionality."""

    @property
    def name(self) -> str:
        """Encoder name for file naming."""
        return self.__class__.__name__.lower()

    @abstractmethod
    def encode_site(self, img: np.ndarray) -> np.ndarray:
        """Encode a single site image to a feature vector.

        Args:
            img: (C, H, W) float32 array, normalized to [0, 1].
                 C = self.num_channels, H = W = self.input_size.

        Returns:
            1D feature vector of shape (feature_dim,).
        """

    def encode_well(self, site_features: list) -> np.ndarray:
        """Aggregate site-level features to well-level (mean pooling).

        Args:
            site_features: List of 1D feature vectors from encode_site().

        Returns:
            1D feature vector (mean of site features).
        """
        return np.mean(site_features, axis=0)
