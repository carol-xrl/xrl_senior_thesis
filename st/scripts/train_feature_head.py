#!/usr/bin/env python
"""Train a small projection head on frozen well-level features."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch import nn


ST_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ST_DIR / "src"))

from st_benchmark.evaluate import evaluate_feature_dataframe, merge_features_with_metadata, read_table, write_table
from st_benchmark.metadata import build_subset_metadata, load_config
from st_benchmark.metrics import (
    MetricResult,
    feature_columns,
    negcon_challenge,
    replicate_retrieval,
    summarize_metric,
)
from st_benchmark.split_eval import evaluate_split_retrieval
from st_benchmark.transforms import transformed_features


class ProjectionHead(nn.Module):
    """A compact MLP head for adapting frozen encoder features."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.net(x), dim=1)


class ProxyClassifier(nn.Module):
    """Cosine classifier used for proxy-CE training."""

    def __init__(self, output_dim: int, n_classes: int, temperature: float):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_classes, output_dim))
        self.temperature = temperature
        nn.init.normal_(self.weight, std=0.02)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        weight = F.normalize(self.weight, dim=1)
        return F.linear(z, weight) / self.temperature


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def supervised_contrastive_loss(z: torch.Tensor, labels: torch.Tensor, temperature: float) -> torch.Tensor | None:
    """Supervised contrastive loss with same-compound positives."""
    n = z.shape[0]
    if n < 2:
        return None
    same = labels[:, None] == labels[None, :]
    self_mask = torch.eye(n, dtype=torch.bool, device=z.device)
    positive_mask = same & ~self_mask
    valid = positive_mask.any(dim=1)
    if not bool(valid.any()):
        return None

    logits = (z @ z.T) / temperature
    logits = logits - logits.max(dim=1, keepdim=True).values.detach()
    denominator_mask = ~self_mask
    exp_logits = torch.exp(logits) * denominator_mask
    log_prob = logits - torch.log(exp_logits.sum(dim=1, keepdim=True).clamp_min(1e-12))
    positive_count = positive_mask.sum(dim=1).clamp_min(1)
    mean_log_prob = (positive_mask * log_prob).sum(dim=1) / positive_count
    return -mean_log_prob[valid].mean()


def batch_hard_triplet_loss(z: torch.Tensor, labels: torch.Tensor, margin: float) -> torch.Tensor | None:
    """Batch-hard triplet loss in cosine-distance space."""
    n = z.shape[0]
    if n < 3:
        return None
    distances = 1.0 - (z @ z.T)
    same = labels[:, None] == labels[None, :]
    self_mask = torch.eye(n, dtype=torch.bool, device=z.device)
    positive_mask = same & ~self_mask
    negative_mask = ~same
    valid = positive_mask.any(dim=1) & negative_mask.any(dim=1)
    if not bool(valid.any()):
        return None

    hardest_positive = torch.where(positive_mask, distances, torch.full_like(distances, -1.0)).max(dim=1).values
    hardest_negative = torch.where(negative_mask, distances, torch.full_like(distances, 2.0)).min(dim=1).values
    loss = F.relu(hardest_positive - hardest_negative + margin)
    return loss[valid].mean()


def make_projected_features(
    model: ProjectionHead,
    df: pd.DataFrame,
    feat_cols: list[str],
    device: torch.device,
    batch_size: int = 4096,
) -> pd.DataFrame:
    """Project all rows and return a feature table keyed by plate and well."""
    values = df[feat_cols].to_numpy(dtype=np.float32)
    projected_chunks = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(values), batch_size):
            batch = torch.from_numpy(values[start : start + batch_size]).to(device)
            projected_chunks.append(model(batch).cpu().numpy())

    projected = np.concatenate(projected_chunks, axis=0)
    output = df[["Metadata_Plate", "Metadata_Well"]].reset_index(drop=True).copy()
    feature_frame = pd.DataFrame(
        projected.astype(np.float32),
        columns=[f"feature_{idx}" for idx in range(projected.shape[1])],
        index=output.index,
    )
    return pd.concat([output, feature_frame], axis=1)


def validation_score(
    model: ProjectionHead,
    base_df: pd.DataFrame,
    feat_cols: list[str],
    metadata: pd.DataFrame,
    min_positive_count: int,
    device: torch.device,
) -> tuple[float, pd.DataFrame]:
    """Return validation replicate mAP plus a compact validation summary."""
    projected = make_projected_features(model, base_df, feat_cols, device)
    eval_df = merge_features_with_metadata(projected, metadata)
    query_mask = eval_df["Metadata_split"].to_numpy() == "val"
    replicate = replicate_retrieval(eval_df, min_positive_count=min_positive_count, query_mask=query_mask)
    negcon = negcon_challenge(eval_df, min_positive_count=min_positive_count, query_mask=query_mask)
    summary = pd.DataFrame(
        [
            {"scope": "val_queries", **summarize_metric("replicate_retrieval", replicate)},
            {"scope": "val_queries", **summarize_metric("negcon_challenge", negcon)},
        ]
    )
    score = float(replicate.query_scores["average_precision"].mean()) if not replicate.query_scores.empty else float("nan")
    return score, summary


def train_epoch(
    model: ProjectionHead,
    classifier: ProxyClassifier | None,
    optimizer: torch.optim.Optimizer,
    features: torch.Tensor,
    labels: torch.Tensor,
    loss_name: str,
    batch_size: int,
    temperature: float,
    margin: float,
) -> float:
    model.train()
    if classifier is not None:
        classifier.train()

    losses: list[float] = []
    permutation = torch.randperm(features.shape[0], device=features.device)
    for start in range(0, features.shape[0], batch_size):
        idx = permutation[start : start + batch_size]
        if idx.numel() < 2:
            continue
        x = features[idx]
        y = labels[idx]
        z = model(x)

        if loss_name == "supcon":
            loss = supervised_contrastive_loss(z, y, temperature)
        elif loss_name == "triplet":
            loss = batch_hard_triplet_loss(z, y, margin)
        elif loss_name == "proxy_ce":
            assert classifier is not None
            loss = F.cross_entropy(classifier(z), y)
        else:
            raise ValueError(f"Unknown loss: {loss_name}")

        if loss is None or not torch.isfinite(loss):
            continue
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))

    return float(np.mean(losses)) if losses else float("nan")


def write_final_outputs(
    *,
    model: ProjectionHead,
    base_df: pd.DataFrame,
    feat_cols: list[str],
    metadata: pd.DataFrame,
    config: dict,
    output_dir: Path,
    prefix: str,
    device: torch.device,
) -> None:
    """Write projected features and benchmark outputs."""
    projected = make_projected_features(model, base_df, feat_cols, device)
    write_table(projected, output_dir / f"{prefix}_projected_features.csv")

    min_positive_count = int(config["metrics"].get("min_positive_count", 1))
    full = evaluate_feature_dataframe(projected, metadata, min_positive_count=min_positive_count)
    write_table(full["summary"], output_dir / f"{prefix}_summary.csv")
    write_table(full["artifact"], output_dir / f"{prefix}_artifact_sensitivity.csv")

    for metric_name in ("replicate", "negcon", "target"):
        metric = full[metric_name]
        assert isinstance(metric, MetricResult)
        write_table(metric.query_scores, output_dir / f"{prefix}_{metric_name}_query_ap.csv")
        write_table(metric.aggregate_scores, output_dir / f"{prefix}_{metric_name}_map.csv")

    split_summary, _ = evaluate_split_retrieval(projected, metadata, min_positive_count=min_positive_count)
    write_table(split_summary, output_dir / f"{prefix}_split_retrieval_summary.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True)
    parser.add_argument("--config", default="st/configs/subset_u2os_compound_8plate.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--loss", choices=["supcon", "triplet", "proxy_ce"], required=True)
    parser.add_argument("--input-transform", default="plate_zscore_l2")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--output-dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--margin", type=float, default=0.2)
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    set_seed(args.seed)
    repo_root = Path(args.repo_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    metadata = build_subset_metadata(config, repo_root)
    raw_features = read_table(args.features)
    features = transformed_features(raw_features, metadata, args.input_transform)
    base_df = merge_features_with_metadata(features, metadata)
    feat_cols = feature_columns(base_df)

    train_df = base_df[(base_df["Metadata_split"] == "train") & (base_df["Metadata_control_type"] != "negcon")].copy()
    if train_df.empty:
        raise SystemExit("No train treatment rows found")
    label_codes, label_names = pd.factorize(train_df["Metadata_broad_sample"], sort=True)

    device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_x = torch.from_numpy(train_df[feat_cols].to_numpy(dtype=np.float32)).to(device)
    train_y = torch.from_numpy(label_codes.astype(np.int64)).to(device)

    model = ProjectionHead(len(feat_cols), args.hidden_dim, args.output_dim, args.dropout).to(device)
    classifier = ProxyClassifier(args.output_dim, len(label_names), args.temperature).to(device) if args.loss == "proxy_ce" else None
    params = list(model.parameters()) + (list(classifier.parameters()) if classifier is not None else [])
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=args.weight_decay)

    run_config = vars(args).copy()
    run_config.update(
        input_dim=len(feat_cols),
        n_train_rows=int(len(train_df)),
        n_train_labels=int(len(label_names)),
        device=str(device),
    )
    (output_dir / f"{args.prefix}_config.json").write_text(json.dumps(run_config, indent=2, sort_keys=True), encoding="utf-8")

    history_rows: list[dict[str, object]] = []
    best_score = -float("inf")
    best_state: dict[str, object] | None = None
    min_positive_count = int(config["metrics"].get("min_positive_count", 1))

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(
            model,
            classifier,
            optimizer,
            train_x,
            train_y,
            args.loss,
            args.batch_size,
            args.temperature,
            args.margin,
        )
        row: dict[str, object] = {"epoch": epoch, "train_loss": train_loss}

        if epoch == 1 or epoch % args.eval_every == 0 or epoch == args.epochs:
            val_score, val_summary = validation_score(model, base_df, feat_cols, metadata, min_positive_count, device)
            row["val_replicate_map"] = val_score
            for _, item in val_summary.iterrows():
                row[f"val_{item['metric']}_mean_ap"] = float(item["mean_ap"])
            if np.isfinite(val_score) and val_score > best_score:
                best_score = val_score
                best_state = {
                    "model": {key: value.detach().cpu() for key, value in model.state_dict().items()},
                    "classifier": (
                        {key: value.detach().cpu() for key, value in classifier.state_dict().items()}
                        if classifier is not None
                        else None
                    ),
                    "epoch": epoch,
                    "val_replicate_map": val_score,
                }
        history_rows.append(row)
        print(" ".join(f"{key}={value}" for key, value in row.items()), flush=True)

    history = pd.DataFrame(history_rows)
    write_table(history, output_dir / f"{args.prefix}_train_history.csv")

    if best_state is not None:
        model.load_state_dict(best_state["model"])
        torch.save(best_state, output_dir / f"{args.prefix}_best_checkpoint.pt")

    write_final_outputs(
        model=model,
        base_df=base_df,
        feat_cols=feat_cols,
        metadata=metadata,
        config=config,
        output_dir=output_dir,
        prefix=args.prefix,
        device=device,
    )


if __name__ == "__main__":
    main()

