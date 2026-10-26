# AgentOrch evaluation

AgentOrch compares Global orchestration and Step-by-Step interaction on
650 enterprise SOPs and 3,220 runtime variants with the same 64 tool
interfaces, connector simulator, and execution-based evaluator.

## Setup

Run commands from the repository root using Python 3.12:

```bash
python3.12 -m venv .venv-eval
source .venv-eval/bin/activate
python -m pip install -r benchmark/requirements-api.txt
python scripts/download_data.py --only benchmark
```

The API environment runs the evaluator on CPU. For local Hugging Face
inference, install `benchmark/requirements.txt` in a separate GPU environment.

The included sample runs without a model or a data download:

```bash
PYTHONPATH=benchmark python -m verification.connector_runner \
  --backend simulated --recipe-id 64112882 --variant 0
```

Its final JSON should contain `"verifier_ok": true`.

## Run an evaluation

### The canonical evaluator

```bash
export LOCAL_LLM_BASE_URL=http://localhost:8000/v1
export LOCAL_LLM_API_KEY=your-server-key

PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-model --backend simulated --model compat:my-served-model \
  --modes plan_execute,react --ids 64112882 --variants all
```

Replace the endpoint, key, and served model name. Omit the key for an
unauthenticated server. The server accepts Chat Completions requests and
returns the model's JSON response as text in `choices[0].message.content`.
The evaluator supplies prompts and executes tools.

Remove `--ids 64112882` to evaluate all 650 SOPs and 3,220 variants. Use
`--resume` with the same run name and configuration to continue a run.
Use a new run name for a different model or generation configuration.

### Local Hugging Face models

```bash
python -m pip install -r benchmark/requirements.txt
export HF_LOCAL_ENGINE=vllm

PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name local-model --backend simulated \
  --model hf:JesseLiu/agentorch-sft-4b-v1-2ep \
  --modes plan_execute,react --ids 64112882 --variants all
```

Use `hf:<org>/<model>` for a Hub checkpoint or `hf:/absolute/checkpoint/path`
for local weights. Set `VLLM_TENSOR_PARALLEL` for multi-GPU inference and
`HF_MODEL_REVISION` to select a model revision.

### Provider APIs

Set `OPENAI_API_MODE=direct` and `OPENAI_API_KEY` for OpenAI,
`AZURE_OPENAI_*` for Azure OpenAI, or `ANTHROPIC_API_KEY` for Claude.
Pass the provider model ID to `--model`. Credentials can be loaded from
`.env`; see [the environment example](../.env.example).

### Protocols

| Paper setting | Entry point | Model information and execution |
| --- | --- | --- |
| Global | `evaluation.full_eval --modes plan_execute` | One complete workflow per SOP, before concrete runtime inputs; reused across variants. |
| Step-by-Step | `evaluation.full_eval --modes react` | One action at a time, with concrete runtime input and intermediate tool observations. |
| Local | `evaluation.full_eval --modes incremental_workflow` | Append-only workflow construction with validator feedback, without runtime inputs or execution. |
| Input-Conditioned Global | `evaluation.full_eval --modes global_input` | One complete workflow per concrete runtime input, without intermediate execution feedback. |
| Replan | `experiments.replan_iter` | Complete-workflow revision between executions, using feedback from the current workflow. |

All settings use the same simulator and scorer. Reference plans, reference
executions, expected state, and evaluation scores are excluded from model
prompts. [Input-Conditioned Global](doc/global_input.md) corresponds to Table 4.

### Generation settings

The standard local configuration uses a 131,072-token context, with up to
122,880 input tokens, a 4,096-token Global output cap, and an 8,192-token
ReAct hard cap with a 1,024-token soft cap. API ReAct requests use a
4,096-token cap. ReAct generation stops at a complete top-level JSON object.

Reasoning runs use their model-specific configuration. Qwen thinking runs
use 98,304 input tokens and output caps of 32,768 for Global and 16,384 for
ReAct; Claude thinking shares a 16,384-token reasoning/output budget.
Model configurations are in
[global_react_models.json](evaluation/global_react_models.json).

## Replan

Replan starts from a Global workflow. Each round executes the current
workflow, provides its validation or execution feedback to the model, and
requests a complete revised workflow. Execution of the revised workflow
uses no further model calls. Feedback includes tool calls, arguments,
results or errors, control-flow outcomes, and terminal returns; it excludes
reference executions and evaluation scores.

```bash
PYTHONPATH=benchmark python -m experiments.replan_iter \
  --run-name replan --state-namespace revision --backend simulated \
  --model compat:my-served-model --rounds 3 --resume

PYTHONPATH=benchmark python -m experiments.replan_iter_heldout \
  --run-name replan-heldout --state-namespace heldout --backend simulated \
  --model compat:my-served-model --rounds 3 --feedback-variants 2 --resume
```

Add `--ids 64112882` for a sample run. The held-out driver uses the first
two variants of each SOP for feedback and scores `all`, `seen`, `heldout`,
and `heldout2` (the next two variants) separately. An invalid revision leaves
the previous workflow in place. Results for rounds 0–3 are in
[replan_iter.csv](results/replan_iter.csv).

## Scoring and outputs

Each protocol writes `results.jsonl`, `trajectories.jsonl`, and
`leaderboard.json` under `benchmark/outputs/full_eval/<run>/<model>/<mode>/`.
A complete Global or Step-by-Step evaluation has `n = 3220`.

| Metric | Per-variant definition |
| --- | --- |
| Execution Trace Accuracy | Mean of five binary checks: tool selection, order, execution, required arguments, and control path. |
| Side-Effect Accuracy | Required state changes occur without missing, duplicated, or unintended effects covered by the verifier. |
| Orchestration Accuracy | `0.5 × Execution Trace Accuracy + 0.5 × Side-Effect Accuracy`. |
| Terminal Output Accuracy | The terminal response matches the SOP's output contract. |
| Final Accuracy | Both Side-Effect Accuracy and Terminal Output Accuracy pass. |
| Error Rate | Fraction of variants without a scoreable execution. These variants receive zero accuracy and remain in the denominator. |

Tool order compares the realized tool-name sequence with the prescribed
reference sequence. Runtime-generated identifiers are normalized, and
supported Salesforce and Snowflake queries have semantic argument checks.
Partial executions are scored from their accumulated trace and state.
See [metric definitions](doc/metric.md) and the [pipeline](doc/pipeline.md).

## Reported results

| File | Paper comparison |
| --- | --- |
| [results.csv](results/results.csv) | Model scale, generation, reasoning, and protocol comparisons; Section 4 and Appendix I. |
| [local_view.csv](results/local_view.csv) | Incremental workflow construction; Table 5. |
| [global_input.csv](results/global_input.csv) | Input-Conditioned Global; Table 4. |
| [replan_iter.csv](results/replan_iter.csv) | Execution-feedback revision; Figure 4, Table 7, and Appendix B.2. |
| [COST.csv](results/COST.csv) | Inference usage; Figure 1 and Appendix F. |
| [validation_checks/](results/validation_checks/README.md) | Workflow-characteristic metadata; Appendix E. |
| [training results](../training/results/training.csv) | Five base/SFT/RL comparisons; Table 8. |

Aggregate JSON records are in `results/leaderboards/`. To recompute a
leaderboard from your own `results.jsonl`:

```bash
PYTHONPATH=benchmark python -m reproduction.offline.recompute_leaderboard \
  "benchmark/outputs/full_eval/<run>/<model>/<mode>"
```

The result tables contain aggregate records; per-variant records are
created by running the evaluator.

## Data and runtime

`input/` contains model-visible task specifications and public schemas.
`groundtruth/`, `verification/seeds/`, and reference outputs are evaluator
inputs. The downloaded fixtures supply the full benchmark; a single SOP
is included in Git for the sample command.

The shared recipe executor, simulated connectors, and real connectors are
under `verification/backends/`. All model results use `--backend simulated`.
Real connectors support reference collection and require service credentials.
See [verification/](verification/README.md) for their configuration.

The [Slurm launcher](reproduction/cluster/README.md) runs the same evaluator
on a configured cluster. Training is documented in
[training/README.md](../training/README.md).
