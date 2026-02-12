# 采集清单（可执行 checklist）

本文档把 `plan.md` 的 Phase 0–5 翻译成**可以照单执行**的采集清单（含命令/产物路径/日志哈希/验收/兜底）。

> 说明：仓库实现提供两条路径：  
> - **Legacy（离线可跑）**：导出本地样例数据（用于 demo/测试）  
> - **Online（联网）**：S2-first + selection +（可选）全文缓存 + v2 record 生成（用于正式采集）

---

## A. 环境准备（一次性）

### A1. 创建 venv + 安装依赖（推荐）
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r provetok/requirements.txt
.venv/bin/python -m pip install -e provetok
```

### A2. 配置文件与模板
- 主配置：`provetok/configs/dataset.yaml`
- 人工裁剪模板：`docs/templates/manual_decisions.jsonl`
- 作者公开 PDF 覆盖表：`docs/templates/author_pdf_overrides.yaml`

### A3. 环境变量（online 模式）
- `S2_API_KEY`：可选（提高 Semantic Scholar 额度）
- `LLM_API_KEY`：若 `record_build.mode=llm`（生成 v2 record）
- `LLM_API_BASE`：可选（默认 DeepSeek OpenAI-compatible）

---

## B. Phase 0：配置冻结（C0）

### C0-01 固化 dataset_version 与输出目录
- 输入：`provetok/configs/dataset.yaml`
- 输出根目录（默认）：`provetok/data/exports/{dataset_version}/`
- 验收：构建后 `public/dataset_manifest.json` 存在且包含 config 与 artifact hashes

---

## C. Phase 1：候选 works 抓取（C1，仅 online）

### C1-01 S2 works snapshot
- 操作：`provetok dataset build --config provetok/configs/dataset.yaml --track both`
- 输出（Private）：
  - `private/raw_snapshots/s2/works_track_{A,B}.jsonl`
  - `private/raw_snapshots/s2/requests_track_{A,B}.jsonl`
- 需要记录：请求参数 + `response_sha256`
- 验收：works snapshot 行数 > 0，字段齐全（paperId/title/year/references）

### C1-02 Legacy OpenAlex 兼容快照（可选）
- 输出（Private）：`private/raw_snapshots/openalex/works_track_{A,B}.jsonl`
- 用途：仅用于历史离线 fixture 兼容，不再作为在线主采集源

### C1-03 OpenCitations（可选）
- 输出（Private）：`private/raw_snapshots/opencitations/*.jsonl`
- 验收：至少对入选 DOI 子集可返回

---

## D. Phase 2：引用图构建与对齐（C2）

### C2-01 输出依赖边图
- 输出（Public）：
  - `public/dependency_graph_core.edgelist`
  - `public/dependency_graph_extended.edgelist`
- 验收：非空 + DAG（无环/无自依赖）

---

## E. Phase 3：Track 选取（C3）

### C3-01 自动排序 + 覆盖约束
- 输出（Private）：`private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl`
- 输出（Public）：
  - `public/selection_log_core.jsonl`
  - `public/selection_log_extended.jsonl`
- 验收：每条 track 的 `core_size`/`extended_size` 目标以 `dataset.yaml` 为准；若短缺必须在 manifest/日志中可解释

### C3-02 人工裁剪（可选）
- 输入：复制 `docs/templates/manual_decisions.jsonl` 到自定义路径，并在 `dataset.yaml` 配 `selection.manual_decisions_file`
- 验收：selection_log 对 include/exclude 有 reason_tag/evidence/paper_key；reviewer_id 允许为匿名化标注者ID（如 `r1`）

---

## F. Phase 4：全文可得性与缓存（C4，仅内部）

硬约束：入 Track 每篇论文必须满足：
- arXiv PDF/TeX 可下载，或
- 作者公开 PDF 可下载

### C4-01 arXiv 下载（有 arxiv_id 时）
- 输出（Private）：
  - `private/fulltext_cache/arxiv/{arxiv_id}/{arxiv_id}.pdf`
  - `private/fulltext_cache/arxiv/{arxiv_id}/{arxiv_id}.source`
  - `private/fulltext_index_{core,extended}.jsonl`（记录 sha256、时间戳、失败原因）

### C4-02 作者公开 PDF 下载（兜底）
- 输入：S2 `openAccessPdf.url` 或 `author_pdf_overrides.yaml`
- 输出（Private）：
  - `private/fulltext_cache/pdfs/{sha256}.pdf`
  - `private/fulltext_index_{core,extended}.jsonl`

---

## G. Phase 5：结构化 record 生成（C5）

### C5-01 输出 v2 records（Public + Private）
- 输出（Public）：
  - `public/track_A_core_records.jsonl`, `public/track_B_core_records.jsonl`
  - `public/track_A_extended_records.jsonl`, `public/track_B_extended_records.jsonl`
  - `public/taxonomy.json`
- 输出（Private）：
  - `private/track_A_core_records.internal.jsonl`, `private/track_B_core_records.internal.jsonl`
  - `private/track_A_extended_records.internal.jsonl`, `private/track_B_extended_records.internal.jsonl`

---

## H. QA（C6，全量必跑）

### C6-01 生成 QA 报告
- 输出（Public）：
  - `public/qa_report_core.jsonl`
  - `public/qa_report_extended.jsonl`
- 验收：`dataset_manifest.json` 含 QA 汇总（schema pass、consistency pass、graph issues）

---

## I. SDG / sealed worlds（C7）

### C7-01 多 seed sealed worlds
- 输出（Public）：
  - `public/sealed_worlds/{seed}/{core,extended}/records.jsonl`
  - `public/sealed_worlds/{seed}/{core,extended}/manifest.json`
- 输出（Private）：
  - `private/mapping_key/seed_{seed}.codebook.json`（严禁发布）

---

## J. Attack suite（C8）

### C8-01 输出审计模板
- 输出（Public）：`public/attack_suite/README.md`
- 可选执行（需要私有 codebook + LLM）：参考 README 内命令

---

## K. 立即可跑（Legacy 离线 demo）

```bash
.venv/bin/provetok dataset build --config provetok/configs/dataset.yaml --track A
```

产物在：`provetok/data/exports/{dataset_version}/public/` 与 `.../private/`。
