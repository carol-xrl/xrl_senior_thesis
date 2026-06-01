# Senior Thesis — ST

我们的目标是完成一个高质量的 research 并产出报告。具体背景见"文章结构"章节。

> ⚠️ **工作流**：执行每一步前请先阅读 README。每次工作结束更新 README（Progress 打勾 + st Structure）、`log.md`、`skills/` 文件夹。
> 🌿 **分支**：所有工作在 `ssl` 分支上进行。Mac 和服务器均使用 `git switch ssl`，不要在 `main` 或 `st` 上操作。

---

# 工作流

1. 执行每一步前阅读 README
2. 每次工作结束更新三个地方：
   - **README.md** — Progress 打勾并加一句话总结；如有新文件，在 st Structure 里注明
   - **log.md** — 详细记录这一步做了什么、踩了什么坑
   - **skills/** — 发现更好的流程或踩了坑就 update；探索出新流程就新建 skill 文件，并在下方 Skill list 更新描述
3. 如需整理知识点供学习，更新 `notes/` 文件夹

> 遇到问题请深思熟虑后提出解决方案；如需权限或数据请告知并说明如何操作，不要直接退而求其次。

---

# Progress

## 准备阶段

- [ ] 熟悉代码框架
- [ ] SSH 上服务器并 `git clone`，开始下载数据集（可以并行），并更新 `skills/runpod.md`（有空缺字段和路径错误）
- [ ] （与上一步并行）在服务器上搭建 `auto_experiment` pipeline 并通过 smoke test；如有必要更新 `skills/auto_experiment.md`
- [ ] 确认 CPJUMP1 metadata 文件（perturbation ID、target gene、plate batch ID）随数据集下载完毕且路径可读
- [ ] 抽查 3–5 张 TIFF：确认通道数正确、图像无损坏
- [ ] 确定并记录 **checkpoint 保存策略**：每 N epoch 存一次，保留 val 指标最优的 top-k 个；在 `configs/train_defaults.yaml` 里固定此策略，所有实验统一使用

## Phase 1 — Baseline（~2h）

> 所有 baseline embedding 存到 `/workspace/data/cpjump1/features/baselines/`

- [ ] **B1** — Zero-shot DINOv2-B（ImageNet 权重，不做任何后训练）
  - 在 val set 提取 well-level embedding（多 site 取均值）→ 跑全部 4 个 metrics
- [ ] **B2** — Zero-shot DINOv2-S（同上，用于对比规模差异）
- [ ] **B3** — MAE ViT-B（ImageNet MAE init，不做 HCS 后训练）
  - *与前人工作的直接对比锚点*
- [ ] **B4** — DINOv2-B + pixel MSE 后训练（最朴素的域适配，无任何特殊 trick）
  - 100% train plates，无特殊 norm、无特殊 channel 处理
  - *"暴力微调"基线，用来衡量 trick 各自的贡献*

## Phase 2 — Ablation：Normalization（~2h）

固定：DINOv2-B + pixel MSE loss + 标准 concat channel 输入。
逐一改变 normalization 策略，在 val set 跑 replicate consistency + perturbation matching mAP。

- [ ] **N1** — 不做任何 normalization
- [ ] **N2** — 逐通道 z-score（全局统计量）
- [ ] **N3** — 逐 plate z-score（plate-level 统计量，抑制批次效应）
- [ ] **N4** — 训练时逐 plate z-score + 推理时 TVN（Typical Variation Normalization）

## Phase 3 — Ablation：Channel 处理（~1.5h）

固定：DINOv2-B + pixel MSE loss + Phase 2 最优 norm。

- [ ] **C1** — 5 通道直接 concat（标准 ViT 输入方式）
- [ ] **C2** — 每通道独立 tokenize + 可学习 channel-identity embedding
- [ ] **C3** — C2 + channel dropout（训练时随机丢弃 1 个通道，增强泛化）

## Phase 4 — Ablation：Loss 函数（~2h）

固定：DINOv2-B + Phase 2 最优 norm + Phase 3 最优 channel。

- [ ] **L1** — Pixel MSE（重建 loss 基线）
- [ ] **L2** — Fourier MSE（频域重建，捕获周期性细胞纹理）
- [ ] **L3** — Fourier MSE + cross-channel consistency 正则项

## Phase 5 — Ablation：Backbone 规模（~4h）

全部最优设置（Phase 2–4 winner）。

- [ ] **M1** — DINOv2-S（22M）
- [ ] **M2** — DINOv2-B（86M）
- [ ] **M3** — DINOv2-L（307M）`[optional，视时间预算]`
- [ ] **M4** — MAE ViT-B（86M，最优 trick 版本）— 跨框架对比

## Phase 6 — 数据效率曲线（~2h）

最优完整配置（Phase 2–4 winner + DINOv2-B）。
按 plate 随机采样，评估 val perturbation matching mAP。

- [ ] **D1** — 10% train plates
- [ ] **D2** — 25%
- [ ] **D3** — 50%
- [ ] **D4** — 100%（复用 Phase 5 最优 checkpoint）

## Phase 7 — 最终模型：完整 Test Set 评估（~1.5h）

使用 Phase 2–5 选出的最优配置，在 **test set** 上评估全部 4 个 axis。

- [ ] Replicate consistency mAP（同一扰动的 replicate embedding 聚类质量）
- [ ] Perturbation matching Recall@k（跨 plate 匹配，ground truth 来自 CPJUMP1 perturbation ID metadata）
- [ ] Cross-modality retrieval mAP（Compound ↔ CRISPR；ORF 作为 zero-shot held-out probe，不参与任何 val 调参）
- [ ] Temporal robustness（同一扰动跨 plate batch ID 的 embedding cosine drift）
- [ ] Cell-line generalization（A549 vs U2OS 同一扰动 embedding 一致性，作为附加分析）
- [ ] 提取最终 embedding，用于 UMAP 可视化

> 最终 embedding 存到 `/workspace/data/cpjump1/features/final/`

## Phase 8 — 出图（~4h，Mac）

先把结果拉回 Mac：
```bash
rsync -avz root@<HOST>:/workspace/.../outputs/metrics/  ~/Desktop/xrl_senior_thesis/st/outputs/metrics/  -e "ssh -p <PORT>"
rsync -avz root@<HOST>:/workspace/.../features/final/   ~/Desktop/xrl_senior_thesis/st/outputs/features/ -e "ssh -p <PORT>"
```

- [ ] **Figure 1** — Pipeline 示意图（多通道 Cell Painting 图像 → encoder → 下游任务）
- [ ] **Figure 2** — CPJUMP1 数据集划分（plate 布局、modality × cell-line 覆盖矩阵）
- [ ] **Figure 3** — 架构图（per-channel tokenization → DINOv2-B encoder → decoder/projection head）
- [ ] **Figure 4** — UMAP：最优模型 embedding，按扰动类型 / 细胞系 / modality 着色对比
- [ ] **Figure 5** — 分组柱状图：各 ablation 类别（norm / channel / loss）val mAP 对比
- [ ] **Figure 6** — 折线图：数据效率曲线（DINOv2-S / B / L、MAE ViT-B）
- [ ] **Figure 7** — UMAP 对比：最优模型 vs. MAE ViT-B baseline，叠加 plate batch ID 着色

## Phase 9 — 写作（~8h，Mac）

- [ ] 用实验结果填入 proposal 中所有 `[X]`、`[Y]`、`[Z%]` 占位符
- [ ] Abstract（所有数字到手后最后写）
- [ ] Section 3 Benchmark — 确认 split 表格 + metric 定义 + embedding aggregation 方案
- [ ] Section 4 Method — 补充实际 hyperparameter（lr、epoch、batch size、checkpoint 策略）
- [ ] Section 5 Ablation — 写 results 段落 + analysis（哪个因素贡献最大？规模和 trick 哪个更重要？）
- [ ] Section 6 Conclusion — 填入最终数字
- [ ] Section 7 Limitations — 对照实际实验更新
- [ ] 通读 + 一致性检查（图号、metric 名称、模型命名统一）

---

# st Structure

```
st/
  configs/                  # 实验配置 YAML，每个 ablation variant 一个文件
  scripts/                  # 可执行入口（train.py, evaluate.py, queue_runner.py 等）
  src/                      # 库代码（数据加载、模型、loss、metrics）
  skills/                   # 标准流程文档（见下方 Skill list）
  outputs/
    metrics/                # CSV 实验结果 — 拉回 Mac
    figures/                # 图表 — 拉回 Mac
    logs/                   # tmux 重定向的 stdout/stderr — 留在服务器
    checkpoints/            # 模型权重 — 留在服务器
  notes/                    # 知识整理（按需更新）
  log.md                    # 详细工作日志
  README.md                 # 本文件
```

---

# Skill list

| 文件 | 内容 |
|------|------|
| `skills/runpod.md` | 如何 SSH 上 RunPod H100 服务器、目录结构、用 tmux 跑实验、将结果 rsync 回 Mac |
| `skills/auto_experiment.md` | experiment queue 的工作原理：queue YAML 格式、拓扑调度逻辑、smoke test 协议、失败处理 |

---

# 文章结构

## Self-Supervised Visual Representation Learning for High Content Cellular Screening

High Content Screening (HCS) enables quantitative, large-scale analysis of cellular responses to genetic and chemical perturbations, underpinning data-driven drug discovery. While vision models have shown promise in automating HCS image interpretation, existing encoders often fail to capture biologically meaningful morphological patterns — especially under data-limited, multi-modal conditions. This project investigates **data-efficient post-pretraining strategies** for cellular visual encoders, using DINOv2 as a strong initialization and tailoring it to the HCS domain via structured normalization, channel-aware tokenization, and a biologically-informed loss. We validate on a curated CPJUMP1 subset spanning two cell lines (A549, U2OS) and three perturbation modalities (compound, ORF, CRISPR) across four evaluation axes.

## 1. Introduction

**Para 1 — Background.** Cell Painting is a multiplexed fluorescence imaging assay that simultaneously stains up to 8 cellular compartments, enabling high-throughput phenotypic profiling of millions of genetic and chemical perturbations. HCS systems built on this protocol form the experimental backbone of modern drug discovery, allowing quantitative measurement of cellular morphology at scale.

**Para 2 — Visual models as a lever.** Deep visual encoders have demonstrated strong performance on HCS downstream tasks including perturbation matching, mechanism-of-action prediction, and genetic interaction inference. Domain-specific pretraining consistently outperforms ImageNet baselines, yet existing approaches either require massive proprietary datasets (e.g., RPI-93M, 93M images) or underexplore the potential of post-pretraining on modest public data. A key open question remains: *how much domain-specific data is actually needed, and which training strategies drive the gains?*

> **Figure 1:** Multi-channel Cell Painting image → encoder → downstream tasks (replicate consistency / perturbation matching / cross-modality retrieval). Illustrates the encoding pipeline and evaluation paradigm.

---

## 2. Related Work

**Visual models for Cell Painting.** Convolutional and transformer-based architectures have been applied to HCS phenotyping. Domain-specific inductive biases — multi-channel input, plate-aware normalization, perturbation-aware training objectives — are consistently critical for downstream performance.

**HCS datasets.** CPJUMP1 (JUMP Cell Painting Consortium) is the largest public HCS benchmark, covering compound, ORF, and CRISPR modalities across multiple cell lines. Other notable datasets include RxRx1, RxRx3, and the Recursion Phenomics Imageset (RPI-93M, ~93M images across 4M perturbations).

**Supervised → weakly supervised → self-supervised.** Early HCS encoders used perturbation-label supervised classifiers (e.g., DenseNet-161). Weakly supervised learning (WSL) improved generalization via experimental metadata as noisy labels. Recent self-supervised approaches — MAE and variants — trained on large HCS corpora demonstrate superior recall of known biological relationships, establishing self-supervised pretraining as the new state of the art.

**Post-pretraining strategies.** Domain-adaptive post-pretraining (continuing pretraining on domain-specific data from a strong general initialization) has shown efficacy in medical imaging and remote sensing. Its application to cellular imaging in the data-efficient regime remains largely unexplored.

**Our contribution.** We ask: *can a well-chosen post-pretraining strategy on a small CPJUMP1 subset match encoders trained on orders-of-magnitude more data?* We address this by (1) constructing a structured four-axis benchmark from CPJUMP1, and (2) proposing a post-pretraining framework on **DINOv2-B** combining plate-aware normalization, channel-agnostic tokenization, and a Fourier-augmented cross-channel consistency loss — competitive with large-scale pretrained baselines at a fraction of the data.

---

## 3. Benchmark

We construct a structured evaluation suite from a CPJUMP1 subset covering **two cell lines** (A549, U2OS) and **three perturbation modalities** (compound, ORF, CRISPR). Both cell lines are retained: their morphological diversity (lung adenocarcinoma vs. osteosarcoma) is essential for assessing generalization, and cross-cell-line embedding consistency is itself a meaningful evaluation signal for drug discovery applications.

### 3.1 Data Split

| Split | Plates | Cell lines | Modalities |
|-------|--------|------------|------------|
| **Train** | BR00116991/92, BR00116995, BR00117024, BR00117020, BR00117022, BR00118041/42, BR00118045/46 | A549, U2OS | Compound, ORF, CRISPR |
| **Val** | BR00116993, BR00117025, BR00118043, BR00118047 | A549, U2OS | Compound, CRISPR |
| **Test** | BR00116994, BR00117026, BR00117021/23, BR00118044, BR00118048 | A549, U2OS | Compound, ORF, CRISPR |

*~37,800 images total (12 train plates × ~350 wells × 9 sites). ORF is absent from the validation split by dataset design; ORF evaluation is therefore a zero-shot held-out test, which we treat as a cross-modality generalization probe.*

> **Figure 2:** CPJUMP1 structure and our split — plate layout, modality × cell-line coverage, and position within the full CPJUMP1 dataset.

### 3.2 Evaluation Axes

| Axis | Task | Metric | Split |
|------|------|--------|-------|
| **Replicate consistency** | Same perturbation, same plate → embeddings cluster | mAP | Val / Test |
| **Perturbation matching** | Match perturbations across wells/plates using bio-relationship DBs | Recall@k (STRING, CORUM) | Val / Test |
| **Cross-modality retrieval** | Compound ↔ CRISPR matching; ORF as zero-shot probe | mAP across modalities | Test |
| **Temporal robustness** | Embedding stability across plate acquisition batches | Cosine drift across batch IDs | Test |

*Temporal robustness leverages plate acquisition metadata within the existing short-plate setup (batch ID variation across train/test plates), without requiring a separate double-plate configuration.*

---

## 4. Method

### 4.1 Base Model Choice: DINOv2-B

We use **DINOv2-B (86M)** as the backbone, initialized from its ImageNet pretrained weights. Compared to MAE ViT-B, DINOv2-B provides substantially stronger initialization (linear probe: 86.7% vs. ~68% on ImageNet), meaning the limited domain-specific data budget is spent entirely on learning HCS-specific patterns rather than recovering general visual features. MAE ViT-B (ImageNet init) is retained as a direct baseline for comparison with the prior literature.

### 4.2 Post-Pretraining Framework

We apply domain-adaptive post-pretraining on the training plates using the following components:

- **Plate-aware normalization** — per-plate z-score standardization during training; TVN (Typical Variation Normalization) at inference to suppress batch effects.
- **Channel-agnostic tokenization** — each fluorescence channel tokenized independently with a learnable channel-identity embedding (following CA-MAE), enabling flexible inference across varying channel configurations.
- **Tailored loss: Fourier MSE + cross-channel consistency** — reconstruction loss computed in the frequency domain (capturing periodic cellular textures) augmented with a cross-channel consistency term that penalizes biologically implausible inter-channel decorrelation.

> **Figure 3:** Architecture diagram — 5-channel input → per-channel tokenization → DINOv2-B encoder → [decoder for training / projection head for eval].

> **Figure 4:** UMAP of learned embeddings colored by perturbation class, cell line, and modality.

---

## 5. Ablation Study

### 5.1 Setup

All experiments on a single H100. Estimated total compute: **~12–13h**, well within the 24h budget. Ablations use DINOv2-S (22M) for speed; final model uses DINOv2-B. MAE ViT-B serves as a cross-framework baseline.

| Category | Variants |
|----------|----------|
| **Normalization** | None / per-channel z-score / per-plate z-score / TVN |
| **Channel handling** | Concatenated (standard) / independent + channel-ID token / + channel dropout |
| **Loss** | Pixel MSE / Fourier MSE / Fourier MSE + cross-channel consistency |
| **Backbone** | DINOv2-S / DINOv2-B / MAE ViT-B (baseline) |
| **Data fraction** | 10% / 25% / 50% / 100% of train plates |

### 5.2 Results

> **Figure 5:** Grouped bar charts — mAP on replicate consistency and perturbation matching per ablation category (normalization / channel / loss).

> **Figure 6:** Line plots — performance vs. training data fraction for DINOv2-S, DINOv2-B, and MAE ViT-B. Illustrates data efficiency curves.

> **Figure 7:** UMAP comparison — best model vs. MAE ViT-B baseline, colored by perturbation identity and plate batch ID.

### 5.3 Analysis

- Which single component contributes most to downstream performance?
- Does backbone initialization quality outweigh loss design at small data scales?
- Is cross-modality retrieval (esp. zero-shot ORF) the hardest axis, and which tricks help most?
- At what data fraction does our method's advantage over MAE ViT-B emerge?

---

## 6. Conclusion

We present a structured four-axis benchmark for evaluating cellular visual encoders on a CPJUMP1 subset, covering replicate consistency, perturbation matching, cross-modality retrieval (including zero-shot ORF), and temporal robustness across two cell lines and three perturbation modalities. Our post-pretraining framework — DINOv2-B with plate-aware TVN normalization, channel-agnostic tokenization, and Fourier + cross-channel consistency loss — achieves **[X]** on perturbation matching and **[Y]** on cross-modality retrieval, comparable to / exceeding encoders pretrained on RxRx3/RPI-93M by **[Z%]**, using only ~37,800 training images. We view this as a concrete step toward data-efficient, broadly deployable bio-visual foundation models for HCS phenotyping.

---

## 7. Limitations

- **Data scale**: Training on a short-plate CPJUMP1 subset (~37,800 images); generalization to the full JUMP dataset or proprietary HCS corpora is not assessed.
- **ORF validation gap**: ORF modality absent from validation split by dataset design; hyperparameter selection cannot be guided by ORF performance, and ORF results are purely test-time.
- **Biological ground truth ceiling**: Downstream evaluation relies on STRING and CORUM; recall metrics are bounded by database completeness and curation biases.
- **Compute constraints**: Single H100 rental limits ablation breadth; reported sweep is structured but not exhaustive. Seed variance not systematically assessed.