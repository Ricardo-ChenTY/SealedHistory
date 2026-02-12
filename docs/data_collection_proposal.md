# 数据采集 Proposal（plan.md v1.0 实现导向）

**日期**：2026-02-04  
**项目**：SealedHistory / ProveTok  
**目标**：在不分发论文全文、不引入可逆指纹的前提下，构建可复现、可审计、可发布的两条 micro-history tracks（A 视觉表征 / B 序列建模）的结构化 paper records、依赖图与 sealed worlds，并提供泄漏审计材料与 QA 报告。

---

## 1. 目标与非目标

### 1.1 目标（与 plan.md 一致）
1) Track A/B 各产出两层版本：**Core（120 篇，强自动审计）+ Extended（2000+ 篇，覆盖/鲁棒性/泄漏审计）**（可复现选取过程与剔除理由）  
2) 发布结构化 records（paraphrase + 结构化对象），支持 L1/L2/L3 sealing  
3) 构建依赖图并与外部引文边集合对齐，可量化覆盖率/一致率  
4) 数据质量可量化：自动 QA + 置信度分（confidence score）+ record 级质量分  
5) 单点风险兜底：平台不可用时可从快照/替代来源复现

### 1.2 非目标
- 不发布论文全文（PDF/TeX）与可逆的原文对齐片段  
- 不依赖不可复现的网页爬虫作为主路径  
- 不做 unlearning

---

## 2. 数据来源与合规策略

### 2.1 主通路：学术元数据与引用图谱
1) **Semantic Scholar API（S2）**：works 元数据、引用边、DOI/arXiv/abstract、openAccessPdf（主图谱）  
2) **OpenAlex（CC0）**：仅保留离线兼容入口（legacy fixtures）  
3) **OpenCitations（可选，CC0）**：DOI-to-DOI 引文边第三来源校验

### 2.2 全文可访问性（仅内部解析）
硬约束：入 Track 的每篇论文至少满足一种公开可访问全文条件：
- arXiv PDF/TeX（优先）
- 或作者公开 PDF（明确 URL，记录时间戳与 sha256）

对外发布原则：**仅发布结构化衍生数据**；不分发全文；链接指回原站（如需要）。

---

## 3. 数据模型与发布边界

### 3.1 Public record（发布对象）
Public record 字段与 JSON Schema：
- 代码定义：`provetok/src/provetok/data/schema_v2.py`
- JSON Schema：`docs/schemas/paper_record_v2.schema.json`

发布约束（强制）：
- 文本字段必须 paraphrase，限制长度
- 禁止输出 URL/DOI/arXiv id/作者/年份/会议名等可检索指纹
- 禁止输出可检索的长 n-gram 原文

### 3.2 Private（内部保留，严禁发布）
- `paper_id ↔ openalex/doi/arxiv/s2` 映射（leaderboard/审计/回溯用）
- seed codebook 映射（包含真实术语）
- raw snapshots（可能包含可识别元信息）
- 全文缓存（PDF/TeX/source）

---

## 4. 采集与构建流程（ETL，Phase 0–5）

### Phase 0：配置冻结（可复现入口）
- 固定 track 范围（concept/keyword/venue/year）
- 固定输出版本号 `dataset_version`
- 固定阈值（topic_coverage_k、edge coverage threshold、QA pass rates）

对应仓库配置：`provetok/configs/dataset.yaml`

### Phase 1：候选 works 抓取（S2 主、OpenAlex legacy 兼容、OC 交叉）
输出：
- `private/raw_snapshots/s2/works_track_{A,B}.jsonl`
- `private/raw_snapshots/s2/requests_track_{A,B}.jsonl`
- `private/raw_snapshots/openalex/works_track_{A,B}.jsonl`（legacy 兼容，可选）
- `private/raw_snapshots/opencitations/*.jsonl`（可选）

### Phase 2：引用图构建与对齐
输出：
- `public/dependency_graph_core.edgelist`
- `public/dependency_graph_extended.edgelist`
- `public/dataset_manifest.json`：记录边覆盖率/一致率统计

### Phase 3：Track 选取（Selection Protocol）
**自动化排序（可复现）**
- 对候选图计算中心性信号（如 PageRank/入度等）
- topic 覆盖约束（基于 S2 fieldsOfStudy 或 taxonomy）

**可选：手工 include/exclude（默认关闭）**
- 允许少量 include/exclude，但每次必须写入 `public/selection_log_{core,extended}.jsonl`
- 统一字段：reason_tag、evidence（不包含可逆标识符）

输出：
- `private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl`
- `public/selection_log_core.jsonl`
- `public/selection_log_extended.jsonl`

### Phase 4：全文可访问性与全文缓存（仅内部）
策略：
- 若有 arXiv id：缓存 PDF + source
- 否则：仅使用明确的作者公开 PDF URL（或覆盖表）

输出（Private）：
- `private/fulltext_cache/arxiv/**`
- `private/fulltext_cache/pdfs/**`
- `private/fulltext_index_{core,extended}.jsonl`（含 URL、ts、sha256、失败原因）

### Phase 5：结构化 record 生成（抽取/标注）
目标字段：background、mechanism_tags、formula_graph、protocol、results、dependencies

人机协作建议：
- LLM/工具生成初稿（必须受 schema 约束）
- 不做人工复核；以自动 QA/一致性/置信度信号替代（如需仅内部抽样复核，但不作为验收门槛）

输出：
- `public/track_{A,B}_core_records.jsonl`
- `public/track_{A,B}_extended_records.jsonl`
- `public/taxonomy.json`
- `private/track_{A,B}_{core,extended}_records.internal.jsonl`（含内部映射字段）

---

## 5. QA 与一致性验证（全量必跑）

自动化检查（对应 `plan.md` §8）：
1) schema_validate（JSON Schema + 长度限制 + 禁用模式）
2) protocol_result_consistency（缺失标记 incomplete）
3) dependency_graph_check（DAG、连通性、边覆盖率）
4) taxonomy_coverage_check（标签分布，避免大量落入 other）

输出：
- `public/qa_report_core.jsonl`
- `public/qa_report_extended.jsonl`
- `public/dataset_manifest.json`（汇总统计与阈值对比）

（不做 IAA）：
- 以自动 QA 汇总替代（schema pass、禁用模式命中率、依赖图问题、taxonomy 分布等）

---

## 6. SDG 与 sealed worlds（多 seed）

每个 seed：
- 对 public records 施加 L1/L2/L3（按 config）
- 输出 `public/sealed_worlds/{seed}/{core,extended}/records.jsonl` 与 `manifest.json`
- 将 codebook 映射写入 private（严禁发布）

输出：
- `public/sdg_configs/`
- `public/sealed_worlds/{seed}/...`
- `private/mapping_key/seed_{seed}.codebook.json`

---

## 7. 复现与存储策略

### 7.1 可复现原则
- 所有抓取记录：query、时间戳、分页、响应 sha256
- selection 可从 raw snapshots + selection_log 复现
- release 必须附带 `dataset_manifest.json`（版本、hash、统计摘要、已知问题）

### 7.2 存储建议
- raw snapshots / fulltext：内部对象存储或压缩归档（Private）
- public records/sealed worlds：HF Datasets/Zenodo/git-lfs（团队选择）

---

## 8. 风险与兜底

1) 平台不可用/限流：保留 raw snapshots；必要时降低调用速率，或切换替代来源  
2) 全文不可得：硬约束剔除并写 `selection_log_{core,extended}.jsonl`（保证“数据一定能有”）  
3) 版权/发布风险：不发布全文；不发布 codebook 映射；不发布可检索长原文  
4) 抽取质量参差：schema + QA 全量跑；以自动一致性/置信度信号替代人工双标；PWC 对照仅触发 QA issue 统计

---

## 9. 验收标准（Acceptance Criteria）
1) Track A/B：Core = 120 篇 records；Extended ≥ 2000 篇 records（目标；若短缺在 manifest 中报告原因与实际数量）  
2) 100% records 通过 schema 校验；≥95% 通过关键一致性检查  
3) 依赖图边覆盖率达到阈值，并在 manifest 中报告  
4) 生成 ≥M 个公开 seeds 的 sealed worlds 且可复现  
5) public 包含 manifest、hash、统计摘要与已知问题

---

## 10. 对应仓库命令（实现入口）

```bash
# 生成/导出数据集（legacy 或 online，取决于 dataset.yaml 的 record_build.mode）
provetok dataset build --config provetok/configs/dataset.yaml --track both
```

产物目录：
- Public：`provetok/data/exports/{dataset_version}/public/`
- Private：`provetok/data/exports/{dataset_version}/private/`
