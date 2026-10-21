# External generalization: what the numbers say

28 models (5 untrained bases + 13 SFT + 10 RL) x 6 splits = 168 cells, all
complete, zero failed jobs. Greedy decoding, each model's own chat template,
the benchmarks' own scorers. Raw generations in `runs/`, tables in
`summary.{csv,md}`, protocol and caveats in `../harness/README.md`.

## The one-line version

Training on AgentOrch does not destroy general tool-calling ability. It does
cost a small, consistent amount of reference-similarity on foreign code
generation, and it progressively locks the model into our output schema. Most
of the alarming raw numbers are the schema lock-in, not lost capability, and
must not be reported as capability loss.

## 1. Seal-Tools: the drop is mostly format, not capability

Trained checkpoints emit the right API with the right parameters but omit the
`responses` key. Upstream's parser requires all three of api/parameters/
responses and scores such a row **zero**, so a one-field formatting regression
is scored as total failure.

Retriever-64 out-domain, upstream parser vs a parser that does not require
`responses`:

| model | upstream Δ | relaxed Δ | verdict |
|---|---|---|---|
| sft-gemma31b-v1-1ep | **−0.887** | **+0.002** | pure format artifact |
| rl-gemma31b-final | −0.884 | +0.001 | pure format artifact |
| sft-27b-80k-5ep | −0.398 | −0.019 | almost entirely format |
| sft-27b-80k-4ep | −0.359 | −0.017 | almost entirely format |
| sft-27b-80k-3ep | −0.159 | −0.018 | mostly format |
| rl-27b-kl-step120 | −0.046 | **+0.001** | format only |
| sft-gemma26b-v1-2ep | +0.000 | +0.000 | no change at all |
| sft-4b-v2-2ep | −0.237 | **−0.213** | **real** degradation |
| sft-gemma12b-v1-2ep | −0.106 | **−0.080** | **real** degradation |
| sft-4b-v1-2ep | −0.085 | **−0.081** | **real** degradation |

gemma-31B is the headline: taken at face value it "loses" 0.9785 -> 0.0915,
a 91% rejection rate. Its actual selection ability is 0.9785 -> 0.9800.

**Reporting rule: never quote the upstream Seal-Tools delta without the
relaxed one beside it.**

### Format lock-in grows with SFT epochs

27B ladder, retriever-64 out-domain:

| epochs | upstream format rate | upstream F1 | relaxed F1 |
|---|---|---|---|
| base | 0.992 | 0.9764 | 0.9764 |
| 2 | 0.881 | 0.9162 | 0.9411 |
| 3 | 0.716 | 0.8174 | 0.9582 |
| 4 | 0.498 | 0.6178 | 0.9599 |
| 5 | 0.460 | 0.5780 | 0.9578 |

By 5 epochs more than half of all outputs are rejected on a missing field
while selection ability is unchanged. The AgentOrch epoch curve peaks at 3ep
and mildly declines after; out-of-domain, what is happening past 3ep is
schema rigidity, not capability decay.

RL does not have this problem: the KL-anchored 27B checkpoints hold 0.91-0.94
upstream format and sit at or fractionally above base on relaxed F1.

### Capability loss is a small-model phenomenon

Genuine (relaxed) selection degradation appears only in the smaller models --
4B (−0.081 to −0.213) and 12B (−0.080). Every model at 26B and above is
within noise of its base once format is discounted. Less spare capacity, more
forgetting.

## 2. WorkflowBench: a real but small and uniform cost

Parse rates stay at 0.98-1.00, so unlike Seal-Tools this is not a format
artifact.

| family | base ID | trained ID range | Δ range |
|---|---|---|---|
| qwen-27b | 0.2888 | 0.2597-0.2658 | −0.023 to −0.029 |
| qwen-4b | 0.2784 | 0.2171-0.2275 | −0.051 to −0.061 |
| gemma-26b | 0.3038 | 0.2544-0.2628 | −0.041 to −0.049 |
| gemma-31b | 0.2694 | 0.2541-0.2554 | −0.014 to −0.015 |
| gemma-12b | 0.2886 | 0.2369 | −0.052 |

Two structural facts:

- **Flat within a family.** The 27B spans 0.3092 -> 0.4196 AgentOrch
  orchestration (11 points) while WFB-ID moves 0.006. Training harder in
  domain does not cost more out of domain; the cost is paid once, at
  fine-tuning.
- **Bigger at small scale.** 4B loses roughly twice what 27B does, matching
  the Seal-Tools capacity story.
- RL is indistinguishable from SFT throughout.

**Caveat that limits this claim.** CodeBLEU is a similarity-to-reference
metric (n-gram + syntax + data-flow match against one gold implementation);
it executes nothing. A trained model writing correct-but-differently-styled
Python scores lower without being worse. These numbers show reduced
resemblance to WorkflowBench's reference code, which is consistent with
capability loss but does not establish it. An execution-scored benchmark
(tau2-bench) is the way to settle it.

## 3. What did NOT transfer positively

Nothing. No trained checkpoint beats its base on any external split by more
than noise (best case: RL 27B at +0.001 relaxed Seal-Tools). AgentOrch
training is specialisation, not general capability gain — expected, given
3,000 recipes in a single output format, but worth stating plainly rather
than hunting for a positive result that is not there.

## Two benchmark defects found while measuring

1. **Seal-Tools as shipped is saturated.** `dataset_for_finetune` prompts
   carry ~5 already-retrieved candidates, not 4,076. Untrained bases score
   F1_api ~0.98 vs a 0.998 gold ceiling, on the `difficult` subset too. The
   derived retriever-64 split (`harness/build_sealtools_hard.py`) restores
   headroom at the small-model end.
2. **WorkflowBench CodeBLEU has a per-row 0.4 floor.** When a reference has
   no extractable data-flow, that component contributes its full 0.4 weight
   regardless of the prediction, so such rows score >= 0.400 even for an
   empty answer. Per-row, not global. `dataflow_degenerate_rate` in each
   `scores.json` reports the affected fraction (4-14% here).

## A dead end, recorded

The first retriever-64 attempt padded prompts with **uniformly random**
distractors and made the task *easier* (base-qwen4b 0.9845 -> 0.9912).
Cause: 15.5% of upstream's 5 candidates share the gold API's field (hard
negatives) versus 0.1% of random draws — one correct API among 59 tools from
unrelated domains is trivially identifiable. Difficulty is set by distractor
*similarity*, not count. v2 ranks the catalogue by TF-IDF against the task
instruction only (no gold leakage) and validated as genuinely harder
(base-qwen4b 0.9845 -> 0.9348) before the full run.

## Not measured

**tau2-bench** — downloaded, not evaluated. It needs its own agent loop and a
pinned user-simulator model. It is the only suite here that would score
*execution* rather than similarity or format, so it is the one that could
convert the WorkflowBench caveat above into a real answer.
