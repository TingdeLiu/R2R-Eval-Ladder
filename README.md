# R2R-Steptest

VLN-CE 导航评估的冻结阶梯：S100 ⊂ S500 ⊂ S1000。提供可复现生成器、失败关闭的数据/配对/缓存审计、阶段启动门禁与逐 episode 配对报告。Python ≥ 3.10，无运行时第三方依赖。

## 快速开始

```sh
python -m unittest discover -s tests -v
python -m ladder.cli generate --source data/val_unseen.json.gz --parent100 data/start_heading_random100_v1.json.gz --parent500 data/start_heading_random500_v1.json.gz --out artifacts/dataset-v1
python -m ladder.cli audit --source data/val_unseen.json.gz --directory artifacts/dataset-v1
python -m ladder.cli cache --records artifacts/cache_records.json
python -m ladder.cli stage --manifest artifacts/run_manifest.json
python -m ladder.cli stage --manifest artifacts/run_manifest.json --execute
python -m ladder.cli report --directory artifacts/dataset-v1 --b0 artifacts/b0.json --candidate artifacts/candidate.json --b0-manifest artifacts/b0_manifest.json --candidate-manifest artifacts/candidate_manifest.json --out artifacts/report.json
```

生成器默认校验方案中的源和两个冻结父文件 SHA-256，使用 seed 20261006；先写 generation_plan.json 再生成数据，不覆盖不同内容的冻结文件。输出保持源文件顶层元数据，完整 episode 内容必须与源一致。显式 `--holdout` 将检查父集合不重叠并从抽样池排除 holdout。gzip 固定 mtime，JSON 稳定排序；固定 Python/zlib 版本以保证跨机器压缩字节一致。

## 数据与上游

数据下载与 Habitat 环境配置见 [VLN-CE 官方仓库](https://github.com/jacobkrantz/VLN-CE#data)。本项目实现评估协议工具，不包含 Habitat、模型 checkpoint、Matterport3D 场景或 Agent。真实导航运行需要用户提供冻结的外部执行命令与环境。

datasets/manifests/source_registry.json 记录已知哈希与发布状态。已用匹配这些哈希的真实源数据和冻结父集合完成 S1000 生成与完整审计；完整数据、manifest、生成计划和校验和位于 [dataset-v1 发布目录](datasets/releases/dataset-v1/)，并由 `dataset-v1` tag 固定。S1000 导航评估尚未运行。生成计划只记录逻辑文件名，避免把本机绝对路径写入公开 manifest；protocol-v1 固定协议工具。

结果文件是 JSON 数组，每行包含 scene_id、episode_id、sr、spl、os、ne、steps。SR/OS 为 0 或 1；SPL 为 [0,1]。报告输出 original100、additional400、additional500、combined500、combined1000 的配对均值、gain/loss、成功保持率和配对 bootstrap 差值 95% 区间。累计集合不能作为独立重复实验；NE/steps 差值下降通常表示改善。

阶段 manifest 见 schemas/run_manifest.schema.json。command 是参数数组，runner 先审计文件哈希、源码 commit、干净工作树、上阶段通过、冻结状态和批准 token 预算；默认仅预检，--execute 执行外部命令。P2/P3 应只运行增量 episode，外部适配器负责严格按数据清单输出结果与原始请求日志。runner 不自动宣称实验通过。

缓存请求必须包含协议、数据、源码、模型版本、schema、prompt、媒体哈希、event、episode、control epoch 和帧序列；input_sha256 为完整 request 的 canonical JSON SHA-256。保留 response、technical_error、fallback、cache_hit，命中还须携带相同 reused_input_sha256。预算与覆盖率日志由运行适配器采集，不能删除失败记录。

完整设计见 [项目方案](阶梯样本评估与独立GitHub项目方案.md)，协议见 protocols/，报告模板见 reports/。
