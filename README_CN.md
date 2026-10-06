# R2R-Eval-Ladder

[English](README.md) | **中文**

**为调用大模型 API 驱动的 zero-shot 视觉语言导航（VLN）开发，提供 100 → 500 → 1000 条嵌套评估数据集。**

开发这类导航系统时，模型通常需要多次接收导航指令、视觉观测和历史信息，再作出行动决策。一条轨迹就可能涉及多次 API 调用；反复调整 prompt、决策逻辑或控制器并进行大规模评估，会消耗大量 token，增加费用和等待时间。

R2R-Eval-Ladder 的主要目的，是让测试、优化和评估能够按需逐步扩大：先用小样本检查接线和验证思路，再用 100 条筛选方案，方案冻结后扩到 500 条和 1000 条，确认效果与成本。每一级都包含上一级的全部样本；在输入、协议与哈希满足复用条件时，只需评估新增样本，减少重复调用。

项目提供 VLN-CE 阶梯数据集，以及生成、审计和配对报告工具，帮助开发者在 token 预算内迭代 zero-shot VLN 系统。

[下载 dataset-v1](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/tag/dataset-v1) · [查看数据文件](datasets/releases/dataset-v1/)

## 目录

- [当前进度](#当前进度)
- [数据集怎么选](#数据集怎么选)
- [快速开始](#快速开始直接使用已发布数据)
- [复现生成与数据审计](#复现生成与数据审计)
- [导航评估](#如何开展导航评估)
- [文档与开发](#文档与开发)

## 当前进度

| 项目 | 状态 |
| --- | --- |
| S100 / S500 / S1000 数据集 | 已生成并发布为 `dataset-v1` |
| 数据文件、样本清单与 SHA-256 | 已发布，可下载校验 |
| 生成器、审计、阶段预检、配对报告工具 | 已提供 |
| S1000 真实导航评估与模型成绩 | **尚未运行，暂无评估结果** |

本项目提供评估数据和工具。运行导航模型还需要自行准备 Habitat 环境、Matterport3D 场景、模型 checkpoint 和评估执行程序；安装与下载说明见 [VLN-CE 官方仓库](https://github.com/jacobkrantz/VLN-CE#data)。

## 数据集怎么选

所有样本来自同一个冻结版本的 `val_unseen`，满足：

```text
S100 ⊂ S500 ⊂ S1000
S500  = S100 + additional400
S1000 = S500 + additional500
```

点击下表中的下载链接，可直接获取对应文件，无需克隆仓库。

| 文件 | 数量 | 用途 | 数据下载 | 样本清单 |
| --- | ---: | --- | --- | --- |
| `random100_v1.json.gz` | 100 | 初步检查与方案筛选 | [下载 .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random100_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random100_v1.manifest.json) |
| `additional400_v1.json.gz` | 400 | 从 S100 扩到 S500 时新增的样本 | [下载 .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional400_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional400_v1.manifest.json) |
| `random500_v1.json.gz` | 500 | 冻结方案后的中等规模评估 | [下载 .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random500_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random500_v1.manifest.json) |
| `additional500_v1.json.gz` | 500 | 从 S500 扩到 S1000 时新增的样本 | [下载 .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional500_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional500_v1.manifest.json) |
| `random1000_v1.json.gz` | 1000 | 更大规模的效果与成本确认 | [下载 .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random1000_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random1000_v1.manifest.json) |

配套文件：[SHA256SUMS](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/SHA256SUMS) · [generation_plan.json](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/generation_plan.json)

每份数据都有对应的 `*.manifest.json`，记录样本标识、源文件索引和文件哈希。`generation_plan.json` 记录生成参数，`SHA256SUMS` 用于核对下载文件。

样本身份使用 **`(scene_id, episode_id)`**，不能只用 `episode_id`。这些集合用于阶梯测试和工程决策；如需独立泛化验证，应另设不参与调参且不重叠的 holdout。

## 快速开始：直接使用已发布数据

需要 **Python 3.10 或更高版本**。本仓库工具仅使用 Python 标准库。

```sh
git clone https://github.com/TingdeLiu/R2R-Eval-Ladder.git
cd R2R-Eval-Ladder
git checkout dataset-v1
```

数据已包含在 `datasets/releases/dataset-v1/`，也可以从 [Release 页面](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/tag/dataset-v1) 单独下载。

查看 S100 的样本数量：

```sh
python -c "import gzip,json; p='datasets/releases/dataset-v1/random100_v1.json.gz'; print(len(json.load(gzip.open(p,'rt',encoding='utf-8'))['episodes']))"
```

预期输出 `100`。随后将所需 `.json.gz` 文件配置为导航评估程序的数据输入；具体配置项取决于使用的模型项目。

Linux / WSL 下校验全部发布文件：

```sh
cd datasets/releases/dataset-v1
sha256sum -c SHA256SUMS
cd ../../..
```

文件校验确认下载内容与发布版本一致；与原始源数据逐条核对还需要下面的 `audit` 命令。

## 复现生成与数据审计

复现需要以下三个**原始冻结文件**，放在本地 `data/` 目录：

- `val_unseen.json.gz`：原始源数据；
- `start_heading_random100_v1.json.gz`：原始冻结 S100；
- `start_heading_random500_v1.json.gz`：原始冻结 S500。

输入 SHA-256 必须与 [源数据登记表](datasets/manifests/source_registry.json) 一致。发布的 `random100_v1.json.gz` / `random500_v1.json.gz` 经过稳定排序和重新压缩，**不能直接替代要求原始文件哈希的父输入**。

在仓库根目录运行（每条命令均为一行，可用于 PowerShell 或 Bash）：

```sh
python -m ladder.cli generate --source data/val_unseen.json.gz --parent100 data/start_heading_random100_v1.json.gz --parent500 data/start_heading_random500_v1.json.gz --out artifacts/dataset-v1 --seed 20261006
python -m ladder.cli audit --source data/val_unseen.json.gz --directory artifacts/dataset-v1
```

生成器会检查输入哈希、复合 key 唯一性、父子包含关系和完整 episode 内容，记录 seed 后再写出数据。遇到不同内容的已有输出会拒绝覆盖。JSON 使用稳定排序，gzip 固定时间戳；复现压缩文件哈希时应保持 Python / zlib 版本一致。

需要排除独立 holdout 时，生成命令可增加 `--holdout <文件路径>`。生成器会拒绝与父集合重叠的 holdout，并将其从新增抽样池中排除。改变抽样条件应作为新版本保存。

## 如何开展导航评估

先准备 B0（基线）与 candidate（候选方案）的评估程序，再按阶段推进：

| 阶段 | 运行样本 | 启动条件 |
| --- | --- | --- |
| Smoke | 临时 8–20 条 | 检查环境启动、输入输出、动作预算和回退 |
| P1 | S100 | Smoke 通过 |
| P2 | 新增 additional400 | P1 通过，方案冻结 |
| P3 | 新增 additional500 | P2 通过，方案冻结且预算获批 |

每个 episode 都需要 B0 与 candidate 的配对结果。扩容时仅在输入、协议与哈希满足复用条件时保留父集合结果；模型、prompt 或控制器变化需要使用新协议版本。

### 1. 阶段预检与启动

按 [运行清单 schema](schemas/run_manifest.schema.json) 准备 `artifacts/run_manifest.json`，填写数据、源码、模型、配置、seed、token 预算和外部评估命令。`command` 使用参数数组。

```sh
# 只检查条件，不启动导航程序
python -m ladder.cli stage --manifest artifacts/run_manifest.json

# 检查通过后执行 manifest 中的命令
python -m ladder.cli stage --manifest artifacts/run_manifest.json --execute
```

工具检查输入文件哈希、当前工作目录的源码 commit、干净工作树、上阶段通过标记、冻结状态与预算。上阶段标记由实验负责人依据结果填写，工具不会自动判定实验效果达标。外部执行程序负责实际导航、结果记录和原始日志采集。

### 2. 缓存审计

```sh
python -m ladder.cli cache --records artifacts/cache_records.json
```

缓存记录为 JSON 数组。每项需保留完整请求身份、`input_sha256`、`response`、`technical_error`、`fallback` 和 `cache_hit`；命中时 `reused_input_sha256` 必须一致。请求身份覆盖协议、数据、源码、模型版本、schema、prompt、媒体哈希、事件、episode、控制 epoch 和帧序列。

### 3. 生成 S1000 配对报告

B0 和 candidate 结果各为一个 JSON 数组，均须恰好覆盖 S1000。单行示例：

```json
{"scene_id": "scene/path.glb", "episode_id": "123", "sr": 1, "spl": 0.72, "os": 1, "ne": 1.3, "steps": 85}
```

`sr` 为成功、`spl` 为路径效率加权成功、`os` 为轨迹是否曾到达成功范围、`ne` 为导航误差、`steps` 为步数。SR / OS 取 0 或 1，SPL 取值为 [0, 1]。

```sh
python -m ladder.cli report --directory datasets/releases/dataset-v1 --b0 artifacts/b0.json --candidate artifacts/candidate.json --b0-manifest artifacts/b0_manifest.json --candidate-manifest artifacts/candidate_manifest.json --out artifacts/report.json
```

两个运行清单需满足配对锁定条件，`dataset_manifest_sha256` 必须对应本次使用的 `random1000_v1.manifest.json`。

报告分别输出 original100、additional400、additional500、combined500、combined1000 的指标均值、候选减基线的差值、配对 bootstrap 95% 区间、救回数、误伤数与成功保持率。累计集合彼此重叠，不能当作独立样本；NE / steps 的差值下降通常表示改善。

请求数、token、费用、失败重试、干预覆盖率、P50/P95 时延和 GPU 时间需由执行程序另行采集，汇总到 [报告模板](reports/report_template.md)。

## 文档与开发

| 内容 | 入口 |
| --- | --- |
| 阶梯执行协议 | [ladder_v1.md](protocols/ladder_v1.md) |
| B0 / candidate 配对规则 | [b0_candidate_pairing.md](protocols/b0_candidate_pairing.md) |
| Token 预算口径 | [token_budget.md](protocols/token_budget.md) |
| 数据来源与使用说明 | [datasets/README.md](datasets/README.md) |
| JSON 格式约定 | [schemas/](schemas/) |
| 生成、审计与报告实现 | [ladder/](ladder/) |

查看命令帮助与运行测试：

```sh
python -m ladder.cli --help
python -m unittest discover -s tests -v
```

复现实验时固定数据标签 `dataset-v1` 与所用工具 commit。`protocol-v1` 标记初始工具版本，后续工具变化以具体 commit 为准。

代码采用 [MIT License](LICENSE)。上游数据与场景遵循各自的许可和使用条款，来源见 [VLN-CE](https://github.com/jacobkrantz/VLN-CE)。
