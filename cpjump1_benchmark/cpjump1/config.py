"""Configuration loading and validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict
import yaml


@dataclass
class Config:
    # Experiment filters
    batch: str = "2020_11_04_CPJUMP1"
    density: int = 100
    antibiotics: str = "absent"
    exclude_cas9_compound: bool = True

    # Evaluation params
    batch_size: int = 100000
    null_size: int = 100000
    q_threshold: float = 0.05
    random_seed: int = 42

    # Paths (relative to project root)
    profiles_dir: str = "profiles"
    profile_suffix: str = "normalized_feature_select_negcon_batch.csv.gz"
    experiment_metadata: str = "benchmark/output/experiment-metadata.tsv"
    compound_annotations: str = "benchmark/input/JUMP-Target-1_compound_metadata_additional_annotations.tsv"

    # Time label mapping: modality -> {hours: "short"/"long"}
    time_labels: Dict[str, Dict[int, str]] = field(default_factory=lambda: {
        "compound": {24: "short", 48: "long"},
        "crispr": {96: "short", 144: "long"},
        "orf": {48: "short", 96: "long"},
    })

    def time_label(self, modality: str, hours: int) -> str:
        return self.time_labels[modality][hours]

    def hours_for(self, modality: str, label: str) -> int:
        for hours, lbl in self.time_labels[modality].items():
            if lbl == label:
                return hours
        raise ValueError(f"No {label} time for {modality}")


def load_config(path: str = None) -> Config:
    if path is None:
        return Config()
    with open(path) as f:
        raw = yaml.safe_load(f)
    kwargs = {}
    for section in ["experiment", "evaluation", "paths"]:
        if section in raw:
            kwargs.update(raw[section])
    if "time_labels" in raw:
        # Convert string keys to int keys
        kwargs["time_labels"] = {
            mod: {int(k): v for k, v in mapping.items()}
            for mod, mapping in raw["time_labels"].items()
        }
    return Config(**kwargs)
