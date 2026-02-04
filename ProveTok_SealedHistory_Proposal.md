# ProveTok / SealedHistory 详细Proposal（实现导向）
**日期**：2026-02-03  
**目标**：在不重新训练LLM的前提下，通过“同构密封域（Isomorphic Sealing）”解决AI论文演化模拟中的“开卷/后见之明（hindsight）”问题，并提供一个可复现的**长程研究智能体评测框架**（含密封域生成器、泄漏审计、单/多智能体评测环境、rubric评分与基线）。

---

## 0. 一句话摘要（TL;DR）
我们把真实AI论文微历史（micro-history）转成一个**结构同构但语义不可识别**的“密封世界”，用系统化的**泄漏审计**证明LLM无法通过记忆捷径作弊，然后在该世界内评测研究智能体（single/multi-agent）在预算约束下的“读论文→提方案→做实验→审稿通过→推进”的长程能力，并输出可诊断的rubric分解评分与Leakage–Utility帕累托曲线。

---

## 1. 背景与动机（Motivation）
### 1.1 为什么“AI论文发展模拟”会天然开卷
现代LLM在预训练阶段已吸收大量公开论文、博客与百科；如果直接让LLM模拟AI史（CNN→ResNet→Transformer…），模型可能通过**参数记忆**直接“猜中下一步”，而非基于你提供的证据推理。这会导致：
- 评测失真：看起来“很会做科研”，其实是背题。
- 社会模拟失真：多智能体互动变成“知道答案后的角色扮演”。

### 1.2 关键洞见：不让模型“忘记”，而让它“对不上号”
彻底unlearning几乎不现实；更可行的是把任务改造为：
- **即便模型记得真实AI史，也无法把记忆映射到当前世界**。
- 模型只能基于密封世界中提供的“论文记录、依赖图、实验反馈”推进。

---

## 2. 研究问题（Research Questions）
**RQ1（可测）**：在不同密封强度下（L1/L2/L3），LLM对真实AI史的“记忆捷径”能被压到多低？  
**RQ2（可测）**：在泄漏被压制时（通过审计），研究智能体仍能否基于推理实现长程进步（Utility不坍塌）？  
**RQ3（可测）**：同预算下，多智能体是否比单智能体更快达到里程碑、更可靠（更少胡编实验结论）？

---

## 3. 不可替代的贡献（Contributions，严格收敛为2点）
### C1：密封域生成器 SDG + 泄漏审计套件（Audit Suite）
- **SDG**：把真实微历史语料变成“同构但不可识别”的密封世界。
- **Audit**：用攻击测试 + 顺序似然偏置测试，量化“开卷泄漏”。

### C2：SealedHistory 长程研究智能体评测环境（Benchmark Env）
- 面向single/multi-agent，提供“读→提案→实验→审稿→推进”的最小可复现科研循环。
- 采用**rubric分解式评分**，输出可诊断的研究能力画像。

---

## 4. 威胁模型（Threat Model）
我们明确评测要防的是什么，以及不防什么：

### 4.1 攻击者能力（我们要防）
- 攻击者（LLM）看到密封文本后，试图：
  1) 还原真实术语/数据集/模型名（Term Recovery）
  2) 猜它在真实历史中的阶段（Phase/Time Index）
  3) 在不给论文证据的情况下，凭“记忆”预测下一突破（Next Milestone Shortcut）
  4) 对canonical顺序有异常偏好（Order Likelihood Bias）

### 4.2 不防的情况（明确边界）
- 不追求对**无限强白盒攻击**（能访问训练数据/梯度）安全。
- 不追求对**人工专家**在对照真实史时完全不可识别（人类可能通过逻辑也能猜到）。
- 我们要的是：对“使用现成LLM做研究智能体评测”这一常见设定，给出可复现、可量化的抗开卷协议。

---

## 5. 方法（Method）
### 5.1 输入表示：结构化Paper Records（先不碰PDF）
为了版权与可控性，先用结构化记录作为“论文对象”：

**PaperRecord（最小字段）**
- paper_id：唯一ID
- phase：early/mid/late（或数字bucket）
- background：问题与局限
- mechanism：核心机制（可含伪公式）
- experiment：实验设置、指标、消融
- results：主指标与相对改进（可归一）
- dependencies：依赖PaperID列表
- keywords：用于词汇密封的关键词（可后续自动抽取）

### 5.2 SDG：三层密封（L1/L2/L3）
**L1 词汇密封（Lexical Sealing）**
- 术语/模型名/数据集/机构/会议/年份/作者等全部替换为codebook伪token（seed可复现）。
- 依赖图保留（PaperID不变）。

**L2 结构密封（Structural Sealing）**
- 公式/机制描述做等价变形：符号重命名、代数重排、模板化改写。
- 目的：减少“凭公式形状识别是谁”。
- MVP先做轻量变换（占位），后续增强为多种transformation family。

**L3 数值密封（Numeric Sealing）**
- 绝对数值分箱/保序扰动：保留“谁比谁好、提升多少的趋势”，抹掉经典数字指纹。

### 5.3 泄漏审计（Leakage Audit Suite）
我们必须能量化“密封是否有效”：
- **Term Recovery Attack**：让attacker尝试恢复真实术语（top-k）。
- **Phase Prediction Attack**：猜early/mid/late。
- **Next Milestone Attack**：不给证据，只给提示，看能否“背题式预测”。
- **Canonical Order Likelihood Test**：对canonical顺序 vs shuffle顺序的偏好（ΔNLL/ΔPPL）。

**通过标准（建议）**
- 攻击成功率接近随机（含置信区间）。
- canonical偏置不显著。
- utility仍显著高于no-context baseline。

---

## 6. 评测环境（Benchmark Environment）
### 6.1 微历史（micro-history）范围（可控但做深）
建议先做两条 track，采用**分层发布**：每条 track 产出 **Core（120 篇，强自动审计、用于主实验）+ Extended（2000+ 篇，覆盖/鲁棒性/泄漏审计）**：
- Track A：视觉表征演化（vision representation evolution）
- Track B：序列建模演化（sequence modeling evolution）

> MVP：先做一个track（20篇）跑通全链路。

### 6.2 环境循环（最小可复现科研loop）
每个agent拥有预算B（实验次数/步骤/调用次数），动作：
1) Read(paper_id) 读取记录
2) Propose() 输出结构化“下一篇论文计划”
3) Experiment(proposal) 获取实验反馈（fast mode可查表；可选real mode跑小模型）
4) ReviewGate(proposal, results) 给出rubric评分，决定是否“接受论文”并推进state

### 6.3 Multi-agent不是故事会：它是实验变量
我们做single vs multi对照：
- 固定总预算B_total
- multi-agent内部如何分配预算、通信频率、共享记忆作为可控变量
- 指标看：里程碑速度、多样性、可靠性（claim一致率）

---

## 7. 评分体系（Rubric Scoring）
把“像不像真实历史”拆成可评分维度（MVP先做自动化，不完美但可跑）：

1) Problem shift：问题设定是否合理
2) Mechanism class：机制类别是否匹配下一阶段
3) Dependency accuracy：依赖PaperID是否合理（precision/recall）
4) Claim validity：主张是否与实验返回一致（防胡编）
5) Ablation discipline：是否包含关键消融并解释
6) Clarity：结构与可读性（可用LLM-judge + 小样本人审校准）

输出：总分 + 分项诊断（用于论文写作时讲“我们能诊断agent缺陷”）。

---

## 8. 实验设计（Experiments）
### 8.1 主图：Leakage–Utility 帕累托曲线
横轴Leakage（攻击成功率/顺序偏置），纵轴Utility（rubric总分/里程碑到达率）。
- unsealed：Leakage高，Utility虚高（作弊）
- L1：Leakage下降但仍可能识别
- L1+L2+L3：Leakage接近随机且Utility仍>no-context

### 8.2 主表：Single vs Multi-agent（同预算）
- milestone_reach：达到目标里程碑的比例
- steps_to_milestone：达到里程碑的步数/预算消耗
- claim_consistency：主张与实验一致率（越高越好）
- dependency_f1：依赖图合理性

### 8.3 基线（Baselines）
- No-context baseline：不给论文记录
- Unsealed baseline：不给密封（看虚高程度）
- Lexical-only：只L1
- Single-agent：单智能体
- Random/Heuristic：随机提案或简单规则提案（下界）

---

## 9. 里程碑与交付物（Deliverables）
### 9.1 MVP（1–2周内能落地的版本）
- SDG：L1实现 + L2/L3占位
- 数据：一个track 20篇结构化records
- Audit：term/phase攻击（先dummy也行） + order test接口
- Env：单agent dummy跑通循环
- Eval：rubric接口输出json + 一个可视化脚本（画Pareto）

### 9.2 v1（可写初稿的版本）
- L2增强（3–5类变换）
- L3真实保序分箱
- Attack用真实LLM调用（本地/云）
- multi-agent对照 + 报告主图主表

### 9.3 开源交付
- 代码仓库 + README
- configs默认参数
- 示例数据（密封版本）与生成脚本
- 复现实验脚本（scripts/）

---

## 10. 工程落地：推荐Repo结构（Cursor友好）
```text
provetok/
  README.md
  requirements.txt
  configs/
    default.yaml
    sdg.yaml
    audit.yaml
    env.yaml
  data/
    raw/
      micro_history_a.jsonl
    sealed/
  src/
    provetok/
      cli.py
      data/
      sdg/
      audit/
      env/
      agents/
      eval/
      utils/
  scripts/
    build_sealed_dataset.py
    run_audit.py
    run_benchmark.py
  tests/
    test_sdg.py
    test_audit.py
```

---

## 11. 配置文件建议（configs/default.yaml）
```yaml
project: provetok
seed: 42

sdg:
  enable_l1: true
  enable_l2: true
  enable_l3: true
  numeric_bins: 10

audit:
  run_term_recovery: true
  run_phase_pred: true
  run_order_bias: true
  attacker_model: "dummy"   # or "openai" / "local"

env:
  budget: 30
  fast_mode: true
  multi_agent: false
  n_agents: 1

eval:
  rubric_weights:
    problem_shift: 1.0
    mechanism_class: 1.0
    dependency: 1.0
    claim_validity: 2.0
    ablation: 1.0
    clarity: 0.5
```

---

## 12. 快速上手（你在Cursor里最短启动路径）
```bash
# 1) 创建环境
conda create -n provetok python=3.10 -y
conda activate provetok

# 2) 安装依赖
pip install -r requirements.txt

# 3) 生成密封数据 + 跑审计 + 跑模拟（统一入口）
python -m provetok.cli --in_jsonl data/raw/micro_history_a.jsonl --out_jsonl data/sealed/micro_history_a.sealed.jsonl --seed 42
```

---

## 13. 风险与应对（Reviewers会喷的点先封死）
1) **“你这不就是换个名字？”**  
→ L2/L3 + 攻击套件 + Pareto front 证明不是简单替换词。

2) **“密封太强导致推理失败。”**  
→ 做强度扫描，展示utility不坍塌，并与no-context对照。

3) **“全查表实验不真实。”**  
→ 提供real-mode子集（少量里程碑轻量训练）作为可信锚点。

4) **“multi-agent像故事会。”**  
→ 明确动作空间、预算、审稿机制、可复现实验对照。

---

## 14. 附录A：PaperRecord JSONL示例（最小）
```json
{"paper_id":"A_001","title":"Example Paper","phase":"early","background":"...","mechanism":"...","experiment":"...","results":{"metric_main":0.62,"delta_vs_prev":0.05},"dependencies":["A_000"],"keywords":["cnn","convolution","feature"]}
```

---

## 15. 附录B：第一周TODO清单（按优先级）
- [ ] 建repo树 + 统一cli入口（seal→audit→sim）
- [ ] 先写20篇micro-history结构化records（手工也行）
- [ ] L1 codebook + 替换跑通
- [ ] audit输出json（先dummy）
- [ ] env loop + rubric最小实现
- [ ] 输出一张简单Pareto图（哪怕先用随机数据）
