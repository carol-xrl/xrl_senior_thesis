请和我一起高质量完成一篇顶会论文，需要有丰富的实验，实验和结果详尽&分析翔实&结构清晰的实验报告。一起加油！对于背景，请查看代码库以及“文章组织”这个章节。

注意：请理解我们的背景，我们没那么多卡（只能去租，预算100美金，希望可以1-2天完成所有实验），我们只能做一个CPJUMP1的子集！（比如发明一个只在1-4个plate上测试的相关指标，到时候我们一起预估实验、制定计划）然后选择不错且参数量我们可以承担的encoder测试。但是这不妨碍我们产出优异的论文。
---
# To DO List
- [x] 构思文章结构（high level的，不需要太具体）：见 `paper_outline.md` 和 `benchmark_design.md`
- [ ] 制定benchmark并implement：已完成 metadata/metrics smoke scaffold、download manifest、real-feature evaluation、basic plotting；下一步接真实 encoder feature extraction
- [ ] 实验
    - [x] 制定实验计划（baseline、需要选择的loss function/tricks）：见 `experiment_plan.md`
    - [x] 预估计算资源，租显卡（希望在1天内完成所有实验），我把ssh给你：见 `resource_plan.md`
    - [ ] 写README.md 以及构建整个repo并commit
    - [ ] pilot实验（下载模型、保证smoke test可以跑通）
    - [ ] tmux把所有实验挂在后台跑
基于CPJUMP1的数据重构一个数据库，最好用1-4个plate可以解决。

---
# 实验详细计划


---
# 文章组织
## 1. Introduction
High Content Screening (HCS) enables large-scale quantitative analysis of cellular responses to genetic and chemical perturbations, forming a foundation for data-driven drug discovery. Recent advances in machine vision have made automated interpretation of HCS images possible. However, existing visual encoders often fail to capture biologically meaningful and functionally relevant patterns. This project aims to develop a self-supervised bio-visual encoder that eﬀectively represents cellular morphology and perturbation eﬀects. By integrating state-of-the-art architectures (e.g., ViT, U-Net, DiNO) with tailored loss designs（或者其他training方面的tricks也可以）, the model will be validated on 我们自己构建的benchmark build from public HCS datasets such as the JUMP Cell Painting benchmark.
## 2. Benchmark
测试集：以CPJUMP1的1-4个plate为数据（注意一个数据有64个G所以你要思考一下如何可行），然后有4个指标（可以参考CPJUMP1）
训练集：
## 3. Experiment
### 3.1 Set up
有4-5个baseline
+ 不同loss function
+ 一些训练的tricks
### 3.2 Analysis
1. 分析在各种维度上的表现差异并画一个表格
2. 分析2-4 Tricks（及其组合），使用这个有什么理论依据，在实验上有什么增长、下降，原因分析
3. 
### 5. Conclusion
我们构建了一个怎样的benchmark，可以真实的体现对perturbations什么什么的效果；基于CPJUMP1的什么subset构建了训练集，采用xxx + xxx + xxx的训练策略可以让模型在benchmark上达到xxx，comparable to xxx（或者超过xxx encoder百分之多少）我希望这个工作可作为像xxx迈进的坚实一步。
