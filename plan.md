下面是一份**可直接放进你论文/开源仓库的「数据收集与构建 Proposal」**（面向 SealedHistory / SDG），按顶会 benchmark 口径写：**目标清晰、来源可得、合规可发布、流程可复现、质量可审计、单点风险可兜底**。

---

# SealedHistory 数据收集与构建 Proposal（v1.0）

## 0. 执行摘要

本 proposal 旨在构建 SealedHistory 的两条 micro-history 轨道（视觉表征、序列建模）所需的**结构化 paper records**与**依赖图**，并将其作为 Sealed Domain Generator（SDG）的输入，生成多 seed 的 sealed worlds 以及可复现的泄漏审计材料。数据管线只依赖**公开可访问**的学术元数据与论文来源，并提供多源交叉校验与日志化审计，确保“数据一定能拿到”的工程确定性与长期可维护性。

---

## 1. 目标与非目标

### 1.1 目标（Goals）

1. **可复现地构建两条 Track（分层发布）**：每条 track 产出 **Core（120 篇，强自动审计）+ Extended（2000+ 篇，覆盖/鲁棒性/泄漏审计）** 两个版本，并给出可审计的选择过程与剔除理由日志。
2. **生成可发布的结构化 records**：不分发原文 PDF，发布可变换的结构化字段（支持 L1/L2/L3 sealing）。
3. **构建依赖图与元数据对齐**：PaperID 图与外部 citation 边集合对齐，并可量化覆盖率。
4. **数据质量可量化**：提供自动检查 + 置信度分（confidence score）+ record 级质量分。
5. **单点风险可兜底**：任何一个平台不可用时，仍能从替代来源完成数据构建。

### 1.2 非目标（Non-goals）

* 不做 “让模型遗忘历史” 的 unlearning。
* 不发布论文全文或可逆的原文对齐片段（避免版权/泄漏指纹）。
* 不依赖必须在线的网页爬虫作为核心路径（尽量用 API/数据快照/dump）。

---

## 2. 交付物（Deliverables）

### 2.1 公开交付（Public）

* `track_A_core_records.jsonl`, `track_B_core_records.jsonl`：Core 结构化 paper records（强审计主版本）。
* `track_A_extended_records.jsonl`, `track_B_extended_records.jsonl`：Extended 结构化 paper records（更大覆盖，用于鲁棒性与泄漏审计）。
* `taxonomy.json`：机制/任务/指标等标签体系（有限集合，带定义）。
* `dependency_graph_core.edgelist`, `dependency_graph_extended.edgelist`：PaperID DAG（匿名化）。
* `selection_log_core.jsonl`, `selection_log_extended.jsonl`：可复现选取过程日志（每次剔除/纳入的原因标签）。
* `qa_report_core.jsonl`, `qa_report_extended.jsonl`：每条 record 的自动检查结果、问题列表、质量分。
* `sdg_configs/`：SDG 参数配置（L1/L2/L3 开关与强度）。
* `sealed_worlds/{seed}/core/...`, `sealed_worlds/{seed}/extended/...`：多 seed 的 sealed worlds（仅 sealed token + 变换后结构化对象）。
* `attack_suite/`：泄漏审计脚本与报告模板（term recovery / time index / canonical-order test 等）。

### 2.2 内部交付（Private / Leaderboard）

* `mapping_key_{seed}`：每个 seed 的 codebook 映射 key（用于隐藏测试与泄漏审计；默认不公开或仅维护方持有）。
* `paper_id_map_track_{A,B}_{core,extended}.jsonl`：paper_id ↔ (openalex/doi/arxiv/s2/...) 映射（仅内部）。
* `fulltext_cache/**` + `fulltext_index_{core,extended}.jsonl`：全文缓存与索引（仅内部，用于可复现抓取与审计）。

---

## 3. 数据源与合规策略（Sources & Compliance）

> 原则：**主路径必须可程序化获取 + 许可清晰 + 可长期持续**；对外发布只包含我们生成的结构化衍生数据，不打包论文全文。

### 3.1 学术元数据与引用图谱（主通路）

1. **OpenAlex**

   * 用途：works 元数据、概念标签、引文边、venue 等；作为 track 构建的主图谱。
   * 合规：数据整体以 CC0 开放许可提供，可自由使用与分发。([OpenAlex][1])
2. **Semantic Scholar** Academic Graph API

   * 用途：交叉校验论文元数据、引文边、作者/venue 归一化；用于提高图谱准确性。([Semantic Scholar][2])
   * 合规与调用约束：遵循其 API 许可协议与 rate limit 等技术控制（不得规避）。([Semantic Scholar][3])
3. **OpenCitations**（可选第三源校验）

   * 用途：对 DOI-to-DOI 引文边做第三方交叉验证，减少单源错误。
   * 合规：OpenCitations 数据集以 CC0 提供。([OpenCitations][4])
   * 接口：提供统一 REST API 与数据分发。([OpenCitations][5])

### 3.2 论文可访问性（全文获取仅用于内部解析，不对外再分发）

1. **arXiv**

   * 获取元数据：OAI-PMH 接口（只暴露最新版本 item，适合可复现抓取）。([arXiv][6])
   * 元数据复用策略：arXiv 明确允许通过 OAI-PMH harvesting 元数据并在商业/非商业系统中复用，但全文下载链接应指回 arXiv。([arXiv][7])
   * 另备：arXiv API（便于按 query 拉取元数据）。([arXiv][8])

> **硬约束（可得性）**：进入 Track 的每篇论文必须满足至少一种“公开可访问全文”条件：arXiv PDF/TeX，或作者公开 PDF（需记录抓取时间戳与 URL）。这样才能最大化“数据一定能有”。

### 3.3 代码/结果对照（辅助，不作为唯一事实源）

1. **Papers with Code** 数据 dump（来自其 GitHub）

   * 用途：论文↔代码链接、任务/数据集/指标候选、结果表作为对照来源（加速候选生成与一致性检查）。
   * 获取方式：使用其公开 data dumps（避免依赖网站在线状态）。([GitHub][9])
2. **GitHub**

   * 用途：代码仓库抓取（repo URL、commit hash、README 中协议描述等），用于可选 real-mode 子集复现。

---

## 4. 数据模型（Schema）与结构化记录规范

### 4.1 设计原则

* **Schema-first**：先定义 JSON schema 与字段约束，再进行抽取/生成；所有 record 必须可通过校验。
* **可变换性**：核心内容使用结构化对象（formula graph、protocol、results buckets），确保 L2/L3 可以自动化变换，而不是手工洗稿。
* **可追溯性**：每个字段有 provenance 指针（page/section/table/commit），但不保存原文长段内容。
* **可发布性**：禁止输出可检索的长 n-gram 原文；所有文本为 paraphrase（长度上限 + 禁止项）。

### 4.2 paper record 字段（最小必需集）

每篇论文 (p) 生成一条 record（JSON）：

* `paper_id`：匿名 PaperID（稳定、不可逆）
* `track_id`：A 或 B
* `dependencies`：PaperID 列表（依赖 DAG）
* `background`：≤N 字 paraphrase
* `mechanism_tags`：来自 `taxonomy.json` 的标签集合
* `formula_graph`：符号/算子图（nodes/edges/ops）
* `protocol`：

  * `task_family_id`, `dataset_id`, `metric_id`
  * `compute_class`（small/medium/large 或更细）
  * `train_regime_class`（small/medium/large 或更细）
* `results`：

  * `primary_metric_rank`（相对排序）
  * `delta_over_baseline_bucket`（分箱）
  * `ablation_delta_buckets`（关键消融差值分箱）
  * `significance_flag`（可选）
* `provenance`：字段级来源指针（page/section/table id/commit hash）
* `qa`：自动检查输出（见 §8）

---

## 5. 数据管线总体架构（ETL）

### Phase 0：配置冻结（可复现入口）

* 定义 Track 的范围：概念/关键词/venue 范围、年份范围（可选）、最小论文数等。
* 固定输出版本号：`dataset_version`（语义化版本 + git commit）。
* 定义 ID 归一化策略：优先 DOI / arXiv_id；无 DOI 时采用 OpenAlex work_id + title hash 组合键。

### Phase 1：候选 works 集合抓取（OpenAlex 主、S2/OpenCitations 交叉）

* 从 OpenAlex 拉取候选 work 子集（按 concept、关键词、venue、年份 filter）。([OpenAlex][1])
* 为候选 work 生成 `raw_works_snapshot.jsonl`（包含抓取时间、API query、分页信息）。
* 用 Semantic Scholar API 交叉拉取关键字段（DOI/arXiv_id/venue/引用）。([Semantic Scholar][2])
* （可选）用 OpenCitations 对 DOI-to-DOI 引文边做第三方校验。([OpenCitations][5])

### Phase 2：引用图构建与对齐

* 建图：nodes=works，edges=citations（来源：OpenAlex；交叉源：S2/OpenCitations）。
* 记录三种边：

  * `edge_openalex`、`edge_s2`、`edge_opencitations`（可选）
* 计算边覆盖率与一致率：作为后续 selection 的质量信号。

### Phase 3：Track 选取（Selection Protocol，解决“挑故事”）

**自动化候选排序（可复现）**

* 对候选图计算：

  * 中心性（PageRank/betweenness 等）
  * 引用突增（burst / growth）
  * 跨社区桥接（community detection 后跨社区边）
* 覆盖约束：确保每条 track 覆盖 ≥K 个子主题（基于 OpenAlex concept 或自定义 taxonomy）。([OpenAlex][1])

**人工裁剪（可审计）**

* 允许少量人工规则剔除，但每次剔除必须写入 `selection_log_{core,extended}.jsonl`：

  * `reason_tag`：重复/纯工程/不可访问全文/无清晰实验协议/偏离 track
  * `reviewer_id`：内部标注者编号
  * `evidence`：触发规则的说明
* 输出最终 `track_A_papers.jsonl`, `track_B_papers.jsonl`（含 work_id、doi、arxiv_id、抓取时间戳）。

### Phase 4：论文可访问性与全文获取（仅内部解析）

* 对每篇入选论文执行“可访问性检查”：

  * arXiv：通过 OAI-PMH/API 定位并下载 PDF/TeX（内部存储）。([arXiv][6])
  * 非 arXiv：仅采集作者公开 PDF（记录 URL + 时间戳 + 哈希）。
* 合规原则：元数据可复用；对外只发布我们生成的结构化 records，不再分发全文；全文链接指回原站。([arXiv][7])

### Phase 5：结构化 record 生成（抽取/标注）

* **抽取目标**：background、机制标签、formula_graph、protocol、results、dependencies。
* **人机协作策略**：

  * LLM/工具生成初稿（但必须受 schema 约束）；
  * 人类标注者复核关键字段（机制标签、协议字段、关键结果分箱、关键消融）。
* 公式处理：优先从 TeX/LaTeX 或解析结果生成 `formula_graph`；若失败进入 `manual_formula_queue`，并记录失败率用于论文披露（封“不可规模化”喷点）。

---

## 6. 可选 real-mode 子集（不让 benchmark 依赖高门槛复现）

* fast-mode：环境回执由 record 的结构化结果确定性生成（benchmark 核心）。
* real-mode：仅选取少量子集用于现实对齐 sanity-check：

  * 代码开源（GitHub 可获取）、依赖可装、数据可下载、训练可轻量；
  * 复现失败不影响数据集主体发布，只影响“现实对齐”附录指标。

---

## 7. SDG 输入对齐与 sealed worlds 产出

### 7.1 SDG 输入要求

* record 必须包含 `mechanism_tags`、`formula_graph`、`protocol`、`results` 的结构化字段，否则 L2/L3 不可自动化。
* `dependencies` 需形成 DAG（或少量环需解释并在环境中处理）。

### 7.2 sealed world 生成（多 seed）

* 每个 seed：生成一份 codebook + 对 records 执行 L1/L2/L3（按 config）。
* 公开 seeds：用于复现实验与社区对比。
* 隐藏 seeds：用于长期 leaderboard，定期轮换，降低未来污染。

---

## 8. 数据质量控制（QA）与一致性验证

### 8.1 自动化检查（全量必跑）

1. `schema_validate`：JSON schema + 字段长度/禁用模式（禁止长原文 n-gram）。
2. `protocol_result_consistency`：dataset/metric 与 results 对齐；缺失标记 `incomplete=true`。
3. `dependency_graph_check`：DAG 性、连通性、边与外部引文边集合的覆盖率（OpenAlex/S2/OC）。
4. `taxonomy_coverage_check`：机制标签分布，避免大量落入 “other”。

输出 `qa_report_{core,extended}.jsonl`：每条 record 的问题列表与质量分。

### 8.2 置信度与一致性（无人工复核）

* 不做 IAA/人工双标；所有质量信号必须可自动计算、可复现、可审计。
* 对每条 record 生成自动 QA 信号（schema/禁用模式/一致性/依赖图），并给出可汇总的质量分。
* 定义 `confidence_score ∈ [0,1]`（确定性公式，基于 abstract 可用性、跨源命中、全文缓存命中等信号），用于从 Extended 派生 Core 的优先级，并在 manifest/QA 汇总中报告分布。

### 8.3 双通路数值对照（降低抄错风险）

* 关键结果优先来自论文表格/正文（provenance 标注）。
* Papers with Code dump 仅作对照与异常检测（不一致则标记为 QA issue 并在报告中统计）。([GitHub][9])

---

## 9. 版本管理、可复现与存储

### 9.1 可复现原则

* 所有抓取都记录：query、时间戳、分页、API 版本（若可得）、原始响应哈希。
* Track 选择输出可从 `raw_works_snapshot + selection_log` 复现。
* records 生成流程固定：schema + 规则 + 标注指南版本号（写入 `dataset_manifest.json`）。

### 9.2 存储策略（建议）

* 原始快照（raw）：对象存储/压缩归档（只内部）。
* 公开 records/sealed worlds：git-lfs 或数据集托管（如 HF Datasets / Zenodo，按你团队选择）。
* 每次 release 附带 `manifest`：版本、依赖、hash、统计摘要、已知问题列表。

---

## 10. 风险与兜底（保证“数据一定能有”）

1. **平台不可用/限流**

   * 主图谱用 OpenAlex（可 API + 可 snapshot），并交叉使用 S2；PWC 只用 GitHub dumps。([OpenAlex][1])
   * 调用遵循 S2 许可与 rate limit，不做规避；必要时申请 key 并本地缓存。([Semantic Scholar][3])

2. **论文不在 arXiv / 全文不可得**

   * 硬约束：入 Track 必须满足公开可访问全文条件（否则剔除并写日志）。
   * 这牺牲部分“历史完整性”，但换来“数据可获得性”与复现确定性。

3. **版权/发布风险**

   * 不发布 PDF/原文；只发布 paraphrase 的结构化 records + 变换后的 sealed 数据；元数据引用回源链接。([arXiv][7])

4. **抽取质量参差**

   * schema + 自动检查全量跑；以自动一致性/置信度信号替代人工双标；数值双通路对照。

---

## 11. 验收标准（Acceptance Criteria）

数据收集与构建完成需满足：

1. Track A/B：Core = 120 篇 records；Extended ≥ 2000 篇 records（目标；若短缺在 manifest 中报告原因与实际数量）；`selection_log` 记录纳入原因与选择配置。
2. 100% records 通过 schema 校验；≥95% records 通过关键一致性检查（其余进入修复队列）。
3. 依赖图边覆盖率达到预设阈值（例如：与 OpenAlex/S2 引文边重合率/一致率达标），并在 `manifest` 中报告。
4. 至少生成 ≥M 个公开 seeds 的 sealed worlds，并能用同一 SDG 配置一键复现。
5. 所有公开包包含 `manifest`、hash、统计摘要与已知问题列表。

---

如果你希望我把这份 proposal **直接改成可投递的“Data Appendix / Dataset Card”格式**（比如 NeurIPS/ICLR 常用的 dataset documentation 结构：Motivation、Composition、Collection Process、Preprocessing、Uses、Distribution、Maintenance、Ethical Considerations），我也可以在你下一条消息里把它重排成标准卡片文档。

[1]: https://docs.openalex.org/?utm_source=chatgpt.com "OpenAlex technical documentation: Overview"
[2]: https://www.semanticscholar.org/product/api?utm_source=chatgpt.com "Semantic Scholar Academic Graph API"
[3]: https://www.semanticscholar.org/product/api/license?utm_source=chatgpt.com "License Agreement | Semantic Scholar Academic Graph API"
[4]: https://opencitations.net/?utm_source=chatgpt.com "OpenCitations - Open Science Research Infrastructure"
[5]: https://api.opencitations.net/index/v1?utm_source=chatgpt.com "The unifying REST API for all the OpenCitations Indexes"
[6]: https://info.arxiv.org/help/oa/index.html?utm_source=chatgpt.com "Open Archives Initiative (OAI) - arXiv info"
[7]: https://info.arxiv.org/help/oa/metadataPolicy.html?utm_source=chatgpt.com "Policy for metadata harvesting - arXiv info"
[8]: https://info.arxiv.org/help/api/user-manual.html?utm_source=chatgpt.com "arXiv API User's Manual"
[9]: https://github.com/paperswithcode/paperswithcode-data?utm_source=chatgpt.com "The full dataset behind paperswithcode.com"
