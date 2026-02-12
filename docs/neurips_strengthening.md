# NeurIPS “会被喷点”→ 方法与实验加固清单（W1–W5）

目标：把 SealedHistory/ProveTok 从“系统整合 + 工程规范”推到更像 **可泛化评测范式 + 可证伪安全审计**，并把每个质疑点转成可检验实验与可引用相关工作。

> 这份文件是写作与实验设计用的“作战地图”，不替代 `docs/plan.md` / `docs/experiment.md`。

---

## 0) 你现在已经有的“硬对照骨架”（不要浪费）

仓库里已对齐并实现了几类审稿人会点名的路线（对应你 W5 的诉求）：

- 动态/时间窗评测：LatestEval / LiveBench 风格（见 `EXP-035`）
- 污染统计检测：ConStat 风格（见 `EXP-034`）
- 污染可追踪标记：DyePack 风格（见 `EXP-036`）
- 训练数据抽取压力：Carlini/Nasr 风格（见 `EXP-037`）
- Judge 可靠性验证（避免“LLM-as-a-judge 无地基”）：`EXP-038`

这些东西在论文里要被写成“**对照路线**”，不是“我们也做了更多实验”。

---

## 1) 相关工作（按你 W1/W5 的质疑点组织）

### 1.1 不明文发布 / 受控发布（“为什么要 sealed release”）

- Jacovi et al., *Stop Uploading Test Data in Plain Text* (EMNLP 2023)  
  arXiv:2305.10160 — 给出“不要明文发布测试集”的务实策略（包括加密/受控发布等），可作为你动机的直接支撑。  
  https://arxiv.org/abs/2305.10160

### 1.2 动态 / 新鲜基准（“时间窗 vs 你 multi-seed sealed worlds”）

- Li et al., *LatestEval* — time-sensitive / dynamic test construction  
  arXiv:2312.12343 https://arxiv.org/abs/2312.12343
- *LiveBench* — live / continuously updated LLM benchmark（污染更难、但长期复现更难）  
  arXiv:2406.19314 https://arxiv.org/abs/2406.19314
- Jain et al., *LiveCodeBench* — 代码域持续收集、污染更难的评测范式  
  arXiv:2403.07974 https://arxiv.org/abs/2403.07974

### 1.3 变体/扰动式抗污染（“你不是‘把最佳实践拼起来’，你在 generalize 这一类思想”）

- *VarBench* — 通过变量扰动/范围化来缓解污染与作弊（与“多 seed 世界”高度同族）  
  arXiv:2406.17681 https://arxiv.org/abs/2406.17681

### 1.4 污染检测（“检测 ≠ 发布机制”这一分歧点要写清楚）

- Dekoninck et al., *ConStat* (NeurIPS 2024)  
  arXiv:2405.16281 https://arxiv.org/abs/2405.16281
- Zhang et al., *PaCoST* — paired-confidence significance testing for contamination detection  
  arXiv:2406.18326 https://arxiv.org/abs/2406.18326
- Shi et al., *Detecting Pretraining Data from Large Language Models*（Min-K% 系列）  
  arXiv:2310.16789 https://arxiv.org/abs/2310.16789
- Zhang et al., *Min-K%++*（更强的 pretraining data detection）  
  arXiv:2404.02936 https://arxiv.org/abs/2404.02936

### 1.5 污染可追踪标记（“如果审稿人说：你怎么证明模型没看过？”）

- *DyePack* — 通过“可追踪标记”来检测/定位污染  
  arXiv:2505.23001 https://arxiv.org/abs/2505.23001

### 1.6 可提取记忆 / 抽取攻击（W2 的威胁模型地基）

- Carlini et al., *Extracting Training Data from Large Language Models*  
  arXiv:2012.07805 https://arxiv.org/abs/2012.07805
- Nasr et al., *Scalable Extraction of Training Data from (Production) Language Models*  
  arXiv:2311.17035 https://arxiv.org/abs/2311.17035

### 1.7 综述（写 related work / threat model 时“站得住”的大引用）

- *Benchmark Data Contamination of Large Language Models: A Survey*  
  arXiv:2406.04244 https://arxiv.org/abs/2406.04244

---

## 2) W1：把贡献从“工程整合”抬到“可泛化范式”

### 2.1 你需要显式写出的“范式定义”（建议 1 个定义 + 1 个命题）

把 SealedHistory 写成一个 **release protocol**，而不是一个具体数据集：

- 输入：原始记录集合 `R`（可含受限快照）与公开可分发的派生记录 `P`
- 输出：对每个 seed 产生公开世界 `P_s` 与私有 codebook `C_s`
- 目标：在固定威胁模型下，优化 `Utility(P_s) - λ · Leakage(P_s)`

命题可以很朴素，但要“可检验”：  
**多 seed 评测**把“对单一测试集的投机”转化为“对变换族的稳健泛化”，从而给出一个可操作的抗污染指标（跨 seed 方差/最坏值）。

### 2.2 你要避免的叙事坑

- 不要说“我们提供安全保证”，而要说“我们提供 **可证伪审计闭环**，并报告 Pareto 取舍”
- 不要把对照路线写成名单；要写成“它们优化哪个轴、牺牲哪个轴”，你补上哪个缺口

---

## 3) W2：威胁模型与安全性论证（写成“可打分”的结构）

### 3.1 先把攻击者分层（论文里用一个表）

建议至少列三类（审稿人会问的就是这些）：

1) **公开发布攻击者**：只拿到 `P_s`，知道 transformation family，但不知道 `C_s`  
2) **黑盒查询攻击者**：同上 + 有预算 `B` 可查询被测模型/评测 API  
3) **白盒审计者**：持有 `C_s`，用于判定攻击是否成功（不等于把 `C_s` 给攻击者）

### 3.2 你必须明确的假设（否则会被喷“没威胁模型”）

- 攻击者是否知道 transformation family：**建议公开**（Kerckhoffs 原则），只隐藏 seed/key/codebook
- seed 分布是否公开：建议公开 seeds 集合（可复现），但不公开 codebook
- 允许的外部知识：允许攻击者访问 OpenAlex/S2 等公开图谱（否则不现实）

### 3.3 指标要从“直觉”变成“可量化”

最小集（每个都能变成一个图/表）：

- **Linkability / Re-identification**：给定 `P_s`，把条目链接回真实论文的 top-k 准确率
- **Term recovery / codebook recovery**：关键词映射恢复率（hit@k）与预算曲线
- **Extraction under budget**：Carlini/Nasr 风格的预算-成功率曲线
- **Utility invariance**：sealed vs raw 的排名一致性（Spearman/Kendall）与跨 seed 方差

---

## 4) W3/W4/W5：实验设计（把“会被喷点”变成可验收的 Exp）

### 4.1 W4（validity）最关键的两类实验（建议主文 1 张表 + 1 张图）

1) **能力测量不变性（measurement invariance）**  
   - 多模型（或多 agent）在 raw 与 sealed 上的排序一致性（Spearman/Kendall）
   - 报告：rank corr + “改变了哪些模型对比结论”

2) **Metadata-only/structure-only sanity**  
   - 只给 year/venue/graph/标签等，屏蔽文本性线索
   - 结论：如果还能高分 → 你的任务在测“坐标系偷懒”，不是测能力

> 你现在的 ablation 已经覆盖了“删 lexical sealing 泄漏飙升”；但 validity 需要“对模型排序是否稳定”的证据。

已在仓库里落地为可复现实验：
- `EXP-039`: 非 LLM（多 agent）raw↔sealed 排序不变性 + metadata/structure-only sanity
- `EXP-040`: LLM proposer（temperature=0）在 raw/sealed/structure_only/metadata_only 视图下的效用与维度退化对照

### 4.2 W5（baseline）建议的“刀刀见血”对照表

把 baselines 写成一个二维表（发布策略 × 风险控制方式）：

- 动态构造：LatestEval / LiveBench / LiveCodeBench
- 检测：ConStat / PaCoST / Min-K% 系列
- 标记追踪：DyePack
- 发布策略消融：只封 ID / 只封 lexical / 只封结构 / 只封答案 / 纯加密（受控评测）/ 你们的 full sealing

### 4.3 论文呈现（避免 W3 “proposal/草稿感”）

- 所有数字必须来自“可复现实验产物”（路径 + schema），主文只引用 key artifacts
- 把占位符（XX/YY/Δ）全部替换为：`均值±std`、CI、p 值、效应量（d）
- 每个核心结论至少有一个“反例/限制”图（例如 budget 曲线显示中预算就能抽取）
