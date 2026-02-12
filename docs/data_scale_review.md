# 数据规模评审清单（S2 真实采集）

更新时间：2026-02-06

## 1) 已清理的历史模拟数据

已删除：

- `runs/*` 下全部历史实验产物
- `provetok/data/exports/0.1.0/`
- `provetok/data/raw/micro_history_a.jsonl`
- `provetok/data/raw/micro_history_b.jsonl`
- `provetok/data/sealed/micro_history_*.sealed.jsonl`
- `provetok/data/sealed/micro_history_*.sealed.codebook.json`

当前仅保留：

- `provetok/data/sealed/README.md`
- 空目录：`provetok/data/raw/`、`provetok/data/exports/`、`runs/`

## 2) 规模计算口径

双 track（A/B）下：

- 公开记录规模：`2 * extended_size`（extended）与 `2 * core_size`（core）
- S2 调用估算：
  - `search/bulk`：每 track `ceil(max_results / 1000)`
  - `paper/batch`：每 track `ceil(pool_size / 500)`
  - `pool_size = min(max_results, max(extended_size, round(extended_size * backfill_pool_multiplier)))`
  - 双 track 总调用：`2 * (search/bulk + paper/batch)`

说明：当前 pipeline 在进入 fulltext/record 前会对 `selected_pool` 做 `paper/batch` 批量补全，这一步决定了调用上限。

## 3) 规模选项（完整列表）

| 方案 | core_size (每track) | extended_size (每track) | max_results (每track) | backfill_pool_multiplier | pool_size (每track) | S2调用总数(双track) | extended总量(双track) | 预计PDF存储(2~8MB/篇) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S0 最小冒烟 | 30 | 300 | 1000 | 2.0 | 600 | 6 | 600 | 1.2~4.7 GB |
| S1 评审版 | 80 | 1000 | 4000 | 3.0 | 3000 | 20 | 2000 | 3.9~15.6 GB |
| S2 推荐发布 | 120 | 1500 | 6000 | 3.0 | 4500 | 30 | 3000 | 5.9~23.4 GB |
| S3 当前配置 | 120 | 2000 | 10000 | 5.0 | 10000 | 60 | 4000 | 7.8~31.2 GB |

## 4) 当前仓库配置对应规模

`provetok/configs/dataset.yaml` 当前为：

- `A.core_size=120`、`A.extended_size=2000`
- `B.core_size=120`、`B.extended_size=2000`
- `max_results=10000`（A/B）
- `backfill_pool_multiplier` 默认 5.0（来自 selection 配置默认）

对应上表 S3：双 track 约 60 次 S2 调用，extended 总量 4000。

## 5) 推荐你先评审的目标

建议先用 **S2 推荐发布**：

- `core_size=120`（保持 benchmark 主集强度）
- `extended_size=1500`（降低 fulltext 成本与时间）
- `max_results=6000`
- `backfill_pool_multiplier=3.0`

优点：

- 调用量从 60 次降到约 30 次
- extended 从 4000 降到 3000，仍保留较好覆盖
- 更容易在一次迭代内完成并复核

## 6) 供你确认的评审项

- 是否采用 S2（推荐发布）作为本轮上线规模
- 是否保留 `core_size=120` 不变
- `extended_size` 用 1500 还是 2000
- `backfill_pool_multiplier` 是否从 5.0 调到 3.0
- 是否先跑 A 再跑 B（分批上线）还是一次双 track 全量跑
