# 阶梯样本评估数据集与 GitHub 项目方案

更新：2026-10-06。本文定义 Agent 导航评估使用的嵌套随机样本和后续独立 GitHub 项目。目标是先用小样本验证接线与方向，再逐级扩大样本，避免在方案尚未冻结时消耗 500 条或 1000 条的 Agent token。

## 1. 目标与基本原则

评估集合使用同一个固定源数据集 `val_unseen`，建立三个严格嵌套的随机集合：

```text
S100  ⊂  S500  ⊂  S1000  ⊂  source val_unseen
|S100| = 100
|S500| = 500
|S1000| = 1000
```

其中：

- `S100` 用于接线检查、提示词和控制器的第一次配对实验；
- `S500` 用于冻结方案后的中等规模评估；
- `S1000` 用于方案稳定后的规模确认和最终成本/收益报告。

每一级都保留上一级的 episode，不重新抽取整批数据。扩大样本时只从父集合之外的剩余源数据中随机抽取增量集合。任何集合都不能按照 B0 成败、候选成败、Agent 判断或人工挑选结果筛选。

这套数据集用于阶梯测试和工程决策，不自动等同于论文独立验证集。若要报告泛化结论，必须另行冻结一份不参与 100/500/1000 调参的 holdout。

## 2. 已存在的 100 条和 500 条

当前仓库中的两级集合已经满足嵌套关系，生成新的 1000 条时应把它们当作父版本冻结：

| 集合 | 文件 | 数量 | 源数据 | 选择信息 | SHA-256 |
| --- | --- | ---: | --- | --- | --- |
| `S100` | `data/R2R_VLNCE_v1-3_preprocessed/val_unseen/start_heading_random100_v1.json.gz` | 100 | `val_unseen.json.gz` | seed `20260907` | `3b80bf55c1c070e92f796a04f26f848a500acb41365d4fdb2fe6e502a4036fea` |
| `S500` | `data/R2R_VLNCE_v1-3_preprocessed/val_unseen/start_heading_random500_v1.json.gz` | 500 | 同一源数据 | `S100` + 不重叠的 additional400，seed `20260916` | `19ea4ac4dd0bc513c5bcbc1f69326f556193e95b8b122ed0db8faf52db506d9f` |

源文件当前 SHA-256 为：

```text
data/R2R_VLNCE_v1-3_preprocessed/val_unseen/val_unseen.json.gz
0e4fddca056d2e012ecc52f43a259ebddb1128503a7767b5da3b5af8ea8cf653
```

`S500` 不是事后把结果最好的 500 条拼出来的集合。它由已经冻结的 `S100` 和 400 条不重叠的随机增量组成；逐条 episode key 核对后，`S100 ⊂ S500`，且 `S500` 内没有重复 key。episode 的身份必须使用 `(scene_id, episode_id)`，不能只使用 `episode_id`，因为不同 scene 可能出现相同的 episode 编号。

## 3. 1000 条的冻结方式

建议新增以下两个文件：

```text
data/R2R_VLNCE_v1-3_preprocessed/val_unseen/
├── start_heading_random1000_additional500_v1.json.gz
├── start_heading_random1000_additional500_v1.manifest.json
└── start_heading_random1000_v1.json.gz
```

生成规则：

1. 读取源 `val_unseen.json.gz`，核对源 SHA-256；
2. 读取 `S500`，按 `(scene_id, episode_id)` 建立父集合；
3. 从源数据中删除 `S500` 已有的 500 条；
4. 使用一个在生成前写入 manifest 的固定 seed，从剩余 episode 中随机抽取 500 条；
5. 将这 500 条命名为 `S1000` 的 additional500，并与 `S500` 合并得到 `S1000`；
6. 对合并结果按稳定 key 排序，使用固定 gzip 写法生成可复现文件；
7. 重新读取输出文件，验证数量、唯一性、父子包含关系、源内容未被修改，并记录输出 SHA-256。

本项目可以将 `20261006` 作为 proposed seed，但在真正生成前应在 GitHub issue 或 manifest 中最后确认一次。seed 一旦发布不得更换；如果需要另一份随机 1000 条，应使用新版本号和新 seed，而不是覆盖 `v1`。

`S1000` manifest 至少包含：

```json
{
  "version": "nested_random_episode_subset_v1",
  "source_dataset": ".../val_unseen.json.gz",
  "source_sha256": "...",
  "parent_datasets": [
    {"path": ".../start_heading_random100_v1.json.gz", "count": 100, "sha256": "..."},
    {"path": ".../start_heading_random500_v1.json.gz", "count": 500, "sha256": "..."}
  ],
  "seed": 20261006,
  "parent_count": 500,
  "additional_count": 500,
  "output_count": 1000,
  "selected_source_indices": [],
  "selected_keys": [],
  "output_sha256": "..."
}
```

manifest 中保留 source index 和 episode key，便于审计；报告中使用 episode key，避免源文件排序变化造成误配。

## 4. 阶梯执行协议

每一级都包含 B0 和 candidate 两条配对路径。B0 与 candidate 必须使用相同的 episode 集合、episode seed、模型 checkpoint、最大步数、环境配置、源码 commit 和数据 manifest。候选运行只在上一阶段通过冻结门槛后启动。

| 阶段 | 使用集合 | 触发条件 | 运行内容 | 通过后动作 |
| --- | --- | --- | --- | --- |
| 接线 smoke | 8–20 条临时集合 | 新配置或控制器有改动 | 不做自然分布结论，只查启动、schema、回退、动作预算、输入 hash | 修复接线问题，不进入统计报告 |
| P1 | `S100` | smoke 通过 | B0 + candidate，记录完整 Agent 请求、响应、动作和成本 | 方案淘汰、修复或冻结；未冻结不得扩大 |
| P2 | `S500` | P1 达到预设安全门槛 | 保留 `S100` 的冻结 artifacts，只新增 additional400 的配对运行 | 报告 original100、additional400、combined500；决定是否进入 P3 |
| P3 | `S1000` | P2 通过且 token 预算已批准 | 保留 `S500` 的冻结 artifacts，只新增 additional500 | 报告 original100、additional400、additional500、combined500、combined1000 |

P1 是发现阶段，P2 是工程规模阶段，P3 才是更稳定的规模确认。某阶段失败时停止向上扩展；修复方案后必须提高版本号，不能在相同阶段结果上反复改参数再重新命名为同一实验。

最终报告不能只写 1000 条总均值。至少同时给出：

```text
S100                    （父集合）
S500 - S100             （新增 400）
S1000 - S500            （新增 500）
S500                    （累计 500）
S1000                   （累计 1000）
```

这样可以看出收益是否只来自最初 100 条，也可以区分新增样本的成本和表现。

## 5. Token 成本控制

成本控制的核心是“冻结后增量运行”和“输入 hash 命中才复用”。对某一类 Agent 事件，令 `C_event` 为一次完整请求的实际 token 成本，`Q_n` 为 `S_n` 中该事件的数量，则新增成本近似为：

```text
P1:       100 × C_event
P2 增量:  400 × C_event
P3 增量:  500 × C_event
累计:   1000 × C_event
```

如果每一级都从头重新跑，名义样本量会变成 `100 + 500 + 1000 = 1600` 条；按嵌套增量执行且复用有效 artifacts，只需覆盖 1000 条不同 episode。实际账单还必须加上失败重试、MAGE、图像输入、审核复核和并行等待成本。

允许复用的条件：

- 数据 manifest、源码 hash、模型名和模型版本完全一致；
- 请求 schema、system prompt、用户 prompt、图像/深度文件 hash 完全一致；
- event id、episode key、控制 epoch 和输入帧序列一致；
- 原始 response、技术错误和回退决策均被保留，不能只缓存成功回答；
- 复用命中和未命中都写入 cache manifest。

只要输入 hash 不一致，就重新请求并把新结果标记为新 protocol version。不能因为“看起来是同一个 STOP”就跨轨迹复用 Agent response。

每一级开始前先做 token 预算预估：

```text
estimated_tokens = event_count × (p50_prompt_tokens + p50_completion_tokens)
reserve_tokens    = estimated_tokens × (1 + retry_rate + failure_reserve)
```

预算表同时记录请求数、图像数、输入 token、输出 token、技术失败、重试次数、模型路由、总耗时和实际费用。预算不足时暂停升级到下一阶段，不通过缩短日志或删除失败请求来降低账面成本。

## 6. 统计与配对口径

主指标使用 episode 配对的 SR、SPL、OS、NE、steps，并报告 candidate 相对 B0 的 gain/loss。所有增量集合仍要重新跑对应 B0 或使用通过完整 hash 审计的冻结 B0 row；不能把旧 B0 的均值直接当作新 episode 的 B0。

每一级都检查：

- 成功保持率和 B0 成功被破坏数；
- candidate 救回数、误伤数、净 gain/loss；
- 中间 shadow、Start 审核、Stop 审核和实际动作覆盖数；
- schema/超时/输入不匹配/规划 fallback；
- token、请求时延、P50/P95 和 GPU 时间；
- 原始集合、增量集合和累计集合的置信区间。

`S100` 的结果可以支持接线和方向筛选，不能单独支撑总体结论。`S500` 和 `S1000` 也不能因为包含前一级就被当作三份独立样本；累计集合的统计单位仍是 episode/trajectory，重复使用的父集合只计一次。

## 7. 数据冻结与审计门禁

生成器在输出前必须失败关闭，至少验证：

1. 源数据 SHA-256 与 manifest 一致；
2. 每个集合 episode key 唯一；
3. `S100 ⊂ S500 ⊂ S1000`；
4. additional400 与 S100 不重叠，additional500 与 S500 不重叠；
5. 每个 episode 的 instruction、scene、start position 和 goal 内容与源文件完全一致；
6. 输出数量分别为 100、500、1000；
7. 生成同一 seed 两次得到相同 selected keys 和输出 hash；
8. holdout 与三个阶梯集合没有重叠；
9. 运行 manifest 锁定数据、源码、模型、配置、seed 和缓存策略；
10. 报告生成脚本从逐条 row 重新计算均值，禁止手工填写累计指标。

已有 `scripts/eval/merge_episode_dataset_subsets.py` 只按 `episode_id` 去重，不足以作为这个项目的最终生成器。GitHub 项目应实现按 `(scene_id, episode_id)` 去重的专用 generator，并为每一个输出写 manifest。

## 8. 独立 GitHub 项目建议

项目可以命名为 `agent-eval-ladder` 或 `nav-agent-sample-ladder`，仓库只保存可复现协议、manifest、生成器、审计器和报告模板。若基准数据有分发限制，仓库不直接提交原始 Habitat 数据，只提交下载说明、源 hash、selected keys 和生成命令。

建议目录：

```text
agent-eval-ladder/
├── README.md
├── LICENSE
├── protocols/
│   ├── ladder_v1.md
│   ├── b0_candidate_pairing.md
│   └── token_budget.md
├── datasets/
│   ├── manifests/
│   │   ├── random100_v1.manifest.json
│   │   ├── random500_v1.manifest.json
│   │   └── random1000_v1.manifest.json
│   └── README.md
├── generators/
│   └── make_nested_random_sets.py
├── audits/
│   ├── check_nested_sets.py
│   ├── check_pairing.py
│   └── check_cache_integrity.py
├── runners/
│   └── run_ladder_stage.py
├── reports/
│   └── report_template.md
├── schemas/
│   ├── dataset_manifest.schema.json
│   ├── run_manifest.schema.json
│   └── token_usage.schema.json
└── tests/
    ├── test_nestedness.py
    ├── test_deterministic_generation.py
    └── test_no_duplicate_keys.py
```

GitHub 项目第一版应先完成数据层和审计层，再接入具体 Agent：

1. 发布源数据版本和 `S100/S500/S1000` manifest；
2. 在 CI 中检查嵌套关系、唯一 key、源 hash 和确定性；
3. 以 tag 固定 `dataset-v1` 和 `protocol-v1`；
4. 评估项目只引用 tag，不引用会漂移的 `main`；
5. 把每次实验的 run manifest、token usage 和结果报告作为 release artifact；
6. 任何新模型、新 prompt、新控制器都增加 protocol version，不覆盖旧结果。

## 9. 当前执行顺序

本仓库目前只冻结了 `S100` 和 `S500`，新的 `S1000` 还应先完成数据生成和审计，再启动 1000 条 Agent 评估。推荐顺序为：

1. 把本文和现有 100/500 manifest 复制到独立 GitHub 项目；
2. 实现按 `(scene_id, episode_id)` 工作的 nested-set generator；
3. 生成 proposed `S1000` additional500，执行完整审计；
4. 先在 smoke 集合上验证 runner 和 token cache；
5. 使用同一冻结方案完成 `S1000 - S500` 增量评估；
6. 合并并报告累计 1000 条，同时保留 100、增量400、增量500、累计500 的分层结果。

在 1000 条集合和 manifest 发布前，不应把未来的 1000 条称为已经完成的随机评估，也不能用它替换当前 `S500` 的既有实验记录。
