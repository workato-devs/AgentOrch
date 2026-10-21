# External-benchmark eval harness

Evaluates the AgentOrch-trained checkpoints on the third-party benchmarks in
this folder. Deliberately standalone: nothing here imports the AgentOrch
`evaluation` package or `verification` backends, so no part of our own harness
(WorkflowPlan validators, JSON-stop logits processors, simulator state) can
leak into an external measurement.

## Layout

```
harness/
  build_tasks.py            # benchmarks -> tasks/*.jsonl (normalised prompts)
  generate.py               # one model x N splits, single vLLM engine load
  score_workflowbench.py    # upstream CodeBLEU protocol   (needs .venv-score)
  score_sealtools.py        # upstream ToolLearning P/R/F1 (stdlib only)
  summarize.py              # runs/*/scores.json -> results/summary.{csv,md}
  models.json               # the 28 evaluated models (5 base + 13 SFT + 10 RL)
  run_external_eval.sbatch  # Slurm array, one array index per model
  requirements-score.txt    # pinned CodeBLEU stack
  .venv-score/              # scoring venv (codebleu needs old tree-sitter)

tasks/          normalised task files, one JSONL row per benchmark task
runs/<split>/<model_id>/
  generations.jsonl   raw model output, one row per task (never overwritten)
  per_sample.jsonl    per-task parse flag + score
  scores.json         aggregated metrics for that model/split
  meta.json           model dir, decoding settings, timing, Slurm job id
logs/           Slurm stdout, one file per array task
results/        summary.csv, summary.md
validation/     gold-oracle and smoke runs proving the scorers work
```

## Reproduce

```bash
PY=python   # the benchmark environment (benchmark/requirements.txt)
$PY harness/build_tasks.py                      # tasks/ (deterministic)
cd ../..; sbatch --array=0-33%6 src/external_eval/harness/run_external_eval.sbatch; cd -
$PY harness/score_sealtools.py                  # scores every sealtools run
harness/.venv-score/bin/python harness/score_workflowbench.py
$PY harness/summarize.py
```

Generation is resumable: rerunning an array task reads back
`generations.jsonl` and only runs missing `task_id`s.

## Protocol

Greedy (`temperature=0, top_p=1, seed=0`), each model's **own** chat template
with `enable_thinking=False` where supported, `max_model_len=16384`, one H200
per model. Decode caps: 4096 new tokens for WorkflowBench (matching the
visible-output cap the AgentOrch benchmark uses, so a model gets no more room
here than at home), 1024 for Seal-Tools (gold p90 is ~180 tokens).

### Deliberate deviations from upstream, and why

1. **Chat template instead of raw Llama-3 control tokens.** The upstream
   WorkflowLLM prompt hard-codes `<|begin_of_text|><|start_header_id|>...`.
   Feeding those literal strings to a Qwen or gemma checkpoint measures
   tokenizer mismatch, not orchestration. The prompt *text* is carried over
   byte-identical; only the turn framing is each model's own.
2. **Sorted API list.** `statistics.pkl['action_names']` is a Python `set` and
   upstream joins it straight into the prompt, so upstream prompts are not
   byte-reproducible across runs. Sorted here. Same content, stable order.
3. **`test` split for WorkflowBench ID.** Upstream's training script validates
   on `dev`; `dev` is therefore model-selection data. `test` (1,190 keys) is
   the clean held-out split. OOD has only train/dev upstream, so OOD uses
   `dev` as upstream does.
4. **Rows without resolvable API docs are dropped** (6 of 1,190 ID, 4 of 636
   OOD): with no `identifier2python` entry the prompt has an empty tool
   section and the task is unanswerable by construction.

### Two scoring hazards, measured rather than hidden

**WorkflowBench — the degenerate data-flow 0.4.** CodeBLEU's weights are
`(ngram .1, weighted_ngram .1, syntax .4, dataflow .4)`. When the *reference*
has no extractable data-flow, the library folds a full 1.0 into that 0.4
regardless of the prediction, so such a row scores >= 0.400 even for an empty
answer. It is per-row, not global — references with real variable chains score
normally, and a bad answer there lands below 0.4. A blanket rescale of the
mean would misreport, so the headline `codebleu` stays faithful to upstream
and `dataflow_degenerate_rate` reports what fraction of rows got the free 0.4.
`codebleu_earned_mean` averages only the non-degenerate rows. **Never quote
the headline CodeBLEU without the degenerate rate beside it.**

**Seal-Tools — lossy quote normalisation.** The upstream parser does
`re.sub("'", '"', text)` before `json.loads`, which mangles apostrophes inside
string values. It costs ~0.5% of rows even on gold. Kept as-is for
comparability; it is why the gold oracle scores 0.998 rather than 1.000.

## Validation

`validation/gold_oracle/` feeds each benchmark's own gold answers back through
the scorers. Scoring gold must be ~1.0, and is:

| split | metric | gold-oracle score |
|---|---|---|
| workflowbench_ood_dev | CodeBLEU | 0.9974 |
| sealtools_test_in_domain | F1_api / F1_param | 0.9980 / 0.9966 |
| sealtools_test_out_domain | F1_api / F1_param | 0.9982 / 0.9973 |

`validation/smoke/` is the 8-task end-to-end run (base Qwen3-4B) used to prove
the generate -> score path before the full array.

## Not covered here

**tau2-bench.** It drives the agent through its own loop and needs a second
model as user simulator, so it cannot reuse this batch-generation harness. It
is downloaded and documented in `../README.md` but not evaluated; doing so
needs a `model_corpus.py`-shaped adapter and a pinned simulator model.
