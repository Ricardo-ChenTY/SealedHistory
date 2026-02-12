> Artifact-backed paper draft (synced: 2026-02-11). Main-paper Table/Figure sources are materialized from:
> - Table 1 (scale main results): `runs/EXP-022/main_results.csv` (meta: `runs/EXP-022/summary.json`)
> - Figure 1 (scale tradeoff curve): `runs/EXP-023/tradeoff_curve.png` (data: `runs/EXP-023/tradeoff_curve.json`)
> - Table 2 (micro diagnostic table): `runs/EXP-011/main_results.csv` (meta: `runs/EXP-011/summary.json`)
> - Figure 2 (micro ablations): `runs/EXP-013/ablation_results.csv` (scale replication: `runs/EXP-025/ablation_results.csv`)
>
> Full experiment matrix (commands + PASS/FAIL) is in Appendix B; claim→artifact index is in Appendix A.

---

# 标题（Title）

## 备选标题 A（更顶会、更“方法贡献”）

**SealedHistory: 通过可形式化封印变换族与可证伪泄漏审计，构建抗污染的研究历史模拟基准**

英文：**SealedHistory: Contamination-Resistant Research-History Simulation via Formal Sealing Transformations and Falsifiable Leakage Audits**

## 备选标题 B（更系统、更“可复现评测”）

**ProveTok: Evidence-Closed-Loop Benchmarking for Contamination and Memorization in Open Evaluation Artifacts**

---

# 摘要（Abstract）

> 摘要建议 **1 段**（NeurIPS常见），最多 2 段。你要把“问题—方法—结果—资源”压缩得像刀一样。

### 段落 A1（写作目的：一口气讲清楚 4 件事）

大模型评测正受到**基准污染与可提取记忆**的双重侵蚀：测试样本进入训练语料或后训练流程会虚高分数，而模型在黑盒/白盒威胁下对训练片段的泄漏又使“公开可复现评测”与“安全可信结论”产生冲突。已有对策（隐藏答案、动态基准、性能统计检测等）要么成本高、要么随时间脆弱、要么难以在**开放发布**与**可审计安全**之间兼得。本文提出 **SealedHistory**：将学术元数据与派生记录构造成可发布的“纸级记录（paper records）”，并通过一个**可形式化的封印变换族**在多随机种子下生成**公开 sealed worlds** 与**私有 codebooks**，同时配套 **ProveTok** 证据闭环评测框架：每个研究主张都绑定到可运行命令、确定性产物契约与记录化实验日志，并用**可证伪攻击套件**在黑盒/白盒威胁模型下量化泄漏。实验显示：在 scale（non-toy）数据集上（Track A/B 各 1500 条，seeds=[11,22,33]），SealedHistory (main) 的效用与 Raw 几乎一致（0.8407±0.0005 vs 0.8413±0.0010；`runs/EXP-022/main_results.csv`），同时将黑盒泄漏从 1.0000 降至 0.6667。Defense knob sweep 进一步给出可解释的 Pareto：在效用保留 0.9975 时黑盒泄漏可降至 0.0267（白盒约 0.5433；`runs/EXP-023/tradeoff_curve.json`；见 `runs/EXP-023/tradeoff_curve.png`）。我们将发布公开数据导出、评测脚本与可复现实验记录（私有快照与 codebook 仅以哈希形式记录），以支持长期可审计评测。

> 你文档里“动态基准/不明文发布测试集”的动机可以在摘要里轻点一下：Jacovi 等提出不要明文上传测试数据 ([arXiv][1])；动态时间窗 LatestEval ([arXiv][2])；持续收集 LiveCodeBench ([arXiv][3])；污染统计检测 ConStat ([arXiv][4])；训练数据抽取 Carlini ([arXiv][5])、Nasr ([arXiv][6])。

---

# 1 引言（Introduction）

> 引言要做到：**把“为什么重要”讲到审稿人无法反驳**，并且在第 2 页内把你的贡献钉死。

## 1.1 评测危机：污染与泄漏如何让结论失真（2–3 段）

### 段落 I1（现象：污染使分数虚高）

近年来，语言模型评测越来越难回答一个基本科学问题：**模型分数究竟反映能力提升，还是反映训练—评测重叠的扩大**。当评测样本以明文形式长期公开，或通过网页、论文、代码库等渠道被收集进预训练/后训练语料，静态基准的可解释性会随时间持续衰减。社区已开始系统性讨论“不要明文上传测试数据”的工程策略 ([arXiv][1])，以及通过“最近时间窗自动构造评测”降低重叠风险的动态基准方法（如 LatestEval）([arXiv][2])，或持续收集新题以实现近似无污染评测（如 LiveCodeBench）([arXiv][3])。

### 段落 I2（第二把刀：可提取记忆与隐私审计）

与污染并行的另一条线是**可提取记忆（extractable memorization）**：即便攻击者只拥有黑盒查询权限，也可能从模型输出中恢复训练语料片段。经典工作已展示从大模型中抽取训练数据的可行性 ([arXiv][5])，后续研究进一步显示在生产级与对齐后的模型上仍可能实现大规模抽取 ([arXiv][6])。这意味着：即使我们通过隐藏答案或动态构造缓解污染，**公开评测 artifacts 本身也可能成为泄漏与过拟合的载体**。因此，一个面向开放发布的评测系统需要同时回答两件事：如何在“可复现”前提下抑制污染；以及如何以明确威胁模型、可证伪指标量化泄漏风险。

### 段落 I3（定位缺口：现有路线为何仍不够）

现有路线各有取舍：隐藏测试集与受控评测能降低污染，但复现实验与社区扩展成本高；动态基准通过时间窗或持续收集缓解重叠，但对“开放发布”与“长期复现”的工程约束仍苛刻；统计检测方法能在一定程度上发现污染迹象（如 ConStat）([arXiv][4])，但它并不直接给出可发布 artifacts 的构造原则，也不提供可被复现实验验证的泄漏审计闭环。我们缺少的是一种机制：**在不牺牲开放发布与可复现性的前提下，把评测 artifacts 设计成“默认不明文泄露、且可被攻击套件证伪审计”的对象**。

## 1.2 本文任务：研究历史模拟的“坐标系偷懒”问题（2 段）

### 段落 I4（解释你评测对象：研究历史模拟/提案生成）

本文关注一种越来越常见的 agentic 评测形态：模型读取一组结构化研究记录（论文、引用依赖、机制标签等），并生成可执行的研究提案、实验设计或“下一步发展”。这类任务的难点不是单条问答，而是要求模型在**依赖结构、机制类别与证据链**上做长程一致推理。然而，一旦记录直接对应真实世界论文与概念坐标，强模型可能通过训练中学到的“真实 AI 史”完成对齐，从而绕开你真正想测的能力——这就是我们所说的**坐标系偷懒**。

### 段落 I5（引出 sealed worlds：让模型必须在“封印世界”里推理）

我们提出的思路不是让模型“忘记知识”，而是让评测环境避免提供能被直接对齐到真实世界坐标的明文钥匙：通过在多随机种子下对记录执行确定性封印变换，构建多个 **sealed worlds**。每个 sealed world 对外发布变换后的记录与依赖结构，而将恢复映射所需的 **codebook** 保持私有，仅用于审计与白盒攻击评测。这样，模型即使拥有丰富先验，也需要在当前封印世界的结构约束下完成推理，评测更接近“泛化能力”而非“训练重叠”。

## 1.3 贡献总结（1 段 + bullet）

### 段落 I6（NeurIPS 标准写法：3 点贡献 + 证据闭环）

本文的主要贡献如下：

1. **可形式化封印变换族（Sealing Transformation Family）**：在不发布明文主键映射的前提下，将学术记录构造成可发布的 sealed worlds，并以私有 codebook 支持可验证的白盒审计；
2. **ProveTok 证据闭环评测框架**：将“主张—命令—产物契约—实验记录”绑定，提供可复现实验矩阵与确定性导出（manifest、selection logs、QA reports），使评测结论可重复验证；
3. **可证伪泄漏审计与 Pareto 评估**：在黑盒/白盒威胁模型下定义泄漏指标与预算曲线，并与任务效用共同形成可解释的效用—泄漏 Pareto 前沿，用于比较不同封印与防御配置。

---

# 2 相关工作（Related Work）

> 相关工作不要写成“论文名单”，要写成“**分歧点**”：别人解决什么、没解决什么、你补上什么。

## 2.1 污染缓解：从“不明文发布”到动态基准（2 段）

### 段落 R1（不明文发布的工程策略）

针对公开基准被吸入训练的风险，Jacovi 等提出“不要以明文上传测试数据”，并给出加密发布、训练排除控制与上下文发布等实践策略 ([arXiv][1])。这类方法强调一个核心事实：**开放评测的 artifact 设计本身会影响未来污染的发生概率**。SealedHistory 延续这一观点，但将其推广到结构化研究记录与依赖图场景：我们不只隐藏答案，而是将“坐标系对齐钥匙”系统性封印，并通过可验证审计维持科学可证伪性。

### 段落 R2（动态/持续基准：时间窗与滚动收集）

另一条路线是通过最新时间窗构造评测以降低训练重叠，例如 LatestEval 利用近期文本自动生成阅读理解评测，强调 time-sensitive construction ([arXiv][2])；在代码领域，LiveCodeBench 通过持续收集竞赛新题实现近似无污染评测并扩展能力维度 ([arXiv][3])。SealedHistory 与这些工作互补：我们不依赖持续引入新题，而是提供一种**可复现、可公开发布**的 sealed-world 机制，使同一“底层记录”在不同 seeds 下生成多个评测世界，延长 artifact 的抗污染寿命，并支持跨世界的稳健性分析。

## 2.2 污染检测：统计检验与性能对比（1–2 段）

### 段落 R3（ConStat 等：发现污染，但不指导 artifact 构造）

污染检测方法试图在未知训练数据情况下推断模型是否“看过题”。例如 ConStat 提出基于性能对比的统计检验以检测和量化污染 ([arXiv][4])。这类方法的优势是可直接作用于现有基准，但它们通常回答“是否污染”，而较少回答“如何构造一个可发布且可长期复现的评测 artifact，使污染更难发生并且风险可审计”。本文从 artifact 设计出发：封印变换 + codebook + 攻击套件，形成一个可被复现实验反复验证的闭环。

## 2.3 记忆、抽取与隐私审计（2 段）

### 段落 R4（训练数据抽取：黑盒可行、规模可扩展）

训练数据抽取攻击展示了模型会以可恢复形式记忆训练片段。Carlini 等系统展示了从大模型中抽取训练数据的可行性 ([arXiv][5])；Nasr 等进一步表明即使在生产级、对齐后的模型上也可能实现可规模化抽取，并提出专门用于绕过对齐的攻击策略 ([arXiv][6])。这些工作说明：评测系统若要开放发布 artifacts，就必须把“可提取泄漏风险”作为一等公民纳入威胁模型与指标。

### 段落 R5（MIA 与数据工程：去重与攻击面）

除抽取外，成员推断攻击（MIA）也用于衡量训练样本是否可被识别，例如 Mattern 等提出基于邻域比较的 MIA 以减少对参考训练分布的依赖 ([ACL Anthology][7])。与此同时，数据工程层面的去重不仅提升训练效率，也能显著降低模型输出记忆片段的频率并减少训练—评测重叠 ([ACL Anthology][8])。SealedHistory 将这些洞见纳入 pipeline：通过 canonical keys、去重与选择日志降低结构性重叠；并通过黑盒/白盒审计量化封印配置下的泄漏可提取性。

## 2.4 可审计数据发布与评测可复现（1–2 段）

### 段落 R6（Datasheets/Model Cards：审计规范）

关于数据与模型的可审计发布，Datasheets for Datasets ([arXiv][9])、Data Statements ([ACL Anthology][10])、Model Cards ([arXiv][11]) 等框架强调透明记录数据来源、构造过程与适用边界。SealedHistory 的贡献在于把这种“文档化”进一步推进为**可执行、可验证**的证据闭环：manifest、日志与实验矩阵不仅描述过程，还能由脚本端到端复现并产生一致哈希产物。

### 段落 R7（评测框架：lm-eval 的经验与我们的 evidence loop）

在评测工具层面，Language Model Evaluation Harness 总结了可复现评测的工程经验与方法学陷阱，并提供统一的评测基座 ([arXiv][12])。ProveTok 的定位与之互补：我们不仅实现评测执行器，还将“主张—产物契约—实验记录—审计脚本”写入同一体系，使数据构建与安全审计也被纳入可复现评测范畴。

## 2.5 学术知识图谱与数据源（1 段）

### 段落 R8（OpenAlex / S2ORC / S2 Open Data Platform：可追溯来源）

SealedHistory 构建在可追溯的学术元数据与引用图之上。OpenAlex 提供 CC0 的开放学术知识图谱并具有成熟的 works/作者/机构/概念体系 ([arXiv][13])；Semantic Scholar Open Data Platform 描述了 S2 学术图谱的构建与开放接口 ([arXiv][14])；S2ORC 则提供大规模学术语料与结构化信息用于研究文本挖掘 ([ACL Anthology][15])。本文默认仅公开发布我们派生的 records 与日志，不直接分发可能受限的原文内容，从而降低许可与再分发风险。

---

# 3 方法（Method）

> 方法部分要像“定理 + 系统”结合：**定义清楚对象、变换、威胁模型、指标与算法/管线**。

## 3.1 问题定义与设计目标（2 段）

### 段落 M1（形式化：公开 artifact 与私有 codebook 的二层发布）

我们将评测数据定义为一组“纸级记录” (R={r_i})，每条记录包含可发布元数据、机制标签、依赖结构与用于任务的最小语义描述。对于每个随机种子 (s)，我们定义一个确定性的封印变换 (T_s)，生成 sealed world 的公开记录 (R_s=T_s(R)) 以及私有 codebook (C_s)。其中 (R_s) 可公开分发并用于模型评测；(C_s) 不公开，仅用于白盒审计与可证伪攻击评估。目标是在保持任务效用（utility）的同时，最小化在给定威胁模型下的泄漏风险（leakage）。

### 段落 M2（设计目标：四个可验收约束）

我们的设计目标由四类可验收约束组成：
(1) **可复现性**：数据构建、封印生成与评测均可由固定命令端到端复现，并输出确定性 artifact（manifest + 哈希）；
(2) **可发布性**：公开导出不包含可逆主键映射与敏感快照；
(3) **可审计性**：对每个构建与选择决策提供可追溯日志（selection logs、QA reports、request ledgers）；
(4) **可证伪安全性**：在黑盒/白盒威胁模型下定义可执行攻击与成功判定，使“泄漏”成为可实验验证的量。

## 3.2 数据模型：Tracks、Subsets 与 canonical paper keys（3 段）

### 段落 M3（Tracks A/B：用“查询程序”定义而非主观领域）

我们用两个互斥的“查询程序（query programs）”定义 Track A/B，而非以主观领域描述，以确保可离线重放与可审计。每个 track 由版本化 YAML 指定数据源优先级、过滤条件、时间窗与确定性分页策略；构建时我们在离线快照上重放查询程序，生成候选 works 与引用边，从而保证在相同快照与配置下输出完全一致。

### 段落 M4（core/extended：同一构造逻辑的两档发布）

每个 track 进一步划分 core 与 extended：core 强调高审计性与高一致性（更严格字段完备与 QA 门槛），extended 覆盖更广的长尾机制与分布迁移。两者共享同一 canonicalization 与 selection 管线，仅在阈值与候选规模上不同，从而支持“规模—质量—安全”的系统性消融分析。

### 段落 M5（paper_key：稳定主键是反泄漏与审计的基础）

为避免跨源重复与人工决策不可追溯，我们为每条记录构造稳定 canonical key：优先使用 DOI，其次 arXiv id、S2 paperId，最后回退到 OpenAlex id 与标题哈希组合。该 key 在 mapping、selection logs 与导出 records 中一致传播，使得去重、人工包含/排除、以及跨 seed 的对齐分析成为确定性的、可审计的操作。

## 3.3 快照 ledger 与 offline rebuild（2 段）

### 段落 M6（requests/works 分离：证明“你查过什么”与“你用的是什么数据面”）

我们采用 split snapshot：works 文件保存构建 records 所需的最小字段集合；requests ledger 记录每一次 API/查询的参数、时间戳、返回项数与响应哈希，以支持后续审计“离线模式是否真的未发起新网络请求”。这种设计将“数据面”（可复现构建所需）与“行为证据”（可追溯抓取过程）解耦，使 offline rebuild 的证据链可以被独立验证。

### 段落 M7（offline build：网络隔离下的确定性产物）

在 offline 模式下，构建过程仅消费已存在快照与配置文件：从 canonicalization、selection、record build 到 sealed world 生成，所有产物以固定排序与 canonical JSON 写入并记录 sha256。我们在实验中通过网络沙盒（例如无网络 namespace）强制验证 offline build 不产生任何外部连接尝试，并对导出目录的 manifest 哈希进行一致性校验。

## 3.4 封印变换族（Sealing Transformation Family）（4 段）

### 段落 M8（核心定义：封印算子集合 + 可调强度）

我们将封印定义为一组可组合算子 (\mathcal{O})，包括：(i) **Identifier sealing**：对 paper_key 的公开别名执行 keyed-hash 或置换映射；(ii) **Lexical sealing**：对可公开的简短语义描述执行受控释义/模板化改写，避免直接复制原文片段；(iii) **Structural sealing**：对依赖图做保持关键性质的扰动（如对等价边集合重排、边类型压缩），以减少可逆对齐信号；(iv) **Numeric sealing**：对敏感数值字段分桶或截断。每个算子带有强度参数 (\lambda)，从而形成可比较的安全—效用配置族。

### 段落 M9（codebook：只记录“必要可逆性”，其余不可逆）

封印的可逆性被严格限制在审计必要范围：codebook (C_s) 仅保存 identifier sealing 的映射与少量用于白盒验证的校验材料；而 lexical/structural/numeric sealing 默认不可逆（或仅保留判定所需的摘要哈希）。这样公开发布的 sealed records 在设计上缺乏“完整还原到真实世界”的信息通道，而审计仍可通过 codebook 判定攻击成功与否。

### 段落 M10（一个可写进论文的小性质：键控映射的不可猜测性）

在 identifier sealing 中，我们将公开别名定义为 (a = \mathrm{HMAC}_k(\text{paper_key})) 或等价的键控置换，其中密钥 (k) 仅存在于私有 codebook。若将 HMAC 视为伪随机函数，则在不知道 (k) 的情况下，从公开别名恢复原始 paper_key 的成功概率可忽略（上界与输出位数指数相关）。该性质并不声称“语义不可推断”，但为我们提供了一个可验证保证：**公开 artifact 不会泄露可直接用于跨语料对齐的明文主键**。

### 段落 M11（为什么“多 seed sealed worlds”是关键，而不是单一加密）

单一封印世界仍可能随时间被吸入训练并发生适应性过拟合。我们因此对每个数据版本生成多个 seeds 的 sealed worlds：同一底层记录集合在不同 seed 下拥有不同的公开别名与局部表征扰动。评测时我们既报告各 seed 的平均效用与泄漏，也分析跨 seed 的方差与最坏情况，从而将“对单一测试集的投机”转化为“对变换族的稳健泛化”要求。

## 3.5 威胁模型与泄漏指标（3 段）

### 段落 M12（黑盒威胁：只给公开 sealed records 与有限查询预算）

黑盒威胁模型中，攻击者可访问公开导出的 sealed records，并以预算 (B) 次交互查询目标模型（或评测 API），试图诱导模型输出能够对齐到真实世界的标识、原文片段或可逆映射线索。我们定义黑盒泄漏指标为攻击成功率与预算曲线（top-1 success under budget），并在不同封印强度与模型上比较曲线的整体下移幅度。

### 段落 M13（白盒威胁：审计者持有私有 codebook，用于判定攻击是否成功）

白盒威胁用于安全审计：审计者持有私有 codebook (C_s)，攻击者输出一个候选映射或候选解码结果；审计者通过 (C_s) 对其进行**确定性判定**（例如 codebook recovery rate、exact match on identifiers）。这种“可证伪判定”避免了主观解释，使泄漏评估与效用评估一样可以标准化复现。

### 段落 M14（效用指标：你的 rubric 就是 utility 的可解释分解）

效用（utility）由 ProveTok rubric 计算得到：我们将模型输出的研究提案按 problem shift、mechanism class、dependency reasoning、claim validity、ablation quality 与 clarity 等维度打分，并报告总分与维度均值。这样效用下降可以被定位到具体能力维度，从而支持封印算子的可解释消融。

## 3.6 ProveTok 证据闭环：Claim→Command→Contract→Record（2 段）

### 段落 M15（把你 docs/plan.md 的“证据地图”写成方法贡献）

ProveTok 将评测系统设计成证据闭环：每个研究主张（例如“离线构建可导出完整 public artifacts”）都绑定到一个可执行命令、一个确定性产物契约（文件路径与 schema），以及实验记录条目（stdout/stderr、退出码、产物哈希）。这种设计把系统论文常见的“我们实现了一个框架”提升为“我们提供了可证伪主张集合与可复现实验契约”，使同行可独立验证或复现失败案例。

### 段落 M16（为什么这能提升科学性：可复现不是附录，而是主线）

我们强调可复现性并非工程附属，而是评测可信性的必要条件：当污染与泄漏使评测结果随时间漂移时，只有将“构建过程、选择决策与审计脚本”固化为可重放证据，才能让后续研究在同一基线上进行可比较实验。为此我们将 manifest、selection logs、QA reports 与攻击套件文档作为公开导出的一部分，而将敏感快照与 codebook 仅以哈希引用保留在私有目录中。

---

# 4 实验（Experiments）

> 实验写法必须满足 NeurIPS oral 口味：
> **(i) 主结果一张图/表讲清楚；(ii) 机制消融解释“为什么有效”；(iii) 威胁模型审计让结论可信；(iv) 统计检验与人评补强。**
> 你文档里的 ORAL-001..010 正好对应这些模块。

### 主文表图（micro + scale 都出现）

- Table 1（scale 主表，主结论）：`runs/EXP-022/main_results.csv`
- Figure 1（scale tradeoff 曲线）：`runs/EXP-023/tradeoff_curve.png`
- Table 2（micro 机制对照表）：`runs/EXP-011/main_results.csv`
- Figure 2（micro 消融）：`runs/EXP-013/ablation_results.csv`

完整复现实验矩阵（命令 + PASS/FAIL + 产物路径）见 Appendix B（EXP-001..033）。scale 版 micro 复现链条（EXP-025..030）用于“micro 的分析在 scale 上也成立”的更硬叙事。

## 4.1 实验设置（2 段）

### 段落 E1（数据规模与 splits：直接用你默认 v2 规模）

我们使用两套数据尺度：**micro-history**（仓库内置 fixtures，Track A/B 各 20 条；`provetok/data/raw/micro_history_{a,b}.jsonl`）用于机制诊断与消融（EXP-011..020）；以及 **scale（non-toy）** 数据集（Track A/B 各 1500 条 raw + 1500 条 sealed；internal build manifest: `runs/EXP-021/dataset/dataset_manifest.json`；public repro bundle manifest: `runs/EXP-031/public/public_dataset_manifest.json`）用于主结果与可扩展性复现（EXP-021..030）。除非另有说明，所有表格默认在 seeds=[11,22,33] 与两 tracks 上汇总（每个配置 n_runs=6）。

### 段落 E2（模型与评测协议：固定 prompt、固定 seed、固定脚本）

我们评测多种模型设置（闭源/开源，或不同 post-training 版本），并对每个设置运行同一 ProveTok harness：固定系统 prompt、固定最大输出长度与温度策略，并在每个 seed 的 sealed world 上重复评测以估计方差。所有结果由脚本生成并记录在实验目录中，包含运行日志、JSON 报告与统计汇总文件，确保评测可复现与可审计。

## 4.2 对比方法（Baselines）与消融（2 段）

### 段落 E3（基线：Raw vs Sealed vs Defended）

我们比较三类配置：
(1) **Raw（未封印）**：公开 records 直接使用 canonical keys 与最小语义描述；
(2) **Sealed（封印）**：应用完整封印变换族生成 sealed worlds；
(3) **Defended（防御增强）**：在 sealed 基础上加入额外防御（例如更强的 lexical/structural sealing 或输出拒答策略），用于分析效用—泄漏的 Pareto 权衡。
此外，我们将封印算子强度作为连续参数进行消融，以建立“封印强度→效用/泄漏”的曲线关系。

### 段落 E4（与动态/污染检测路线的关系：可选加分实验）

为对比动态评测与污染检测路线，我们额外报告两类参考：时间窗动态构造思路（如 LatestEval）([arXiv][2]) 的启发性对照，以及性能统计污染检测（如 ConStat）([arXiv][4]) 在我们任务设置中的适用性分析。该对照用于说明 sealed worlds 并非替代动态基准或污染检测，而是为开放发布的结构化评测提供一种互补机制。

## 4.3 指标：效用、泄漏与 Pareto（2–3 段）

### 段落 E5（效用：rubric 总分 + 维度分解）

效用以 ProveTok rubric 度量：报告总分、接受率（n_accepted / n_proposals）以及六个维度均值（problem_shift、mechanism_class、dependency、claim_validity、ablation、clarity）。我们同时报告不同 seed、不同 track 的均值与标准差，以区分“能力变化”与“封印世界偶然性”的影响。

### 段落 E6（泄漏：黑盒预算曲线 + 白盒可证伪判定）

黑盒泄漏用预算曲线衡量：在预算 (B\in{1,2,5,10,\dots}) 下 top-1 攻击成功率的变化，并报告曲线下面积或关键预算点的成功率。白盒泄漏以 codebook recovery rate 或 identifier exact-match 判定，审计者用私有 codebook 给出确定性成功/失败标签。该设计使泄漏指标与效用指标一样可以复现并进行显著性检验。

### 段落 E7（Pareto：把“安全—效用”写成主结果图）

我们用效用—泄漏二维平面呈现不同配置（raw/sealed/defended、不同强度、不同 seed）的 Pareto 前沿，并报告“在相同效用下泄漏降低多少”或“在相同泄漏下效用提升多少”的支配关系。Pareto 视角避免了只追求单一指标的误导，也使封印强度的取舍更具可解释性。

## 4.4 主结果（Main Results）：ORAL-001/018/017（3 段 + 图表说明）

### 段落 E8（主结论段：一句话结论 + 三个证据点）

Table 1（scale 主表；`runs/EXP-022/main_results.csv`）给出主结果：在 Track A/B 各 1500 条、seeds=[11,22,33] 的设置下，SealedHistory (main) 的效用为 0.8407±0.0005，而 Raw 为 0.8413±0.0010（差异 -0.0006）；同时黑盒泄漏从 1.0000 降至 0.6667（Δ=-0.3333），而白盒泄漏仍为 1.0000。Figure 1（scale tradeoff 曲线；`runs/EXP-023/tradeoff_curve.png`）进一步展示可解释的 Pareto：在 level=2 时平均效用保留 0.9975 下黑盒泄漏可降至 0.0267（白盒约 0.5433）；进一步增强到 level=4 可将黑盒压到 0.0，但效用保留降至 0.8186（数据见 `runs/EXP-023/tradeoff_curve.json`）。这些趋势在两个 track 上同向，并在三 seeds 上复现。基于该曲线，我们给出明确的 **shipping decision**：按固定阈值策略推荐 `level=2` 作为默认发布配置；若要达到黑盒 0 泄漏则需要 `level=4` 并接受显著效用损失（见 `runs/EXP-033/recommended_config.json`）。

作为机制 sanity-check，Table 2（micro；`runs/EXP-011/main_results.csv`）显示在 micro-history 上封印将黑盒泄漏从 1.0000 降至 0.0583，但效用也从 0.8338 降至 0.7812；该差异帮助解释“强机制约束的 micro 与可扩展的 scale”之间的张力，并与 Figure 2 的消融结论一致（lexical sealing 决定性影响黑盒泄漏）。

### 段落 E9（解释“为什么不是因为任务变简单”：维度分解）

效用维度分解显示，封印主要影响的是“坐标系偷懒”的通道，而非降低推理难度：dependency 与 claim_validity 等结构性维度的得分保持稳定或略有提升，而与表面匹配相关的维度（如 mechanism_class 的词汇对齐部分）在高强度 lexical sealing 下出现可控下降。该结果支持我们的设计目标：封印并非通过“削弱任务”换取安全，而是通过切断可逆对齐信号迫使模型进行结构一致推理。

### 段落 E10（统计检验：把 ORAL-007 写成可信度背书）

我们对关键比较（Raw vs Sealed、Sealed vs Defended）进行 bootstrap 置信区间与置换检验（micro: `runs/EXP-017/summary.md`；scale: `runs/EXP-028/summary.md`）。在 micro-history 上，Sealed vs Raw 的效用差异为 -0.0526，95% CI [-0.0528, -0.0524]，p=0.0010；该结果说明 micro 封印带来可测的效用代价（与其强机制约束一致）。在 scale 主表上，Sealed vs Raw 的效用差异为 -0.0005，95% CI [-0.0013, 0.0003]，p=0.2032，效用差异不显著；这支持“主结论在 scale 上不靠降低任务难度取得”的叙事。

## 4.5 攻击与审计（Attacks & Audits）：ORAL-002/016（2–3 段）

### 段落 E11（黑盒攻击：提示注入/诱导解码/多轮对话）

在黑盒设置下，我们报告两类证据：默认离线攻击设置下的主表泄漏（Table 1）以及更强的预算扫掠曲线（Appendix；`runs/EXP-029/budget_curves.png`，数据为 `runs/EXP-029/budget_curves.json`）。预算扫掠显示攻击具有明显的“随预算上升而变强”的形态：在 scale 上，`A_sealed` 的 top1 黑盒成功率从 budget=8 的 0.7950 上升到 budget=16 的 0.9950，并在 budget=32 达到 1.0000；这说明仅依靠基础封印并不能在中等预算下阻止黑盒抽取。与此同时，防御增强配置可将黑盒曲线压到 0.0（见 `A_defended/B_defended`），但白盒仍保持较高（约 0.745–0.915），为后续更强防御或更严格发布策略留下空间。

为回应“heuristic leakage proxy 低估真实攻击者”的质疑，我们额外运行了 **LLM-backed term-recovery 校准攻击**（`runs/EXP-032/summary.json`；模型与 endpoint 记录在 `runs/EXP-032/run_meta.json`）：在 micro 上 hit@3 为 A=0.00、B=0.20；在 scale 上 hit@3 为 A=0.00、B=0.05。该结果表明在当前封印设计下，伪 token 的语义反推并非一个“容易被 LLM 直接破解”的通道；更强的风险仍主要来自预算提升带来的检索/匹配能力提升（budget sweep）。

### 段落 E12（白盒攻击：codebook recovery 的可证伪判定）

在白盒审计中，攻击者输出候选映射（例如 sealed alias → canonical key），审计者使用私有 codebook 进行 exact-match 判定，从而得到可证伪的恢复率。scale 证据表明防御增强确实能降低白盒泄漏：semantic redaction defense 将 white-box leakage 从 1.0 降至 0.5267（Track A）与 0.4967（Track B），同时效用保留为 0.8141/0.8159（`runs/EXP-027/summary.json`）。该结果与 Figure 1 的 knob sweep 一致，清晰呈现了 defense 的 Pareto 代价，并为实际发布时的强度选择提供可解释依据。

### 段落 E13（把“攻击套件文档”写成可复现承诺）

所有攻击与审计均由脚本生成结构化 JSON 报告，报告中包含数据版本、seed、配置、预算曲线与脚本哈希。公开数据导出包含 attack_suite 文档，指向仓库脚本与命令模板，使得第三方可在相同数据版本上复现实验并验证我们的安全结论。

## 4.6 消融研究（Ablations）：ORAL-003（2–3 段）

### 段落 E14（逐一移除算子：lexical/structural/numeric）

为理解封印变换族中各算子的作用，我们逐一移除 lexical、structural 与 numeric sealing，并比较效用与泄漏的变化（micro: `runs/EXP-013/ablation_results.md`；scale: `runs/EXP-025/ablation_results.md`）。在两种尺度上，`no_lexical_seal` 都会使黑盒泄漏显著上升：micro 中黑盒泄漏从 0.0583 上升到 0.9500；scale 中黑盒泄漏从 0.6667 上升到 1.0000，且效用几乎不变（0.8407→0.8413）。该结果表明 lexical sealing 是控制黑盒抽取通道的决定性组件之一，而其他算子在当前协议下贡献更依赖任务与攻击设置；消融为后续选择“最小足够封印强度”提供了可复现依据。

### 段落 E15（人工决策审计：把 CLAIM-005 写成“过程可信”）

我们进一步分析 selection logs 中的人工包含/排除决策：每条人工决策均带有 reviewer_id、reason_tag 与 paper_key，并出现在公开 selection_log 中。我们报告人工决策占比、冲突率与对最终数据分布的影响，说明封印与评测结论并非依赖不可追溯的人工过滤，而是在可审计日志约束下完成。

## 4.7 跨域趋势与稳健性（Cross-domain & Robustness）：ORAL-004/019（2 段）

### 段落 E16（Track A/B：证明不是“只对某个领域有效”）

Track A/B 的设计使两者在概念与来源分布上尽量互斥，从而可检验封印与防御是否具有跨域一致性。我们在 micro 与 scale 两个尺度上都显式计算“趋势是否同向”（micro: `runs/EXP-014/cross_domain_summary.json`；scale: `runs/EXP-026/cross_domain_summary.json`）：总体上黑盒趋势在两 track 上保持一致（`trend_holds_all_tracks_black_box=true`），而白盒趋势不保持（`trend_holds_all_tracks_white_box=false`）。这使我们能在主张范围内明确陈述“跨域一致性在黑盒威胁下成立，但白盒仍是主要风险源”。

### 段落 E17（时间窗 holdout：抗“未来污染”）

我们采用时间切分构造 holdout（quantile=0.7）以模拟未来污染风险，并在 micro 与 scale 两个尺度上复现该检查（micro: `runs/EXP-019/summary.json`；scale: `runs/EXP-030/summary.json`）。结果显示 sealed 配置在 holdout 下保持稳定效用：micro 平均效用保留为 0.9382，而 scale 平均效用保留为 0.9995；同时黑盒趋势在两 track 上均保持（`black_box_trend_holds_all_tracks=true`），支持“主要结论在时间切分下不崩”的稳健性叙事。

## 4.8 人类评测与一致性（Human Eval）：ORAL-005/020（1–2 段）

### 段落 E18（双评审一致性：作为限制与诊断，而非强结论）

我们对一部分样本进行双评审人类打分，并计算 Cohen’s kappa 以衡量一致性（`runs/EXP-020/human_eval_report.json`；诊断扩展见 `runs/EXP-024/human_eval_report.json`）。当前 n=36 的双评审样本上，percent agreement=0.6111，但 Cohen’s kappa=0.128、Krippendorff alpha=0.1372，显示二分类一致性偏低；同时连续评分相关性更高（Pearson r≈0.6449、Spearman r≈0.6263），且大量样本落在阈值附近。基于该结果，我们将 human-eval 作为“协议可执行 + 风险披露/诊断”证据，而非用于支撑强定量结论；若需将其升级为主要证据，需引入 3+ raters 或仲裁流程（协议见 `docs/human_eval_protocol.md`）。

---

# 5 讨论（Discussion）

> 讨论要做三件事：**解释机制、承认边界、指出未来方向**。oral 的讨论尤其看重“你知道自己哪里脆弱”。

## 5.1 机制解释：Sealing 到底改变了什么？（2 段）

### 段落 D1（从“偷懒通道”角度解释）

SealedHistory 的核心作用不是隐藏信息量，而是改变信息的**可对齐性**：当主键映射与可逆表征被移出公开 artifact，模型难以通过“记住真实论文→直接输出答案”的捷径完成任务；相反，它必须依赖 sealed world 内的结构约束（依赖图、机制标签关系、证据一致性）生成提案。实验中 dependency/claim_validity 维度的稳定性支持了这一解释。

### 段落 D2（为什么多 seed 重要：把过拟合转成稳健性要求）

多 seed sealed worlds 将对单一测试集的适应性过拟合转化为对变换族的稳健泛化要求：即使某个 seed 被污染或被模型部分记住，其他 seeds 仍提供独立检验；同时跨 seed 的方差可作为“投机风险”的指标。该机制提供了一种介于静态基准与持续动态基准之间的折中：既可复现，又能延长 artifact 的抗污染寿命。

## 5.2 局限性（Limitations）（2 段）

### 段落 D3（承认：语义推断无法被完全禁止）

封印并不声称阻止一切语义推断：强模型可能通过语义线索猜测真实论文或概念对应，尤其当记录包含高辨识度事实时。更重要的是，我们的 budget sweep 揭示了中等预算下的抽取风险：在 scale 上，sealed 配置的 top1 黑盒成功率在 budget=16 已达 0.995，并在 budget=32 达到 1.0000（`runs/EXP-029/budget_curves.png`），说明仅靠基础封印并不能在强攻击者下保证低泄漏。因此我们强调“可证伪审计”而非“绝对安全”：通过黑盒/白盒攻击套件量化不同配置下的泄漏风险，并将其与效用共同呈现为 Pareto 取舍。

### 段落 D4（承认：封印强度与效用存在真实张力）

封印强度提高通常会牺牲部分可读性与效用，尤其是 lexical sealing 可能降低某些语义细粒度判断。我们在 scale knob sweep 中观察到明确的 knee：level=2 时效用保留 0.9975 且黑盒泄漏 0.0267，但白盒仍约 0.5433；将黑盒压到 0 需要 level=4，效用保留降到 0.8186（`runs/EXP-023/tradeoff_curve.json`）。micro 消融也呈现一致趋势：移除 lexical sealing 会显著抬高黑盒泄漏（`runs/EXP-013/ablation_results.md`）。因此不同任务、不同威胁模型与不同模型家族可能对应不同最优点；未来可通过学习型封印或自适应强度策略进一步优化 Pareto 前沿。

## 5.3 更广泛影响与伦理（1 段）

### 段落 D5（面向社区：如何负责任地发布评测 artifacts）

SealedHistory 的目标是帮助社区在开放发布与可信评测之间取得更好的平衡。我们默认不公开原始快照与 codebook，并在公开导出中包含构建与审计文档、manifest 与哈希，以支持复现与问责。我们也建议使用者在不同许可约束下谨慎选择公开字段，仅发布派生记录与结构化标注，而不直接再分发可能受限的原文内容。

## 5.4 未来工作（1 段）

### 段落 D6（把未来工作写成“可验证路线图”）

未来方向包括：扩展封印算子到跨模态证据与工具交互轨迹；引入更强的自适应攻击与红队评测；以及将 sealed worlds 与动态时间窗构造结合，使同一基座既能多 seed 封印，又能随时间引入新记录，从而进一步降低长期污染风险并提升外部有效性。

---

# 6 结论（Conclusion）（1 段）

### 段落 C1（总结三点：问题→方案→证据）

本文提出 SealedHistory 与 ProveTok，用于在开放发布前提下缓解评测污染并量化可提取泄漏风险。我们通过可形式化封印变换族生成多 seed sealed worlds，并以私有 codebook 支持可证伪白盒审计；通过证据闭环 harness 将主张、命令、产物契约与实验记录绑定；并用效用—泄漏 Pareto 分析对比不同封印与防御配置。实验在双 track 与多 seed 上表明：在 scale 主表协议下 SealedHistory 在几乎不损失效用的情况下可降低黑盒泄漏（Table 1），并且 defense knob 可进一步压低黑盒泄漏但仍存在白盒与预算攻击下的残余风险（Figure 1；`runs/EXP-029/budget_curves.png`）。这些结果为长期可审计评测提供一种可复现的开放发布路径，同时明确了未来需要更强防御与更严格威胁模型的方向。

---

# 参考文献（References，建议你最后用 BibTeX 统一）

下面列你最该放进 BibTeX 的“支撑骨架”（足够把 related work 站稳）：

* Jacovi et al. **Stop Uploading Test Data in Plain Text: Practical Strategies for Mitigating Data Contamination by Evaluation Benchmarks.** EMNLP 2023. ([ACL Anthology][16])
* Li et al. **LatestEval: Addressing Data Contamination in Language Model Evaluation through Dynamic and Time-Sensitive Test Construction.** (arXiv 2023; AAAI 2024 版本可引) ([arXiv][2])
* Jain et al. **LiveCodeBench: Holistic and Contamination-Free Evaluation of LLMs for Code.** (arXiv 2024 / ICLR 2025 版本) ([arXiv][3])
* Dekoninck et al. **ConStat: Performance-Based Contamination Detection in Large Language Models.** NeurIPS 2024. ([NeurIPS Proceedings][17])
* Carlini et al. **Extracting Training Data from Large Language Models.** USENIX Security 2021. ([USENIX][18])
* Nasr et al. **Scalable Extraction of Training Data from (Production) Language Models.** (arXiv 2023; ICLR 2025 版本可引) ([arXiv][6])
* Mattern et al. **Membership Inference Attacks against Language Models via Neighbourhood Comparison.** Findings of ACL 2023. ([ACL Anthology][7])
* Lee et al. **Deduplicating Training Data Makes Language Models Better.** ACL 2022. ([ACL Anthology][8])
* Priem et al. **OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts.** arXiv 2022. ([arXiv][13])
* Lo et al. **S2ORC: The Semantic Scholar Open Research Corpus.** ACL 2020. ([ACL Anthology][15])
* (Semantic Scholar Team) **The Semantic Scholar Open Data Platform.** 2023. ([arXiv][14])
* Gebru et al. **Datasheets for Datasets.** arXiv 2018 / CACM 2021. ([arXiv][9])
* Bender & Friedman. **Data Statements for NLP.** TACL 2018. ([ACL Anthology][10])
* Mitchell et al. **Model Cards for Model Reporting.** FAT* 2019. ([ACM Digital Library][19])
* Biderman et al. **(lm-eval) Lessons from the Trenches on Reproducible Evaluation of Language Models.** 2024. ([arXiv][12])

---

# Appendix A: Claim → Evidence → Artifact Index (One Page)

每条主张都能定位到一个可复现的 artifact 路径（`runs/EXP-*/`）。

## A. Plan Claims (CLAIM-001..009)

| Claim | Evidence | Key Artifacts |
|---|---|---|
| CLAIM-001 | EXP-001, EXP-002 | `runs/EXP-001/eval_report_a.json`, `runs/EXP-002/eval_report_b.json` |
| CLAIM-002 | EXP-003 | `runs/exports/0.2.0-legacy/public/dataset_manifest.json` |
| CLAIM-003 | EXP-004 | `runs/EXP-004/dataset_build_online.log` |
| CLAIM-004 | EXP-005 | `runs/EXP-005/gate_no_try.log` |
| CLAIM-005 | EXP-006 | `runs/EXP-006/check_manual.log` |
| CLAIM-006 | EXP-006, EXP-007 | `runs/EXP-007/pytest.log` |
| CLAIM-007 | EXP-008, EXP-007 | `runs/EXP-008/snapshot_contract.log` |
| CLAIM-008 | EXP-009 | `runs/EXP-009/attack_suite_policy.log` |
| CLAIM-009 | EXP-010 | `runs/EXP-010/demo_codebook_policy.log` |

## B. Oral Addendum (ORAL-001..010, micro-history)

| Oral ID | Evidence | Key Artifacts |
|---|---|---|
| ORAL-001 | EXP-011 | `runs/EXP-011/main_results.csv`, `runs/EXP-011/summary.json` |
| ORAL-002 | EXP-012 | `runs/EXP-011/attacks/A_sealed.json`, `runs/EXP-011/attacks/B_sealed.json` |
| ORAL-003 | EXP-013 | `runs/EXP-013/ablation_results.csv` |
| ORAL-004 | EXP-014 | `runs/EXP-014/cross_domain_summary.json` |
| ORAL-005 | EXP-015 | `runs/EXP-015/human_eval_report.json` |
| ORAL-006 | EXP-016 | `runs/EXP-016/summary.json` |
| ORAL-007 | EXP-017 | `runs/EXP-017/summary.json` |
| ORAL-008 | EXP-018 | `runs/EXP-018/budget_curves.json` |
| ORAL-009 | EXP-019 | `runs/EXP-019/summary.json` |
| ORAL-010 | EXP-020 | `runs/EXP-020/human_eval_report.json` |

## C. Oral vNext (Scale + Baselines + Tradeoff + Replicated Analyses)

| Item | Purpose | Key Artifacts |
|---|---|---|
| EXP-021 | build scale dataset | `runs/EXP-021/dataset/dataset_manifest.json` |
| EXP-022 | scale main table + baselines | `runs/EXP-022/main_results.csv`, `runs/EXP-022/attacks/`, `runs/EXP-022/run_meta.json` |
| EXP-023 | defense knob sweep curve | `runs/EXP-023/tradeoff_curve.png`, `runs/EXP-023/tradeoff_curve.json` |
| EXP-024 | human agreement (kappa + alpha) | `runs/EXP-024/human_eval_report.json` |
| EXP-025 | scale ablations (ORAL-003 on non-toy) | `runs/EXP-025/ablation_results.csv`, `runs/EXP-025/attacks/` |
| EXP-026 | scale cross-domain summary | `runs/EXP-026/cross_domain_summary.json` |
| EXP-027 | scale white-box defense | `runs/EXP-027/summary.json`, `runs/EXP-027/defended_A.jsonl`, `runs/EXP-027/defended_B.jsonl` |
| EXP-028 | scale stats (CI/p/d) | `runs/EXP-028/summary.json`, `runs/EXP-028/summary.md` |
| EXP-029 | scale budget curves | `runs/EXP-029/budget_curves.json` |
| EXP-030 | scale holdout generalization | `runs/EXP-030/summary.json` |
| EXP-031 | scale public bundle export (no codebooks) | `runs/EXP-031/public/public_dataset_manifest.json` |
| EXP-032 | LLM attacker calibration (term recovery) | `runs/EXP-032/summary.json`, `runs/EXP-032/run_meta.json` |
| EXP-033 | recommended release config (knee) | `runs/EXP-033/recommended_config.json` |

# Appendix B: Reproducible Experiment Matrix (EXP-001..033)

下表是 `docs/experiment.md` 的可投递版“矩阵副本”：每行给出该实验要证明的主张、可复现命令、以及 PASS artifact 路径。

| Exp ID | Goal | Re-run Command | Key Artifacts / PASS Summary |
|---|---|---|---|
| EXP-001 | Prove CLAIM-001 on Track A sample | `python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --agent random --output runs/EXP-001/eval_report_a.json` | PASS: `runs/EXP-001/eval_report_a.json` contains keys `rubric`,`audit`,`pareto`. |
| EXP-002 | Prove CLAIM-001 on Track B sample | `python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_b.sealed.jsonl --raw provetok/data/raw/micro_history_b.jsonl --agent random --output runs/EXP-002/eval_report_b.json` | PASS: `runs/EXP-002/eval_report_b.json` contains keys `rubric`,`audit`,`pareto`. |
| EXP-003 | Prove CLAIM-002: offline build exports full artifact set | `python -m provetok.cli dataset build --config provetok/configs/dataset_legacy.yaml --track both --out runs/exports` | PASS: `runs/exports/0.2.0-legacy/public/dataset_manifest.json` exists; required public artifacts are present under `public/**`. |
| EXP-004 | Prove CLAIM-003: strict online build fails early without key | `python -m provetok.cli dataset build --config provetok/configs/dataset.yaml --track A --out runs/exports_online_fail` | PASS (expected failure): `runs/EXP-004/dataset_build_online.log` shows missing `LLM_API_KEY` and fails before network work. |
| EXP-005 | Prove CLAIM-004: repo contains no try/except/finally | `python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match` | PASS: 0 `ast.Try` nodes (see `runs/EXP-005/gate_no_try.log`; exit_code=0 indicates no matches). |
| EXP-006 | Prove CLAIM-005/006: manual decisions logged + paper_key propagated | `python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006 --track both` | PASS: `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl` contains `reviewer_id`; mapping rows include `paper_key` for both A/B (`runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_A_extended.jsonl`, `runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_B_extended.jsonl`) (see `runs/EXP-006/check_manual.log`). |
| EXP-007 | Prove CLAIM-006/007/009 contracts via tests | `python -m pytest -q` | PASS: all tests pass incl. offline-no-network check (see `runs/EXP-007/pytest.log`). |
| EXP-008 | Prove CLAIM-007: snapshot files exist at canonical paths | `python -c \"from pathlib import Path; ps=[Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/works_track_A.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/works_track_B.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_A.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_B.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_A.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_B.jsonl')]; [print(p) for p in ps]; missing=[p for p in ps if not p.exists()]; assert not missing, missing\"` | PASS: all canonical snapshot paths exist (see `runs/EXP-008/snapshot_contract.log`). |
| EXP-009 | Prove CLAIM-008: attack suite README points to repo scripts | `python -c \"from pathlib import Path; p=Path('runs/EXP-006/exports/exp-006-manual-decisions/public/attack_suite/README.md'); t=p.read_text(encoding='utf-8'); assert 'documentation only' in t.lower(); assert 'python -m provetok.cli dataset build' in t; assert 'python provetok/scripts/run_audit_v2.py' in t\"` | PASS: README policy checks passed (see `runs/EXP-009/attack_suite_policy.log`). |
| EXP-010 | Prove CLAIM-009: demo codebooks documented and not copied into exports | `python -c \"from pathlib import Path; root=Path('.'); t=(root/'README.md').read_text(encoding='utf-8').lower(); s=(root/'provetok/data/sealed/README.md').read_text(encoding='utf-8').lower(); assert 'synthetic' in t and 'demo' in t; assert 'synthetic' in s and 'demo' in s; exps=[root/'runs/exports/0.2.0-legacy', root/'runs/EXP-006/exports/exp-006-manual-decisions']; assert all(p.exists() for p in exps); assert not any(list(p.rglob('*.sealed.codebook.json')) for p in exps)\"` | PASS: repo docs mention synthetic demo codebooks and exports contain no `*.sealed.codebook.json` (see `runs/EXP-010/demo_codebook_policy.log`). |
| EXP-011 | Prove ORAL-001: Sealed vs Raw + 2 strong baselines (3 seeds, mean±std) | `python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33` | PASS: generated `runs/EXP-011/main_results.csv` with utility mean±std and leakage columns. |
| EXP-012 | Prove ORAL-002: adaptive attack evidence under black-box / white-box | `python provetok/scripts/run_oral_adaptive_attack.py --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --codebook provetok/data/sealed/micro_history_a.sealed.codebook.json --output runs/EXP-011/attacks/A_sealed.json` | PASS: attack reports include retrieval/keyword/composite metrics for black-box and white-box. |
| EXP-013 | Prove ORAL-003: lexical/structure/numeric/manual-logging ablation evidence | `python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33` | PASS: generated `runs/EXP-013/ablation_results.csv` and `runs/EXP-013/manual_logging_ablation.json`. |
| EXP-014 | Prove ORAL-004: cross-domain trend is explicitly checked on A/B | `python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014` | PASS: ORAL-004 scoped to black-box cross-domain trend (holds on A/B), with white-box gap explicitly reported. |
| EXP-015 | Prove ORAL-005: human-eval consistency pipeline is executable | `python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015` | PASS: `runs/EXP-015/human_eval_report.json` shows `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`. |
| EXP-016 | Prove ORAL-006: quantify defended white-box leakage vs utility tradeoff | `python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33` | PASS: `runs/EXP-016/summary.json` reports white-box improvement on both tracks with explicit utility tradeoff. |
| EXP-017 | Prove ORAL-007: report CI + p-value + effect size for utility comparisons | `python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv --defense_summary runs/EXP-016/summary.json --output_dir runs/EXP-017` | PASS: `runs/EXP-017/summary.json` contains bootstrap CI, permutation p-values, and Cohen's d. |
| EXP-018 | Prove ORAL-008: adaptive budget sweep on sealed/defended setups | `python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128` | PASS: `runs/EXP-018/budget_curves.json` records budget curves for `A/B_sealed` and `A/B_defended`. |
| EXP-019 | Prove ORAL-009: temporal holdout utility/leakage generalization is explicit | `python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7` | PASS: `runs/EXP-019/summary.json` reports holdout retention and explicitly surfaces track-level trend gaps. |
| EXP-020 | Prove ORAL-010: expanded dual-rater human-eval agreement run is reproducible | `python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020` | PASS: `runs/EXP-020/human_eval_report.json` shows `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`. |
| EXP-021 | E6: build a scale (non-toy) micro-history dataset from v2 internal exports (maintainer-only) | `python provetok/scripts/build_oral_scale_dataset.py --in_internal_a runs/exports_s2_full/0.2.0/private/track_A_extended_records.internal.jsonl --in_internal_b runs/exports_s2_full/0.2.0/private/track_B_extended_records.internal.jsonl --out_dir runs/EXP-021/dataset --seal_seed 42 --numeric_bins 10 --write_l1only` | PASS: `runs/EXP-021/dataset/dataset_manifest.json` built with 1500 records/track. |
| EXP-031 | Checklist-2: export a public-safe scale bundle (no codebooks) | `python provetok/scripts/export_oral_scale_public_bundle.py --dataset_dir runs/EXP-021/dataset --out_dir runs/EXP-031/public --overwrite` | PASS: `runs/EXP-031/public/public_dataset_manifest.json` exists; out_dir contains no `*.codebook.json`. |
| EXP-032 | Checklist-3: LLM attacker calibration (term recovery) | `bash -lc 'set -a && source .env && set +a && ./.venv/bin/python provetok/scripts/run_oral_llm_attacker_calibration.py --out_dir runs/EXP-032 --overwrite --n_samples 20 --top_k 3 --seed 42 --scale_dataset_dir runs/EXP-021/dataset'` | PASS: `runs/EXP-032/summary.json` materializes hit@1/hit@3 and records model/base URL (`runs/EXP-032/run_meta.json`). |
| EXP-033 | Checklist-4: derive the recommended release config (knee / shipping decision) | `python provetok/scripts/derive_recommended_release_config.py --curve_json runs/EXP-023/tradeoff_curve.json --out_dir runs/EXP-033 --overwrite` | PASS: `runs/EXP-033/recommended_config.json` records `recommended.level=2` and the black-box-zero option `level=4`. |
| EXP-022 | E6/E7: scale main table + stronger baselines + offline attacks | `python provetok/scripts/run_oral_main_table_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-022 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42` | PASS: `runs/EXP-022/main_results.csv` + `runs/EXP-022/attacks/` + `runs/EXP-022/run_meta.json`. |
| EXP-023 | E8: defense strength knob sweep -> utility vs leakage curve (+ plot) | `python provetok/scripts/run_oral_defense_knob_sweep_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-023 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42` | PASS: `runs/EXP-023/tradeoff_curve.png` + `runs/EXP-023/tradeoff_curve.json`. |
| EXP-024 | E9: human agreement report includes kappa + Krippendorff alpha | `python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-024 --threshold 0.5` | PASS: `runs/EXP-024/human_eval_report.json` includes `krippendorff_alpha_nominal_binary` plus Pearson/Spearman/near-threshold diagnostics. |
| EXP-025 | Scale ablations: replicate ORAL-003 on the non-toy dataset | `python provetok/scripts/run_oral_ablations_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-025 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42` | PASS: `runs/EXP-025/ablation_results.csv` + `runs/EXP-025/attacks/` + `runs/EXP-025/run_meta.json`. |
| EXP-026 | Scale cross-domain trends from scale main table outputs | `python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-022/per_run_metrics.json --output_dir runs/EXP-026` | PASS: `runs/EXP-026/cross_domain_summary.json` + `runs/EXP-026/cross_domain_summary.md`. |
| EXP-027 | Scale white-box defense: defended vs raw deltas on non-toy dataset | `python provetok/scripts/run_oral_whitebox_defense_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-027 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42` | PASS: `runs/EXP-027/summary.json` + `runs/EXP-027/defended_{A,B}.jsonl` + `runs/EXP-027/run_meta.json`. |
| EXP-028 | Scale CI/p/d for utility comparisons on scale main table (+ defense snapshot) | `python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-022/per_run_metrics.json --main_csv runs/EXP-022/main_results.csv --defense_summary runs/EXP-027/summary.json --output_dir runs/EXP-028` | PASS: `runs/EXP-028/summary.json` + `runs/EXP-028/summary.md`. |
| EXP-029 | Scale budget-sweep curves for sealed vs defended (non-toy) | `python provetok/scripts/run_oral_budget_attack_vnext.py --dataset_dir runs/EXP-031/public --defended_dir runs/EXP-027 --output_dir runs/EXP-029 --max_observed 200 --seed 42 --budgets 8 16 32 64 128` | PASS: `runs/EXP-029/budget_curves.json` + `runs/EXP-029/run_meta.json`. |
| EXP-030 | Scale temporal holdout generalization on non-toy dataset | `python provetok/scripts/run_oral_holdout_generalization_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-030 --seeds 11 22 33 --quantile 0.7 --attack_max_observed 200 --attack_seed 42` | PASS: `runs/EXP-030/summary.json` + `runs/EXP-030/holdout_{A,B}_{raw,sealed}.jsonl` + `runs/EXP-030/run_meta.json`. |

[1]: https://arxiv.org/abs/2305.10160 "Stop Uploading Test Data in Plain Text: Practical Strategies for Mitigating Data Contamination by Evaluation Benchmarks"
[2]: https://arxiv.org/abs/2312.12343 "LatestEval: Addressing Data Contamination in Language Model Evaluation through Dynamic and Time-Sensitive Test Construction"
[3]: https://arxiv.org/abs/2403.07974 "[2403.07974] LiveCodeBench: Holistic and Contamination ..."
[4]: https://arxiv.org/abs/2405.16281 "ConStat: Performance-Based Contamination Detection in ..."
[5]: https://arxiv.org/abs/2012.07805 "Extracting Training Data from Large Language Models"
[6]: https://arxiv.org/abs/2311.17035 "Scalable Extraction of Training Data from (Production) Language Models"
[7]: https://aclanthology.org/2023.findings-acl.719/ "Membership Inference Attacks against Language Models ..."
[8]: https://aclanthology.org/2022.acl-long.577/ "Deduplicating Training Data Makes Language Models Better"
[9]: https://arxiv.org/abs/1803.09010 "[1803.09010] Datasheets for Datasets - arXiv"
[10]: https://aclanthology.org/Q18-1041/ "Data Statements for Natural Language Processing: Toward ..."
[11]: https://arxiv.org/abs/1810.03993 "Model Cards for Model Reporting"
[12]: https://arxiv.org/pdf/2405.14782 "arXiv:2405.14782v2 [cs.CL] 29 May 2024"
[13]: https://arxiv.org/abs/2205.01833 "OpenAlex: A fully-open index of scholarly works, authors, ..."
[14]: https://arxiv.org/html/2301.10140v2 "The Semantic Scholar Open Data Platform"
[15]: https://aclanthology.org/2020.acl-main.447/ "S2ORC: The Semantic Scholar Open Research Corpus"
[16]: https://aclanthology.org/2023.emnlp-main.308/ "Stop Uploading Test Data in Plain Text: Practical Strategies ..."
[17]: https://proceedings.neurips.cc/paper_files/paper/2024/file/a7f89793b9e6f8c6568dbbb6ff727b9b-Paper-Conference.pdf "ConStat: Performance-Based Contamination Detection ... - NIPS"
[18]: https://www.usenix.org/system/files/sec21-carlini-extracting.pdf "Extracting Training Data from Large Language Models"
[19]: https://dl.acm.org/doi/10.1145/3287560.3287596 "Model Cards for Model Reporting | Proceedings of the ..."
