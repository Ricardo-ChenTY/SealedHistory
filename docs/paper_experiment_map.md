# Paper Experiment Map (micro + scale)

目标：把 `docs/plan.md` 的主张写成论文时，**micro-history（可控机制验证）**与**scale（非 toy、主结论展示）**两套实验都进入文章，并且每个结论都能指到可复现 artifact。

---

## 0) 放置原则（避免“实验表塞满主文”的反效果）

- **主文只放“读者看得懂的结果表/图”**（2–4 个表图）。
- **完整实验矩阵/命令/产物路径**放 Appendix / Supplement（但仍然属于“文章的一部分”）。
- 文内任何数值结论都必须能链接到 `runs/` 下的机器可读产物（CSV/JSON/PNG）。

术语统一：
- `micro`: `provetok/data/{raw,sealed}/micro_history_{a,b}*`（对应 `EXP-011..020`）
- `scale`: public bundle `runs/EXP-031/public/*`（对应 `EXP-021..024` 的可公开复现输入；主结果来自 `EXP-022/023`；内部构建源目录为 `runs/EXP-021/dataset/*`）

---

## 1) 主文（Main Paper）建议的最小表图集（两套都出现）

### Table 1（主表，scale）
**用途**：主结论（utility vs leakage + baselines）  
**来源**：`runs/EXP-022/main_results.csv`（也有 `runs/EXP-022/main_results.md`）

建议在表注中固定写清楚：
- `n_raw=n_sealed=1500/track`（见 `runs/EXP-022/summary.json`）
- seeds = `[11,22,33]`
- attack 设置（例如 `attack_max_observed=200`，见 `runs/EXP-022/summary.json`）

### Figure 1（tradeoff 曲线，scale）
**用途**：展示 defense knob 的 utility-retention vs leakage tradeoff（knee point）  
**来源**：`runs/EXP-023/tradeoff_curve.png` + `runs/EXP-023/tradeoff_curve.json`

推荐配置（shipping decision）：
- `runs/EXP-033/recommended_config.json`（从 tradeoff curve 按固定阈值策略导出：推荐 `level=2`；黑盒 0 泄漏最小 level 为 `level=4`）

### Table 2（机制对照表，micro）
**用途**：解释性结果（同协议下 micro 的 Sealed vs Raw + 强基线）  
**来源**：`runs/EXP-011/main_results.csv`（也有 `runs/EXP-011/main_results.md`）

写作建议：
- Table 2 放在“Mechanism / Sanity-check”小节，明确它是**可控 micro**，不是主结论的最终规模。

### Figure 2（micro 消融）
**用途**：说明哪些模块在起作用（lexical/structure/numeric/manual logging）  
**来源**：`runs/EXP-013/ablation_results.csv`（也有 `runs/EXP-013/ablation_results.md`）

---

## 2) Appendix / Supplement（把“实验表”完整放进文章）

### Appendix A：Claim → Evidence → Artifact（1 页索引）
**用途**：审稿/复现时一眼定位证据  
**来源**：`docs/oral_artifact_index.md`（可直接作为 appendix）

### Appendix B：可复现实验矩阵（完整版）
**用途**：把每个 Claim/Oral 的命令、产物路径、PASS/FAIL 固化  
**来源**：`docs/experiment.md`（建议放 supplement；或抽取关键列重排成 Table A1）

### Appendix C：复现与工程合约（plan 的 CLAIM-001..009）
这些不是“结果”，但用来支撑“系统可发布/可审计/可复现”的论文叙事：
- CLI smoke / eval schema：`EXP-001/002` → `runs/EXP-001/eval_report_a.json`, `runs/EXP-002/eval_report_b.json`
- offline legacy export 全产物：`EXP-003` → `runs/exports/0.2.0-legacy/public/dataset_manifest.json`
- strict online 缺 key 早失败（expected-fail）：`EXP-004` → `runs/EXP-004/dataset_build_online.log`
- repo gate（no try/except）：`EXP-005` → `runs/EXP-005/gate_no_try.log`
- manual decisions 审计：`EXP-006` → `runs/EXP-006/check_manual.log`
- tests + offline-no-network：`EXP-007` → `runs/EXP-007/pytest.log`
- snapshot contract：`EXP-008` → `runs/EXP-008/snapshot_contract.log`
- attack suite 文档政策：`EXP-009` → `runs/EXP-009/attack_suite_policy.log`
- demo codebook 不外泄：`EXP-010` → `runs/EXP-010/demo_codebook_policy.log`

（建议把上述作为 Appendix C 的 checklist，避免主文跑题。）

### Appendix D：Threat Model 的边界证据（micro）
- 白盒 defense 前后：`EXP-016` → `runs/EXP-016/summary.json`
- 统计置信：`EXP-017` → `runs/EXP-017/summary.json`
- budget 曲线：`EXP-018` → `runs/EXP-018/budget_curves.json`, `runs/EXP-018/budget_curves.png`
- temporal holdout：`EXP-019` → `runs/EXP-019/summary.json`

### Appendix E：Human-eval（必须写成“风险披露”风格）
- 双评审 kappa：`EXP-020` → `runs/EXP-020/human_eval_report.json`
- alpha + 连续一致性诊断：`EXP-024` → `runs/EXP-024/human_eval_report.json`
- 协议：`docs/human_eval_protocol.md`

写作口径要点：
- 当前二分类一致性偏低（kappa/alpha），但连续评分相关性更高；大量样本落在阈值附近（解释为何 kappa 低）。
- 若要把 human-eval 升格为“强证据”，需要 `r3`（3+ raters）或严格校准/仲裁流程（见 `docs/human_eval_protocol.md`）。

---

## 3) 逐条映射（plan.md 的 Claim/Oral 在论文里怎么引用）

### Plan Claims（CLAIM-001..009）
把它们作为“System/Artifacts/Reproducibility”章节的子主张：
- CLAIM-001：`EXP-001/002`
- CLAIM-002：`EXP-003`
- CLAIM-003：`EXP-004`
- CLAIM-004：`EXP-005`
- CLAIM-005/006：`EXP-006/007`
- CLAIM-007：`EXP-008/007`
- CLAIM-008：`EXP-009`
- CLAIM-009：`EXP-010`

### Oral Addendum（ORAL-001..010, micro）
把它们作为“Evaluation（micro diagnostic）”章节：
- ORAL-001：`EXP-011`
- ORAL-002：`EXP-012`（产物在 `runs/EXP-011/attacks/*`）
- ORAL-003：`EXP-013`
- ORAL-004：`EXP-014`
- ORAL-005：`EXP-015`
- ORAL-006：`EXP-016`
- ORAL-007：`EXP-017`
- ORAL-008：`EXP-018`
- ORAL-009：`EXP-019`
- ORAL-010：`EXP-020`

### Scale vNext（非 toy 主结论）
把它们作为“Main Results（scale）”章节：
- scale dataset：`EXP-021`
- scale main table + stronger baselines：`EXP-022`
- defense knob sweep：`EXP-023`
- agreement report（用于 limitations）：`EXP-024`

---

## 4) 你现在“都要有”的最关键写作风险（以及解决方式）

风险：micro 与 scale 的证据混用导致 reviewer 质疑“主结论到底在哪个规模成立”。  
解决：
- 主文所有“主结论句子”只引用 scale（`EXP-022/023`）。
- micro 只用于解释机制、消融、边界案例（`EXP-011..020`），并且每个 micro 小节标题写明 “micro-history diagnostic”.

如果你希望 micro 的所有分析在 scale 也都复现（更强叙事），本仓库已新增并跑通（产物位于）：
- `EXP-025`：scale ablations（`runs/EXP-025/ablation_results.csv`）
- `EXP-026`：scale cross-domain summary（`runs/EXP-026/cross_domain_summary.json`）
- `EXP-027`：scale white-box defense（`runs/EXP-027/summary.json`）
- `EXP-028`：scale stats (CI/p/d)（`runs/EXP-028/summary.json`）
- `EXP-029`：scale budget curves（`runs/EXP-029/budget_curves.json`, `runs/EXP-029/budget_curves.png`）
- `EXP-030`：scale holdout generalization（`runs/EXP-030/summary.json`）

---

## 5) Micro vs Scale 配对表（确保“都要有”时不混乱）

| 分析块 | micro 证据 | scale 证据 | 建议放置 |
|---|---|---|---|
| 主结果表（Sealed vs Raw + baselines） | `EXP-011` | `EXP-022` | 主文放 scale；micro 放 sanity-check 小节/appendix |
| 攻击报告（black-box/white-box） | `EXP-012`（产物在 `runs/EXP-011/attacks/*`） | `EXP-022`（`runs/EXP-022/attacks/`） | 主文引用 scale；micro 可做可视化/解释补充 |
| 消融（lexical/structure/numeric + manual logging） | `EXP-013` | `EXP-025` | 主文可放 micro 解释；appendix 放 scale 复现以“更硬” |
| 跨域趋势（A/B） | `EXP-014` | `EXP-026` | Appendix（通常不占主文版面） |
| 强防御（defended vs raw） | `EXP-016` | `EXP-027`（另有曲线 `EXP-023`） | 主文放 scale（曲线/对照）；micro 作边界示例 |
| 统计置信（CI/p/d） | `EXP-017` | `EXP-028` | Appendix（或主文 1–2 句 + appendix 表） |
| 预算攻击曲线（budget sweep） | `EXP-018` | `EXP-029` | Failure-first / Limitations（scale 更有说服力） |
| 时间 holdout | `EXP-019` | `EXP-030` | Appendix（主文可一句话概括） |
| 人评一致性 | `EXP-020` | N/A（与数据规模无关） | Limitations（必须谨慎表述） |

---

## 6) 顶会提交流程里的“清单/复现声明”（把实验矩阵合理放进论文里）

核心点：**“实验表全部进文章里”不等于塞进主文**。更稳妥的做法是：
- 主文放 2–4 个最关键表图（读者可读、可复述）。
- Appendix / Supplement 放完整实验矩阵、命令、artifact paths（仍然是“文章的一部分”，也更符合顶会的复现/透明度要求）。

把仓库里的文档对应到常见要求（跨会议通用口径）：
- Paper checklist / reproducibility checklist:
  - 证据入口：`docs/experiment.md`（命令 + PASS/FAIL + 产物路径）
  - 复现声明：`docs/reproducibility_statement.md`
  - Claim→Artifact 索引：`docs/oral_artifact_index.md`
- Supplement 内容组织建议（便于 reviewer 快速核对）：
  - Appendix A: `docs/oral_artifact_index.md`（一页索引）
  - Appendix B: `docs/experiment.md`（完整矩阵）
  - Appendix C: `docs/claim_evidence.md`（逐条 Yes/No/Partial）
