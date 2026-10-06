# R2R-Eval-Ladder

**English** | [中文](README_CN.md)

**Nested 100 → 500 → 1000 episode evaluation datasets for developing zero-shot vision-and-language navigation (VLN) systems powered by large-model API calls.**

During development, these systems often send navigation instructions, visual observations, and history to a model repeatedly to decide the next action. A single trajectory can involve many API calls. Repeatedly tuning prompts, decision logic, or controllers and evaluating at scale can consume substantial tokens, increasing both cost and turnaround time.

R2R-Eval-Ladder is designed to expand testing, optimization, and evaluation progressively: use a small smoke subset to check integration and validate an idea, screen candidates on 100 episodes, then expand to 500 and 1000 after freezing the protocol to assess effectiveness and cost. Each stage includes every episode from the previous stage. When inputs, protocol, and hashes satisfy reuse requirements, only the new episodes need to be evaluated, reducing repeated API calls.

The project provides staged VLN-CE datasets, generation and auditing tools, and paired reports to help developers iterate on zero-shot VLN systems within a token budget.

[Download dataset-v1](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/tag/dataset-v1) · [Browse dataset files](datasets/releases/dataset-v1/)

## Contents

- [Current status](#current-status)
- [Choosing a subset](#choosing-a-subset)
- [Quick start](#quick-start-use-the-published-dataset)
- [Reproduce and audit the dataset](#reproduce-and-audit-the-dataset)
- [Run navigation evaluations](#run-navigation-evaluations)
- [Documentation and development](#documentation-and-development)

## Current status

| Item | Status |
| --- | --- |
| S100 / S500 / S1000 datasets | Generated and published as `dataset-v1` |
| Data files, episode manifests, and SHA-256 checksums | Available for download and verification |
| Generator, audits, stage preflight, and paired reporting | Available |
| S1000 navigation evaluation and model scores | **Not yet run; no evaluation results available** |

This project provides evaluation data and tools. To run a navigation model, prepare a Habitat environment, Matterport3D scenes, a model checkpoint, and an evaluation program. See the [official VLN-CE repository](https://github.com/jacobkrantz/VLN-CE#data) for setup and download instructions.

## Choosing a subset

All episodes come from the same frozen version of `val_unseen`:

```text
S100 ⊂ S500 ⊂ S1000
S500  = S100 + additional400
S1000 = S500 + additional500
```

Download individual files directly from the table below; cloning the repository is optional.

| File | Episodes | Purpose | Download | Manifest |
| --- | ---: | --- | --- | --- |
| `random100_v1.json.gz` | 100 | Initial checks and candidate screening | [Download .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random100_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random100_v1.manifest.json) |
| `additional400_v1.json.gz` | 400 | New episodes when expanding from S100 to S500 | [Download .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional400_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional400_v1.manifest.json) |
| `random500_v1.json.gz` | 500 | Intermediate evaluation after freezing the protocol | [Download .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random500_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random500_v1.manifest.json) |
| `additional500_v1.json.gz` | 500 | New episodes when expanding from S500 to S1000 | [Download .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional500_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/additional500_v1.manifest.json) |
| `random1000_v1.json.gz` | 1000 | Larger-scale confirmation of effectiveness and cost | [Download .json.gz](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random1000_v1.json.gz) | [Manifest](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/random1000_v1.manifest.json) |

Supporting files: [SHA256SUMS](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/SHA256SUMS) · [generation_plan.json](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/download/dataset-v1/generation_plan.json)

Each dataset has a corresponding `*.manifest.json` containing episode identifiers, source indices, and file hashes. `generation_plan.json` records generation parameters; `SHA256SUMS` verifies downloaded files.

Episode identity is **`(scene_id, episode_id)`**, not `episode_id` alone. These subsets support staged testing and engineering decisions. Independent generalization evaluation requires a separate, non-overlapping holdout that is excluded from tuning.

## Quick start: use the published dataset

Requires **Python 3.10 or later**. The tools use only the Python standard library.

```sh
git clone https://github.com/TingdeLiu/R2R-Eval-Ladder.git
cd R2R-Eval-Ladder
git checkout dataset-v1
```

The data is included in `datasets/releases/dataset-v1/`. Individual files are also available on the [Release page](https://github.com/TingdeLiu/R2R-Eval-Ladder/releases/tag/dataset-v1).

Check the number of episodes in S100:

```sh
python -c "import gzip,json; p='datasets/releases/dataset-v1/random100_v1.json.gz'; print(len(json.load(gzip.open(p,'rt',encoding='utf-8'))['episodes']))"
```

Expected output: `100`. Configure your navigation evaluation program to use the desired `.json.gz` file as its dataset input. The configuration field depends on the model project.

Verify all published files on Linux / WSL:

```sh
cd datasets/releases/dataset-v1
sha256sum -c SHA256SUMS
cd ../../..
```

Checksum verification confirms that downloaded files match the published version. Comparing every episode against the original source additionally requires the `audit` command below.

## Reproduce and audit the dataset

Place these three **original frozen files** in your local `data/` directory:

- `val_unseen.json.gz`: the original source dataset;
- `start_heading_random100_v1.json.gz`: the original frozen S100;
- `start_heading_random500_v1.json.gz`: the original frozen S500.

Input SHA-256 hashes must match the [source registry](datasets/manifests/source_registry.json). The published `random100_v1.json.gz` / `random500_v1.json.gz` files have been sorted and recompressed; **they cannot directly replace parent inputs whose original file hashes are required**.

Run from the repository root. Each command is a single line and works in PowerShell or Bash:

```sh
python -m ladder.cli generate --source data/val_unseen.json.gz --parent100 data/start_heading_random100_v1.json.gz --parent500 data/start_heading_random500_v1.json.gz --out artifacts/dataset-v1 --seed 20261006
python -m ladder.cli audit --source data/val_unseen.json.gz --directory artifacts/dataset-v1
```

The generator checks input hashes, composite-key uniqueness, parent–child inclusion, and complete episode content. It records the seed before writing datasets and refuses to overwrite an existing output with different content. JSON ordering is stable and gzip timestamps are fixed. Use the same Python / zlib versions to reproduce compressed-file hashes.

To exclude an independent holdout, add `--holdout <file-path>` to the generation command. The generator rejects a holdout that overlaps the parent subsets and excludes it from the pool for new episodes. Save changes to sampling conditions as a new version.

## Run navigation evaluations

Prepare evaluation programs for B0 (the baseline) and the candidate, then proceed through these stages:

| Stage | Episodes to run | Entry condition |
| --- | --- | --- |
| Smoke | Temporary subset of 8–20 | Check environment startup, inputs/outputs, action budgets, and fallback behavior |
| P1 | S100 | Smoke passed |
| P2 | New additional400 | P1 passed and protocol frozen |
| P3 | New additional500 | P2 passed, protocol frozen, and budget approved |

Every episode requires paired B0 and candidate results. Retain parent results during expansion only when inputs, protocol, and hashes satisfy reuse requirements. Changes to the model, prompt, or controller require a new protocol version.

### 1. Stage preflight and execution

Prepare `artifacts/run_manifest.json` using the [run manifest schema](schemas/run_manifest.schema.json). Specify the dataset, source code, model, configuration, seed, token budget, and external evaluation command. Represent `command` as an argument array.

```sh
# Validate conditions without starting the navigation program
python -m ladder.cli stage --manifest artifacts/run_manifest.json

# Execute the manifest command after validation passes
python -m ladder.cli stage --manifest artifacts/run_manifest.json --execute
```

The tool checks input file hashes, the source commit in the current working directory, a clean working tree, the previous-stage pass flag, protocol freeze status, and budget. The experiment owner sets the pass flag based on results; the tool does not automatically judge whether performance meets the acceptance criteria. The external program handles navigation, result recording, and raw logs.

### 2. Cache audit

```sh
python -m ladder.cli cache --records artifacts/cache_records.json
```

Cache records form a JSON array. Each record must retain the complete request identity, `input_sha256`, `response`, `technical_error`, `fallback`, and `cache_hit`. For a hit, `reused_input_sha256` must match. Request identity covers the protocol, dataset, source code, model version, schema, prompts, media hashes, event, episode, control epoch, and frame sequence.

### 3. Generate an S1000 paired report

B0 and candidate results are separate JSON arrays, each covering exactly S1000. Example row:

```json
{"scene_id": "scene/path.glb", "episode_id": "123", "sr": 1, "spl": 0.72, "os": 1, "ne": 1.3, "steps": 85}
```

`sr` is success, `spl` is success weighted by path efficiency, `os` indicates whether the trajectory ever entered the success region, `ne` is navigation error, and `steps` is the step count. SR / OS must be 0 or 1; SPL must be in [0, 1].

```sh
python -m ladder.cli report --directory datasets/releases/dataset-v1 --b0 artifacts/b0.json --candidate artifacts/candidate.json --b0-manifest artifacts/b0_manifest.json --candidate-manifest artifacts/candidate_manifest.json --out artifacts/report.json
```

Both run manifests must satisfy the pairing lock requirements. `dataset_manifest_sha256` must match the `random1000_v1.manifest.json` used for this report.

The report includes original100, additional400, additional500, combined500, and combined1000. For each group, it reports metric means, candidate-minus-baseline differences, paired bootstrap 95% intervals, recovered successes, lost successes, and success retention. Cumulative subsets overlap and must not be treated as independent samples. Lower NE / steps differences generally indicate improvement.

The execution program must separately collect request counts, tokens, costs, failed retries, intervention coverage, P50/P95 latency, and GPU time. Summarize these using the [report template](reports/report_template.md).

## Documentation and development

| Topic | Entry point |
| --- | --- |
| Staged evaluation protocol | [ladder_v1.md](protocols/ladder_v1.md) |
| B0 / candidate pairing rules | [b0_candidate_pairing.md](protocols/b0_candidate_pairing.md) |
| Token budgeting | [token_budget.md](protocols/token_budget.md) |
| Data provenance and usage | [datasets/README.md](datasets/README.md) |
| JSON format contracts | [schemas/](schemas/) |
| Generation, auditing, and reporting implementation | [ladder/](ladder/) |

View CLI help and run tests:

```sh
python -m ladder.cli --help
python -m unittest discover -s tests -v
```

Pin the `dataset-v1` data tag and the tool commit used for reproducible experiments. `protocol-v1` marks the initial tool version; identify later tool changes by their specific commit.

Code is licensed under the [MIT License](LICENSE). Upstream datasets and scenes retain their respective licenses and terms; see [VLN-CE](https://github.com/jacobkrantz/VLN-CE) for provenance.
