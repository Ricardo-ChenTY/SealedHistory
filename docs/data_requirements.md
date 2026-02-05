# 数据需求（plan.md v1.0 对齐）

本文档给出 SealedHistory / ProveTok 的**完整数据需求清单**：外部来源需要哪些 raw 数据、内部必须保存哪些快照与日志、最终需要发布哪些公开产物，以及哪些内容必须保持私有以满足合规与“防泄漏”要求。

> 核心原则：**Public 发布物只包含我们生成的结构化衍生数据**；不分发论文全文（PDF/TeX），不分发能反推出真实术语的 codebook 映射，不发布 DOI/arXiv/作者/年份等高可检索指纹。

---

## 0. 分层定义（强制）

### 0.1 Raw（原始数据）
来源平台的原始响应/文件快照，必须具备：
- 抓取时间戳（Unix 或 ISO8601）
- 请求参数（query/filter/fields/cursor 等）
- 原始响应哈希（sha256）
- 分页信息（cursor/page）

### 0.2 Derived（衍生数据）
由我们基于 raw 数据生成的结构化产物：records、依赖图、QA 报告、manifest、sealed worlds 等。

### 0.3 Public vs Private
- **Public（可发布）**：结构化 records、taxonomy、依赖图、QA、SDG configs、sealed worlds、attack suite 模板
- **Private（仅内部）**：paper_id ↔ 真实标识符映射、seed codebook 映射、raw snapshots、全文缓存（PDF/TeX）、（可选）人工复核材料

---

## 1. 外部来源数据（Raw，字段级要求）

### 1.1 OpenAlex（主通路：works 元数据 + 引文边）
**用途**：候选论文集合、概念标签、venue、引用关系（作为主图谱与 selection 输入）。

**必须采集的 work 字段（最低要求）**
- `id`（OpenAlex work id）
- `title`
- `publication_year`
- `doi`（若有）
- `ids.arxiv_id`（若有）
- `concepts[].id`（用于 topic 覆盖约束；可选：display_name/score）
- `cited_by_count`
- `referenced_works[]`（引用的 OpenAlex work id 列表；用于建图）

**可选但建议采集**
- `abstract_inverted_index`（用于 record 抽取兜底；若缺则用 S2 abstract）
- `host_venue` / `primary_location` / `open_access`（用于可访问性信号）

**必须保存的 raw 快照附带信息**
- query/filter/search/select/per-page/max_pages/cursor
- `response_sha256`、`response_len`

### 1.2 Semantic Scholar（S2）（交叉校验）
**用途**：补齐 DOI/arXiv、abstract、references；作为第二来源引文边（用于一致率/覆盖率统计）。

**必须采集字段（最低要求）**
- `paperId`
- `title`
- `abstract`（如 OpenAlex 无 abstract 时兜底）
- `year`, `venue`, `authors[].name`（用于归一化/对齐；注意：这些字段不得进入 Public record）
- `references[].paperId`
- `externalIds.DOI` / `externalIds.ArXiv`
- `openAccessPdf.url`（若存在，用作“作者公开 PDF”候选 URL）
- `url`（落地页；仅 Private）

**必须保存的 raw 快照附带信息**
- 请求 paper key / query、fields 参数、是否使用 API key
- `response_sha256`、`response_len`

### 1.3 OpenCitations（可选第三来源校验）
**用途**：DOI-to-DOI 引文边第三方校验，降低单源错误。

**必须采集字段（最低要求）**
- 给定 DOI 的 citations 列表（能恢复 “doi → doi” 边集合）

**必须保存的 raw 快照附带信息**
- 请求 DOI、`response_sha256`、`response_len`

### 1.4 arXiv（全文通路之一，仅内部解析）
**用途**：满足“可访问全文”硬约束；为 formula_graph 抽取提供更可靠来源。

**必须采集**
- 元数据（优先 OAI-PMH）：用于可复现定位（identifier、datestamp、arXiv id）
- 文件：PDF、TeX/source（内部缓存）

**必须保存的附带信息**
- 下载时间戳、最终 URL、文件 sha256、文件大小、失败原因

### 1.5 作者公开 PDF（全文兜底，仅内部解析）
**用途**：对非 arXiv 论文满足硬约束。

**必须采集**
- PDF URL（明确公开、可直接访问）
- 抓取时间戳、最终 URL、文件 sha256、文件大小

**约束**
- 不做“网页爬虫式搜索全文”作为主路径；仅采集明确给出的公开 PDF 链接（可通过覆盖表维护）。

### 1.6 Papers with Code dump（可选对照）
**用途**：任务/数据集/指标候选与结果对照（仅用于异常检测/复核触发，不作为唯一事实源）。

**建议采集**
- paper ↔ task/dataset/metric/repo 的关联
- results 表（用于对照检查）
- dump 版本/commit hash

### 1.7 GitHub（可选 real-mode 子集）
**用途**：构建“可跑子集”用于 sanity-check，不影响主数据集发布。

**建议采集**
- repo URL、commit hash、license/README 摘要
- 依赖安装信息（用于可跑性筛选）

---

## 2. 内部中间产物（Private，必须保存以满足“可复现/可审计”）

### 2.1 Raw snapshots（按来源分目录）
必须保存以下快照文件（JSONL 追加写）：
- `private/raw_snapshots/openalex/works_track_{A,B}.jsonl`（候选 works 明细）
- `private/raw_snapshots/openalex/requests_track_{A,B}.jsonl`（请求/响应元信息，含 hash）
- `private/raw_snapshots/s2/requests_track_{A,B}.jsonl`
- `private/raw_snapshots/opencitations/*.jsonl`（可选）

### 2.2 选取过程与映射（可审计）
- `public/selection_log_{core,extended}.jsonl`：每次 include/exclude 必须记录 reason_tag/evidence/paper_key（不包含可逆标识符；reviewer_id 允许为匿名化标注者ID，如 `r1`）
- `private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl`（至少包含）：
  - `paper_id`, `paper_key`, `openalex_id`, `doi`, `arxiv_id`, `s2_id`, `retrieved_at_unix`

### 2.3 全文缓存与索引（仅内部）
- `private/fulltext_cache/arxiv/{arxiv_id}/...`（PDF + source）
- `private/fulltext_cache/pdfs/{sha256}.pdf`（作者公开 PDF）
- `private/fulltext_index_{core,extended}.jsonl`：paper_id → (来源、ts、sha256、paths)

### 2.4 抽取/复核材料（建议）
- 抽取 prompt/version、抽取输出草稿（如存在）
- `manual_formula_queue`（公式图抽取失败队列）及失败率统计
- （可选）IAA 双标输入/输出与一致率统计（不作为默认验收门槛）

---

## 3. 公开发布产物（Public，必须产出）
对齐 `plan.md` §2.1：
- `public/track_A_core_records.jsonl`, `public/track_B_core_records.jsonl`
- `public/track_A_extended_records.jsonl`, `public/track_B_extended_records.jsonl`
- `public/taxonomy.json`
- `public/dependency_graph_core.edgelist`
- `public/dependency_graph_extended.edgelist`
- `public/selection_log_core.jsonl`
- `public/selection_log_extended.jsonl`
- `public/qa_report_core.jsonl`
- `public/qa_report_extended.jsonl`
- `public/sdg_configs/`
- `public/sealed_worlds/{seed}/{core,extended}/records.jsonl` + `public/sealed_worlds/{seed}/{core,extended}/manifest.json`
- `public/attack_suite/`（脚本与报告模板）
- `public/dataset_manifest.json`（版本、hash、统计摘要、已知问题）

---

## 4. 私有保留物（Private / Leaderboard，严禁发布）
对齐 `plan.md` §2.2：
- `private/mapping_key/seed_{seed}.codebook.json`（**包含真实术语映射**）
- `private/mapping_key/*paper_id_map*`（paper_id ↔ doi/arxiv/openalex/s2）
- `private/raw_snapshots/**`（可能包含可识别元数据）
- `private/fulltext_cache/**`（PDF/TeX）

---

## 5. v2 record（Public）字段级需求（最终 Schema）
公开 record 必须包含（与 `plan.md` §4.2 一致）：
- `paper_id`, `track_id`, `dependencies`
- `background`（paraphrase，长度上限，禁止 URL/DOI/arXiv 等模式）
- `mechanism_tags`（来自 taxonomy）
- `formula_graph`（nodes/edges/ops）
- `protocol`（task/dataset/metric/compute/train_regime）
- `results`（rank + 分桶 + 关键消融分桶）
- `provenance`（字段级来源指针，不含长原文）
- `qa`（自动检查摘要）

对应 JSON Schema：`docs/schemas/paper_record_v2.schema.json`
