# External benchmarks for AgentOrch generalization testing

Three third-party benchmarks vendored here to measure how the AgentOrch-SFT/RL
checkpoints transfer *off* our own corpus. None is part of the AgentOrch
benchmark — all three are held-out, externally-authored suites with their own
scorers.

## Why these three

Our training set (`training/input` + `training/groundtruth`) is 3,000 Workato
recipes in **global mode only**: one natural-language task + a 64-card tool
surface → one complete symbolic `WorkflowPlan` (JSON, with `if/else`, loops,
`try/catch`, regions). `local`, `react`, and `replan` have no training data,
but the benchmark evaluates all four modes, so transfer to the interactive
modes is a claim we make and should corroborate externally.

| Axis | Question | Covered by |
|---|---|---|
| **Ecosystem transfer** | Same skill, entirely different API universe | WorkflowBench |
| **Unseen-tool transfer** | Can it orchestrate APIs never seen in training? | WorkflowBench OOD split, Seal-Tools out-domain split |
| **Interactive + side-effect** | Does `react`/`replan` skill survive in another stateful sandbox? | τ²-bench |

The first two are static generation tasks scored offline and need no agent
loop. τ²-bench is the interactive one and costs an adapter — see its section.

---

## `workflowllm/` — WorkflowBench (OpenBMB, arXiv:2411.05451)

**The closest external analogue to AgentOrch global mode.** Apple Shortcuts
workflows: NL query → executable workflow with nested control flow over a
catalog of **1,503 APIs / 83 apps / 28 categories**.

```
workflowllm/
  data/
    seed_data.json              # 14,523 transcribed real workflows
                                #   fields: query, key, workflow_code, task_plan
    synthesized_data.json       # 95,810 synthesized (106,763 total)
    dataset_split_keys.json     # ID split  (unseen instructions):
                                #   train 9,757 / reward 2,380 / dev 1,190 / test 1,190
    dataset_split_keys_ood.json # OOD split (unseen APIs):
                                #   train 8,071 / dev 636          <-- the generalization read
    identifier2json.pkl         # API docs, JSON form (1,503 APIs)
    identifier2python.pkl       # API docs, Python-signature form
    statistics.pkl              # per-workflow category / action-count / nesting stats
  code/                         # OpenBMB repo: scripts/infer.sh, scripts/infer_OOD.sh
  DATASET_README.md             # upstream HF dataset card
```

**Adaptation needed.** Targets are **Python-like code**, not our JSON
`WorkflowPlan`. Two honest options:

1. Evaluate zero-shot in their native format — measures whether orchestration
   ability survives a format shift. Cheap, do this first.
2. Write a renderer from WorkflowBench APIs → our 64-card tool-surface prompt,
   and compile their gold code into a `WorkflowPlan` for scoring. More work,
   but it isolates orchestration from serialization the way our own plan
   validator does.

Report both if space allows; (1) alone invites the objection that a low score
is just format mismatch.

---

## `seal_tools/` — Seal-Tools (NLPCC 2024)

Nested tool-call JSON generation over **4,076 tools**, with an explicit
**out-of-domain test split** — an independent unseen-tool read, from different
authors, with an author-provided scorer so there is no metric dispute.

```
seal_tools/
  Seal-Tools_Dataset/
    train.jsonl            12,022
    dev.jsonl                 700
    test_in_domain.jsonl      700
    test_out_domain.jsonl     654    <-- the generalization read
    tool.jsonl              4,076 tool definitions
    field.jsonl
    dataset_for_finetune/  # same data, chat-formatted
    dataset_in_old_format/
  LLM_Evaluation/          # official scorer (tool-selection + parameter-filling F1)
  DPR_Training/            # retriever splits, if you want a retrieval-augmented variant
  Dataset_Construct/
```

Row format is a `calling` list where each call's `responses` are symbolic
`API_call_N` handles that later calls consume — structurally close to variable
binding in our `WorkflowPlan`, so it also gives a read on the *semantic
arguments* sub-skill our trace metric measures.

---

## `tau2_bench/` — τ²-bench (Sierra Research)

Interactive tool-agent-user benchmark. The agent works a customer-service task
against a stateful database while an LLM-simulated user supplies information
and, in τ², **also takes actions of its own** (dual control). The reward is a
**comparison of the final database state against gold**, plus required-action
checks — the same construction as our *side-effect accuracy*, arrived at
independently. That makes it the strongest available external corroboration
for the `react`/`replan` results.

```
tau2_bench/
  data/tau2/domains/
    airline/     tasks.json  50 tasks   + db.json, policy.md, split_tasks.json
    retail/      tasks.json 114 tasks   + db.json, policy.md, split_tasks.json
    telecom/     tasks.json 2,285 tasks + db.toml, user_db.toml, policy/manual/
                 tasks_small.json (20, the curated subset used in the paper)
    banking_knowledge/, mock/           # knowledge-only and smoke domains
  data/tau2/user_simulator/             # user-simulator prompts
  src/, scripts/, docs/, examples/      # harness, CLI, domain SDK
```

Every domain ships a `split_tasks.json` with `train` / `test` / `base` keys
(telecom adds `small` / `full`) — use `test` so we are not reporting on tasks
the harness treats as development.

**Adaptation needed.** τ² drives the agent through its own loop, so it needs a
model adapter in the shape of `benchmark/examples/smoke_adapter/model_corpus.py`, plus its `uv`/pip
env. It also needs a second model to play the user simulator; the published
baselines use `gpt-4.1` for that role, and holding it fixed matters for
comparability. Budget for this being the most engineering of the three.

**Not vendored:** `data/voice/` (~800 MB of audio, irrelevant to us) and
`data/tau2/results/final/` (577 MB of raw baseline trajectories — the headline
pass^k numbers we would cite are in the paper). Both are one sparse-checkout
edit away if needed:

```bash
git -C tau2_bench sparse-checkout set --no-cone '/*' '!/data/voice'
```

---

## Evaluation campaign

The AgentOrch checkpoints are evaluated on the two static benchmarks by the
harness in `harness/` — see [`harness/README.md`](harness/README.md) for the
protocol, the deliberate deviations from upstream, and the scorer validation.

- **28 models**: 5 untrained base models + 13 SFT + 10 RL checkpoints. The
  bases are included so every trained checkpoint has a same-family delta;
  without them the external numbers carry no meaning. The two VOID runs
  (`merged-final`, `merged-step100`, which scored base weights through the
  merge bug) are excluded as duplicates of their base.
- **6 splits**: WorkflowBench ID-test (1,184) and OOD-dev (632); Seal-Tools
  in/out-domain at the upstream 5-candidate setting (700 / 654) and at a
  derived 64-tool surface (700 / 654).
- Generations, per-sample scores, and metadata land under `runs/`; Slurm logs
  under `logs/`; the aggregate tables in `results/summary.{csv,md}`.

### Two measurement problems found while building this

**Seal-Tools as shipped is saturated.** The `dataset_for_finetune` prompts
carry ~5 candidate APIs, not the advertised 4,076 — they are already
retrieved. Untrained base models score F1_api ≈ 0.98 against a 0.998 gold
ceiling, on the `difficult` subset too, so the split cannot show whether
training transferred any tool-*selection* ability; only parameter filling
retains headroom. `harness/build_sealtools_hard.py` therefore adds a derived
64-tool variant (same header, same gold, same scorer, larger candidate pool,
64 chosen to match the AgentOrch tool surface). Report the 5-candidate numbers
for comparability with the paper and the 64-tool numbers for the real
selection question — and never present the derived variant as upstream.

**WorkflowBench CodeBLEU has a per-row 0.4 floor.** When a reference has no
extractable data-flow, that component degenerates and contributes its full
0.4 weight no matter what was predicted, so such a row scores >= 0.400 even
for an empty answer. It is per-row, not global, so rescaling the mean would
misreport. The harness keeps the headline faithful to upstream and reports
`dataflow_degenerate_rate` beside it. Quote the two together.

## What to report

1. **WorkflowBench ID test (1,190) + OOD dev (636)** — headline number; the OOD
   split is the unseen-API claim.
2. **Seal-Tools test_out_domain (654)**, with `test_in_domain` (700) as the
   in-distribution control — the in/out gap is the actual generalization
   signal, and the official scorer makes it hard to contest.
3. **τ²-bench airline (50) + retail (114) + telecom small (20)**, `test` split,
   user simulator pinned to one model — external side-effect-scored evidence
   that the `react`/`replan` gains are not Workato-specific.

Run each against the base checkpoint and the SFT/RL checkpoint under identical
decoding settings. The interesting quantity is the **delta**, not the absolute:
we trained on none of these formats, so absolute numbers will be low.

## Considered and not downloaded

All are one command to restore:

- **τ-bench** (`sierra-research/tau-bench`) — the τ² predecessor, retail +
  airline only. Superseded by `tau2_bench/` above; worth pulling only if a
  reviewer wants the original numbers for direct comparison.
- **WorkBench** (`olly-styles/WorkBench`) — 690 outcome-scored tasks in
  email/calendar/CRM/analytics; closest *domain* match to Workato connectors,
  and the best candidate for a fourth suite. Costs the same adapter work as
  τ²-bench without the recognition, which is why τ² went first.
- **NESTFUL** (`ibm-research/nestful`, `IBM/NESTFUL`) — nested output→input
  wiring in isolation, with executable variants. Largely subsumed by
  Seal-Tools for our purposes.
- **API-Bank** (`AlibabaResearch/DAMO-ConvAI/api-bank`) — 73 APIs, L3
  plan+retrieve+call. Small, but dated and low-signal next to the two kept.
- **StableToolBench** (`THUNLP-MT/StableToolBench`) — ToolBench at 16k APIs
  behind a simulated API server. Code alone is not runnable; the API-response
  cache and server weights are a separate large download.
- **NaturalPlan** (`google-deepmind/natural-plan`) — pure planning, no tool
  surface. Only supports a "did not damage general planning" claim.

## Provenance

Fetched 2026-08-31 from public sources, shallow clones (`--depth 1`);
licenses are each repo's own.

```bash
# WorkflowBench
curl -L -o data.zip https://huggingface.co/datasets/openbmb/WorkflowLLM/resolve/main/data.zip
git clone --depth 1 https://github.com/OpenBMB/WorkflowLLM.git code

# Seal-Tools
git clone --depth 1 https://github.com/fairyshine/Seal-Tools.git seal_tools

# tau2-bench (voice audio and baseline trajectory dumps excluded)
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/sierra-research/tau2-bench.git tau2_bench
git -C tau2_bench sparse-checkout set --no-cone \
  '/*' '!/data/voice' '!/data/tau2/results'
```
