# AgentOrch Training Experiments — Full Record

Goal: train open models on the benchmark-aligned training section to approach
claude-opus-5's global-mode score (orchestration 0.4644). Protocol: SFT warmup
then RL. All runs recorded here + wandb (project `agentorch-qwen38-sft`);
benchmark evals use the frozen public harness (`evaluation.full_eval`,
simulated backend, greedy, 131k ctx, 4096 decode cap) — identical to
`results.csv` baselines. Nothing in the eval path is modified.

## Reproducibility (see ../REPRODUCIBILITY.md)

Every reported score recomputes byte-identically from archived records —
`PYTHONPATH=benchmark python -m reproduction.offline.reproduce_scores --all` → **165/165 lanes EXACT MATCH,
0 mismatches (final verification 2026-09-05; 163/163 on 09-04, 150/150 on 09-01)**. Raw model outputs (plans), scored
per-variant records, trajectories, and merged weights are all retained;
no re-training or re-inference is needed to verify the paper's numbers.

## Baselines (results.csv, frozen)

| model | global orch | error | final |
|---|---|---|---|
| claude-opus-5 (target) | 0.4644 | 0.1916 | 0.2354 |
| Qwen3.8-27B-FP8 | 0.2857 | 0.4388 | 0.1267 |
| gemma-4-31B-it | 0.1271 | 0.7494 | 0.0478 |
| gemma-4-26B-A4B-it | 0.0405 | 0.8922 | 0.0180 |
| Qwen3-4B-Instruct-2507 | 0.1375 | 0.6196 | 0.0391 |
| gemma-4-12B-it | 0.1426 | 0.6578 | (results.csv) |

## Data versions

- **v1** `dataset/training_gd_global_aligned/` (seed `global-aligned-v1`):
  frozen GLOBAL_VIEW template, 64-card surfaces, benchmark-length targeting.
  3,000 rows. Exporter: `task_description/export_training_global_aligned.py`.
- **v2** `dataset/training_gd_global_aligned_v2/` (seed `global-aligned-v2`):
  v1 + all cards canonical-form (uniform contract sections, no raw-recipe
  provenance tells; input/output schemas untouched). 0 style violations.
- **Training files** `src/data_v2/` (exact Qwen tokenizer, 80k budget):
  2,711 train + 60 eval rows. Runtime filter drops targets >6,144 tokens
  (unscorable under the 4096 decode cap): 2,464 rows for Qwen, 2,396 for
  gemma (tokenizer counts differ).
- Sanity subset `src/data_sanity/`: 400 train + 30 eval, targets ≤~2k tokens.
- Golden targets byte-identical to the frozen Plan-SFT export throughout.

## Training runs

| run | model | data | job | wandb | result |
|---|---|---|---|---|---|
| sft-full-2ep-64k | Qwen3.8-27B | v1, 64k, 2ep, LoRA r16 | 26245 | dg6f4jzt | **global 0.3594** (below) |
| qwen27b-v1data-80k-2ep | Qwen3.8-27B | v1, **80k**, 2ep, LoRA r16 | 26613 | (wandb) | 2,521 rows (268 dropped >81,920), 316 steps, 8h42m, final loss 0.078; merged → `merged-27b-v1-80k`, eval pending |
| sanity-4b-short | Qwen3-4B | sanity 400, 2ep | 26281 | pl78rk39 | held-out: parse 57%, seq 13% |
| sft-v2-1ep-80k-r2 | Qwen3.8-27B | v2, 80k, 1ep | 26291 | aztmxc66 | training (eta 8/26 noon) |
| gemma26ba4b-v2-1ep | gemma-4-26B-A4B | v2, 80k, 1ep | 26329 | (running) | training |
| gemma31b-flex-v2-1ep | gemma-4-31B | v2, 80k, 1ep, flex-attn | auto after 26291 | — | queued |
| 4b-full-v2-1ep | Qwen3-4B | v2 full, 80k, 1ep | 26335 | vs0qyk18 | training |

Aborted: 26279 (v2 r1, OOM on 24k-token-target fp32 logits → added target
filter), 26328 (gemma31b sdpa, killed at first step 2077s — in hindsight
mostly 8-rank warmup), 26387 (gemma31b flex_attention: steady 850-1200s/step
because flex recompiles per distinct sequence length and every row differs;
probe at fixed length was misleading), 26392 (gemma31b flash_attention_2:
"FlashAttention forward only supports head dimension at most 256" — gemma-4
head_dim exceeds FA2's limit). Final gemma-31B config: sdpa, measured steady
~800s/step — the sliding-window layers pay full quadratic cost under sdpa but
it is the only working implementation. 26393 killed (node <faulty node> GPU0 HW
thermal slowdown, 345MHz@87C — node excluded, reported); 26397 OOM'd at 80k
rows (sdpa attention masks at ~82k push past 139GB). Final: job 26401 at
**max-len 65536** — 31B trains on the ≤64k subset: only 1,381/2,711 rows
survive the cap under the gemma tokenizer (49% dropped) — a major coverage
caveat vs the other models' ~2,400-2,500 rows; interpret its score
accordingly.

## Benchmark evals (all: full 3,220 variants, frozen harness)

| run name (outputs/full_eval/) | model | orch | error | final | note |
|---|---|---|---|---|---|
| sft-step100-global | **VOID** — evaluated base weights | 0.2887 | 0.4354 | 0.1314 | merge bug, see incidents |
| sft-final-global | **VOID** — evaluated base weights | 0.2887 | 0.4354 | 0.1314 | merge bug |
| **sft-final-fixed-global** | Qwen3.8-27B + v1 SFT (fixed merge) | **0.3594** | **0.2388** | **0.1596** | job 26288; CI95 [0.348, 0.371] |
| **sft-4bfull-global** | Qwen3-4B + v2 SFT 1ep | **0.1929** | 0.5733 | 0.0804 | job 26377; base 0.1375 → +5.5 pts |
| **sft-v2r2-global** | Qwen3.8-27B + v2 SFT 1ep | 0.3092 | 0.3317 | 0.1382 | job 26388; BELOW v1-2ep 0.3594 — confounded (1ep vs 2ep + data change + target filter); error_rate regression suggests under-training, attribution needs a v2-2ep run |
| **sft-gemma26b-global** | gemma-4-26B-A4B + v2 SFT 1ep | **0.1255** | 0.6938 | 0.0512 | job 26410; base 0.0405 → 3.1x. Merged-model config must be restored from the original snapshot (transformers round-trip drops fields vLLM needs) |
| **sft-abl4b-v1-global** | Qwen3-4B + **v1 data** 2ep | **0.2546** | 0.4099 | 0.1078 | job 26423 — DATA ABLATION WINNER |
| **sft-abl4b-v2-global** | Qwen3-4B + v2 data 2ep | 0.2096 | 0.4807 | 0.0870 | job 26425 — single-variable pair with 26423 (same 80k ctx, target filter, 2ep): **v2 canonicalization HURTS by 4.5 pts**. The "style tell" in raw cards is useful learning signal, not just leakage. Verdict: all future runs use v1 data; v2 rejected (honest negative result — the canonicalization was motivated by the later-disproven merge-bug diagnosis) |
| **rl-4b-step20-global** | Qwen3-4B SFT + GRPO 20 steps | **0.2047** | 0.5335 | 0.0761 | job 26469; CI95 [0.1942, 0.2156]. First RL-vs-SFT delta: +1.2 pts over the 4B SFT baseline (0.1929, just below the CI lower bound — marginally significant); error rate 0.5733→0.5335. GRPO production 26431/26439 reached step 34 before being cancelled for the 27B reprioritization; step-20 checkpoint banked |
| **sft-gemma26b-v1-global** | gemma-4-26B-A4B + **v1** SFT 2ep @80k | **0.1989** | 0.5661 | 0.0845 | jobs 26495 (train) + 26552 (eval); CI95 [0.1881, 0.2097]. +7.3 pts over the v2-1ep version (0.1255, confounded 2ep-vs-1ep but consistent with the clean 4B ablation), 4.9x base (0.0405). This replaces 0.1255 as the 26B headline; RL will build on this checkpoint (`merged-gemma26b-v1`) |
| **rl-27b-kl-step60-global** | Qwen3.8-27B v1 SFT + KL-GRPO (LoRA) step 60/124 | **0.3706** | **0.2165** | 0.1643 | job 26596; CI95 [0.3591, 0.3825] vs SFT 0.3594 [0.348, 0.371] — **+1.1 pts orch, −2.2 pts error rate**; CIs overlap at the edges (marginal). New best open-model score (80% of opus 0.4644). Note the 47-prompt in-loop val was flat for this run — the full benchmark resolves what that val cannot |
| **rl-27b-kl-step80-global** | Qwen3.8-27B v1 SFT + KL-GRPO (LoRA) step 80/124 | 0.3702 | 0.2211 | **0.1708** | job 26600; CI95 [0.3588, 0.3815]. Plateau vs step 60 (0.3706/0.2165/0.1643): orch and error flat, final +0.65. RL gain over SFT holds (~+1.1 orch, −2 error) but is not compounding between 60 and 80; steps 100/120 will tell whether it is a ceiling |
| **rl-27b-kl-step100-global** | Qwen3.8-27B v1 SFT + KL-GRPO (LoRA) step 100/124 | 0.3641 | 0.2292 | 0.1674 | job 26610; CI95 [0.3525, 0.3760]. Slightly below steps 60/80 (0.3706/0.3702) — RL gain peaked by step 60 and is drifting down; step 60 is the orch-best checkpoint, step 80 the final-best. Step 120 (last) still to be scored |
| **rl-27b-kl-step120-global** | Qwen3.8-27B v1 SFT + KL-GRPO (LoRA) step 120/124 — **final 27B RL model** | **0.3740** | 0.2224 | 0.1705 | job 26614; CI95 [0.3626, 0.3861]. Highest orch of the four scored checkpoints (60/80/100/120 = 0.3706/0.3702/0.3641/0.3740 — a noise plateau around 0.37, not a decline). vs SFT 0.3594: **+1.5 orch**, −1.6 error, +1.1 final; the CI lower bound now clears the SFT point estimate. Run 26524 completed all 124 steps (41.7 h) |
| **sft-27b-v1-80k-global** | Qwen3.8-27B + v1 SFT 2ep @**80k** | 0.3621 | 0.2425 | 0.1655 | job 26615; CI95 [0.3501, 0.3743]. vs the 64k champion (0.3594/0.2388/0.1596): +0.3 orch — within noise, error slightly worse. **The last lever is spent**: 80k context adds nothing; the 27B final remains 64k-SFT + KL-GRPO step-120 = 0.3740. The not-reaching-opus conclusion stands with every lever now measured |
| **sft-27b-80k-3ep-global** | Qwen3.8-27B + v1 SFT @80k, **3 epochs** (step-474 of the 5ep run) | **0.4196** | **0.1708** | **0.1848** | job 26658; CI95 orch [0.4071, 0.4315], final [0.172, 0.1988]. **The project's largest jump: +5.8 orch over 2ep (0.3621) and +4.6 over the RL step-120 (0.3740). Error rate 0.1708 BEATS opus (0.1916); orch = 90.4% of opus.** The user's call — more epochs — was the lever; the earlier ±1 expectation was wrong. Note: the 3ep checkpoint comes from a 5-epoch lr schedule, so it is not identical to a standalone 3ep run |
| **sft-27b-80k-4ep-global** | Qwen3.8-27B + v1 SFT @80k, 4 epochs (step-632) | 0.4108 | 0.1863 | 0.1832 | job 26659; CI95 [0.3985, 0.4233]. Slightly below 3ep — the epoch curve peaks around 3; 5ep (26660) pending |
| **sft-27b-80k-5ep-global** | Qwen3.8-27B + v1 SFT @80k, 5 epochs (step-790) | 0.4019 | 0.1978 | 0.1758 | job 26660; CI95 [0.3896, 0.4141]. Epoch curve complete: 2/3/4/5 ep = 0.3621/**0.4196**/0.4108/0.4019 (error 0.2425/0.1708/0.1863/0.1978) — clean peak at 3 epochs, monotone overfit after. **3ep is the final 27B SFT champion** |
| **rl-27b-3ep-step40-global** | 27B 3ep SFT + KL-GRPO round-3, step 40/124 | 0.4162 | 0.1733 | 0.1823 | job 26679; CI95 [0.4039, 0.4286]. Flat vs the 3ep SFT (0.4196/0.1708/0.1848) — RL is not (yet) adding to the stronger base; its Tier-1-teachable headroom is mostly consumed by 3ep SFT (train rewards start 0.45-0.7 vs 0.36-0.5 on the 2ep base). Run continues; next eval at step 80 |
| **rl-27b-3ep-step60-global** | 27B 3ep SFT champion + KL-GRPO step 60/124 | 0.4132 | 0.1786 | 0.1795 | job 26697; CI95 [0.4003, 0.4251]. Strong-base RL series: SFT 0.4196 → step40 0.4162 → step60 0.4132 — mild downward drift within noise, no gain. Remaining checkpoints will be left to the run's end; only the final gets scored (borrow GPU economy) |
| **sft-gemma12b-v1-global** | gemma-4-12B-it + v1 SFT 2ep @80k (sdpa, r16) | **0.1792** | 0.6394 | 0.0851 | jobs 26662 (train, 308 steps) + 26708 (eval); CI95 [0.1679, 0.1897] vs base 0.1426/0.6578 — **+3.7 orch (significant)**, error −1.8. Base loaded via snapshot path (offline hub lookup failed); arch Gemma4UnifiedForConditionalGeneration; merge 328/331 lora_B nonzero. TRL RL to follow once a node frees (after the 27B sweep) |
| **rl-27b-3ep-step124-global** | 27B 3ep SFT champion + KL-GRPO step 124/124 (final) | 0.4114 | 0.1938 | 0.1826 | job 26746; CI95 [0.3992, 0.4241]. Strong-base RL series complete: SFT 0.4196 → 40: 0.4162 → 60: 0.4132 → 124: 0.4114 — monotone mild decline (−0.8 total, at the noise edge but consistently downward); error drifts back above opus. **Verdict: Tier-1-reward RL helps a weak base (+1.5 on the 2ep-64k SFT) and hurts a strong one — the 27B final model is the 3ep SFT (0.4196)** |
| **rl-4b-v1-kl-step20-global** | Qwen3-4B v1 SFT (0.2546) + KL-GRPO step 20 (borrow, thrice preempted) | 0.2495 | 0.4050 | 0.0978 | job 26773; CI95 [0.2387, 0.2599] — flat vs the v1 SFT (n.s.). Matches the project-wide pattern: RL with the Tier-1 reward lifts a weak base (4B v2 +1.2, 27B 2ep +1.5) and does nothing for a well-trained v1 base. Only 20 steps survived borrow preemption; 4B headline stays SFT 0.2546 |
| **sft-27b-3ep-r64-global** | 27B v1 SFT @80k, native 3ep cosine, **LoRA r64/α128** (sweep A) | **0.4217** | **0.1339** | 0.1826 | job 26802; CI95 [0.4097, 0.4334] vs 3ep-r16 champion 0.4196/0.1708/0.1848 — orch +0.2 (noise), **error −3.7 (0.1339, far below opus 0.1916)**, final −0.2 (noise). Higher LoRA capacity yields cleaner plans, not more correct ones. New 27B headline on orch-tie + best error: `merged-27b-3ep-r64` |
| **sft-27b-3ep-lr2e4-global** | 27B v1 SFT @80k, native 3ep cosine, r16, **lr 2e-4** (sweep B) | 0.3857 | 0.1724 | 0.1627 | job 26817; CI95 [0.3742, 0.3981] — **−3.4 orch vs the 1e-4 champion (significant); doubling the LoRA lr hurts**. Since (A) at lr 1e-4 on the same native schedule matched 0.42, the schedule is fine and the lr is the culprit |
| **rl-4b-v1-kl-step60-global** | Qwen3-4B v1 SFT + KL-GRPO step 60 (4B RL final; borrow preemption ended the run at 62) | **0.2716** | **0.3612** | 0.1071 | job 26834; CI95 [0.2602, 0.2824] vs v1 SFT 0.2546 — **+1.7 orch (significant), error −4.9**. The step-20 checkpoint was flat; the gain appears by step 60. New 4B headline: `rl/merged_rl/4b-v1-kl-step60` |
| **sft-27b-80k-3ep-replan** | headline 27B (r16 3ep) in **replan** mode | 0.4208 | 0.1720 | 0.1876 | job 26832 (resumed a pre-existing 3,220-task lane); CI95 [0.4086, 0.4325]; 5,207 review turns, 153 accepted / 1,042 rejected replans. ≈ global (0.4196): replan adds +0.1 orch / +0.3 final — global-only training transfers to the replan protocol without loss, and the mid-course revision itself barely moves the score (consistent with the earlier replan-ladder finding). One recipe exceeded the pinned 122,880-token context (LLMError, counted as error — same limit for all models) |
| **sft-27b-80k-3ep-react** | headline 27B (r16 3ep) in **react** mode | 0.5112 | 0.0121 | 0.3016 | job 26833 (resumed a pre-existing lane); CI95 [0.4994, 0.5236]; n_scored 3,181. vs base 27B react 0.5331 / final 0.3177 → **−2.2 orch, −1.6 final**: global-only SFT slightly HURTS the interactive react mode (opus react: 0.6352 / 0.4714). Contrast replan: base 0.2939 → ours 0.4208 (**+12.7**). Training transfers to the plan-shaped interactive protocol, not to free-form tool-by-tool acting — an honest limitation of global-only data |
| **sft-27b-80k-3ep-local** | headline 27B (r16 3ep) in **local** (incremental_workflow) mode | 0.2861 | 0.4696 | 0.1295 | job 26927 (resumed a pre-existing lane); CI95 [0.2735, 0.2984]. vs base 27B local 0.3276 / err 0.327 / final 0.147 → **−4.2 orch, error +14**: global-only SFT clearly HURTS the local (incremental) mode. Mode-transfer summary for the headline model: global +13.4, replan +12.7, react −2.2, local −4.2 — training helps only the plan-shaped protocols. An honest limitation to report; mixing local/react-mode data is the obvious future fix |
| **rl-gemma12b-final-global** | gemma-4-12B v1 SFT + TRL GRPO step 460/992 (48 h limit) — **final 12B model** | **0.2166** | **0.5276** | 0.0854 | jobs 26824 (train) + 26963 (eval); CI95 [0.206, 0.227] vs SFT 0.1792 [0.168, 0.190] — **+3.7 orch (significant), error −11.2**. Base 0.1426 → 1.5x. Same pattern as the 26B (+4.0): gemma SFT bases have RL headroom. Launch ladder (Unified decoder-layer class, Slurm env-export hold, vLLM multimodal-embedder sync) documented above |
| **rl-gemma26b-step180-global** | gemma-26B v1 SFT + TRL GRPO 180/992 steps | **0.2052** | 0.5543 | 0.0814 | job 26594; CI95 [0.1948, 0.2157] vs SFT 0.1989 [0.1881, 0.2097] — +0.6 pts, CIs overlap (NOT significant); error 0.5661→0.5543. First gemma RL data point at 18% of the run; later checkpoints to follow |
| **rl-gemma26b-step680-global** | gemma-26B v1 SFT + TRL GRPO step 680/992 — **final 26B RL model** | **0.2393** | **0.4823** | 0.0935 | job 26634; CI95 [0.2279, 0.2505] vs SFT 0.1989 [0.1881, 0.2097] — **+4.0 orch, CIs fully separated (significant); error −8.4** (0.5661→0.4823). The largest RL gain of the project; the gain grew with steps (step-180 +0.6 n.s. → step-680 +4.0). Run 26583 hit its 48 h limit at 680/992; step-680 is the last checkpoint. 26B RL now exceeds the 31B SFT (0.1955) |
| **rl-gemma31b-step40-global** | gemma-31B v1 SFT + TRL GRPO step 40 (thin run) | 0.1910 | 0.5655 | 0.0922 | job 26653; CI95 [0.1798, 0.2013] vs SFT 0.1955 [0.1849, 0.2056] — **no gain (n.s.)**, as pre-caveated: 40 steps x 131 prompts with completions capped at 3072 (the dense 31B's memory boundary, see the OOM ladder). Honest negative result; the 31B headline remains its SFT (0.1955) |
| **sft-gemma31b-global** | gemma-4-31B + **v1** SFT 1ep @64k | **0.1955** | 0.5717 | 0.0978 | jobs 26434 (train) + 26492/26496/26520 (eval, twice preempted, resumed); CI95 [0.1849, 0.2056]. Base 0.1271 → +6.8 pts (1.5x). Caveat: trained on only 1,381/2,711 rows (the 64k-cap subset under the gemma tokenizer) — the 4B v1-2ep run (0.2546) beats it, consistent with the coverage gap |

## Incidents (kept for honesty and reproducibility)

1. **Merge no-op (2026-08-25)**: PEFT adapters trained on the
   AutoModelForCausalLM view (`model.layers.*`) silently fail to attach to
   Qwen3_5ForConditionalGeneration (`model.language_model.layers.*`) — all 496
   lora_B loaded zero, merge_and_unload merged nothing. The two VOID evals
   above scored base weights (identical plans across 649 recipes proved it).
   Fix: `merge_adapter.py` merges on the training class then transplants
   tensors into the wrapper shards; hard-fails on zero-loaded lora_B or zero
   changed tensors. Do not trust file hashes; verify tensors.
2. **Silent gradient-checkpointing no-op**: requires `model.train()`;
   without it 8k tokens OOM'd 139GB.
3. **fla kernels required** for Qwen3.8 linear-attention layers; the pure
   torch fallback OOMs at 8k tokens.
4. **gemma-4 template**: generation prompt appends an empty thought channel
   (`<|channel>thought\n<channel|>`) when thinking is disabled; training
   sequences are built as exact inference context + continuation.
5. cl100k token estimates mis-filter rows (±20% per row vs real tokenizers);
   all filtering now uses the target model's tokenizer.

## RL (GRPO) pipeline — VALIDATED 2026-08-26

Smoke (job 26390, 4B base, 8 prompts, n=4, 1 GPU) COMPLETED: rollout →
custom symbolic-match reward (rl/reward.py) → GRPO update, 2 optimizer steps,
base-model val reward 0.205. Stack: `.venv-rl` (verl 0.9.0, transformers
5.10.4, vllm 0.27.1, flash-attn 2.8.3 built on-node with the cu13 wheel
toolchain, TransferQueue installed but v0 runner used).

Required non-defaults (all in rl/run_grpo.sbatch):
- `trainer.use_v1=False` (V1 TransferQueue runner hangs single-node)
- `ray_kwargs.ray_init.num_cpus=$SLURM_CPUS_PER_TASK` (default ray.init
  autodetects 192 cores vs cgroup quota and hangs in CoreWorker connect)
- `reward.custom_reward_function.{path,name}` (new-style key; the legacy
  top-level `custom_reward_function.*` is silently ignored by the reward loop)
- `unset ROCR_VISIBLE_DEVICES` (slurm exports it on NVIDIA nodes; verl refuses)
- kill stale ray daemons + per-job RAY_TMPDIR before launch
- flash-attn is a hard dependency of the log-prob no-padding path; build with
  `CUDA_HOME=<torch cu13 wheel dir> MAX_JOBS=6` (MAX_JOBS=24 gets OOM-killed)

Reward: `rl/reward.py` Tier-1 symbolic match (valid .15 / tools .25 / args
.35 / struct .15 / exact .10); self-test golden=1.0, truncated=0. Data:
`rl/make_rl_dataset.py` → data_rl/ (1,000 shortest prompts + 46 eval).
Tier-2 (fixture-replay execution reward on the 5 recorded variants/recipe)
is the planned upgrade.

### 27B GRPO smoke series (why smokes are mandatory before production)

Each fix below was found by a 4-GPU/20-min smoke and would otherwise have
sunk an 8-GPU multi-day production run. All applied to `run_grpo.sbatch` /
the production override set:

| job | failure | fix |
|---|---|---|
| 26400 | vLLM KV cache doesn't fit 27B at TP1/util .5 | `rollout.tensor_model_parallel_size=2` |
| 26402 | vLLM custom all-reduce CUDA crash at TP2 | `+rollout.engine_kwargs.vllm.disable_custom_all_reduce=True` |
| 26409 | **val reward 0.0 — silent**: verl default chat template leaves Qwen thinking ON, every rollout unparseable; plus FSDP1 offload assert (torch 2.13 flat-param) | `+data.apply_chat_template_kwargs.enable_thinking=False` → reward jumped to 0.496; also removed expandable_segments for RL |
| 26411 | actor update OOM: 4×6144-token responses × 248k vocab fp32 logits (22.4GB) | long-seq memory work below |
| 26412/26415 | `model.use_fused_kernels=True` correlates with val reward 0.0 (side effect) and saves nothing | flag rejected |
| 26414 | FSDP1 offload assert again | `actor.strategy=fsdp2` (passes) |
| 26416 | (running) backward OOM from full-vocab logits | `entropy_from_logits_with_chunking` + `entropy_checkpointing` + dynamic-bsz 73728 + ulysses SP2 |

The 26409 case is the honesty argument in miniature: without the step-0
validation reward, a production run would have trained on garbage for days
while looking healthy. Every production config must show a sane step-0
val reward before launch.

Continued smoke series (2026-08-27, reopening the 27B path):

| job | failure | fix |
|---|---|---|
| 26447 (v18) | fused kernels (torch backend) + fsdp2, no offload: step-0 val 0.265 passes, training step crashes `AttributeError: 'FSDPParam' object has no attribute '_unsharded_param'` | root-caused below |
| 26479 (v19) | same crash with `fused_kernel_options.impl_backend=triton` — proves it is not the fused-kernel compile path | root-caused below |
| 26481 (v20) | patched torch: `_unsharded_param` crash GONE; training step now OOMs by 564MB (132GB allocated; vLLM correctly asleep at 4.8GB — actor alone: ~61GB sharded param/optim + ~38GB boundary activations at the 57k token cap). Token cap has no headroom: even the 1000-shortest RL prompts are ~50-68k tokens, so one packed sequence ≈ the cap | memory levers below |
| 26482 (v21) | fsdp2 `offload_policy=True` (CPU Adam): `AssertionError` in the triton kernel — `self.lm_head.weight` reaches the fused kernel as the CPU sharded param. Confirms fused-kernels x CPU-offload conflict is backend-independent; route closed | text-only ckpt |
| 26483 (v22) | text-only checkpoint (`merged-final-textonly`, 26.9B `Qwen3_5ForCausalLM` — wrapper minus the ~3B never-executed visual+mtp, exported via `export_textonly.py`, same AutoModelForCausalLM load path as SFT so weights byte-identical): dtype `AssertionError` in the triton kernel — verl dispatches model_type `qwen3_5_text` to the generic `dense_common` forward, which lacks the qwen3_5 forward's dtype-cast/DTensor handling AND skips the GDN sequence-packing patches (correctness risk under rmpad). Text-only route parked | back to wrapper |
| 26484 (v23) | wrapper + `enable_activation_offload=True`: `AssertionError` in `activation_offload.py tensor_pop` — saved-tensor tag bookkeeping incompatible with qwen3_5's custom GDN/fla autograd ops. Route closed | ulysses SP |
| 26487 (v24) | wrapper + v20 config + `ulysses_sequence_parallel_size=2`. Rationale: measured real token lengths (exact tokenizer): smoke max prompt 49,632; **production data_rl max 66,642, p90 58,256, median 53,702** → production needs a ~70k token cap, +23% activations over the smoke that was 564MB short — cap-trimming can't save production, only halving activations can. Result: cuDNN INTERNAL_ERROR in backward (masked OOM — expandable_segments mapping failures in log; verl's fsdp2 engine enables expandable_segments itself) | discriminating run v25 |
| 26488 (v25) | SP2 + cap 53,760: OOM at 130.5GB vs v20's 132.4GB at cap 57,344 — the ~1.8GB saved is exactly the cap reduction, **SP2 contributes nothing** (original "SP inert for qwen3_5" conclusion stands, even with fused kernels). Note Adam's ~30GB isn't even allocated yet at the backward-peak crash. **Full-param 27B GRPO on 8xH200 is infeasible; route formally closed** | LoRA RL |
| 26489/26490 (v26 a/b) | LoRA RL config errors: hydra chokes on unquoted regex parens; `layered_summon` requires `rollout.load_format=safetensors` | both fixed |
| **26491 (v26c)** | **COMPLETED — 27B RL UNBLOCKED.** LoRA RL (r16/alpha32 all-linear, `exclude_modules='.*(visual\|mtp).*'`, `layered_summon=True`, `load_format=safetensors`, lr 1e-5, fused triton, fsdp2, no offload): val 0.265, 2 GRPO steps, clean exit in 19:52. **Peak 63.9GB allocated / 68.9GB reserved** (vs 132GB full-param) — 70GB headroom covers the production 71,680 cap. grad_norm 0.14-0.16, pg_loss sane, rollout rewards mean 0.65-0.75 (max 1.0) | production launched |

**27B GRPO production: job 26494** `grpo-27b-lora-prod-v1data` (launched
2026-08-28 ~01:5x). v26c config at cap 71,680, **data_rl_v1** (rebuilt from
data_v1_files — the original data_rl was built from v2-canonicalized prompts,
a style mismatch with both the v1-trained SFT champion and the raw-card
benchmark; ablation showed that style gap is worth 4.5 pts). 1,000 prompts x
2 epochs, bsz 16, n=8, test_freq 10, save_freq 20 → 125 steps, est. ~1.5-2
days. Job 26493 (v2-prompt data) cancelled ~40 min in, superseded.

**Production restart #2 (2026-08-28 ~14:40): job 26524 `grpo-27b-lora-v1-kl`.**
26494's val reward declined monotonically then flatlined below its own start
(step 0/10/20/30/40 = 0.541/0.538/0.534/0.504/0.504) while train rewards
rose — textbook unanchored policy drift (lr 1e-5, no KL). Cancelled at step
~41 (13h; step-20/40 LoRA checkpoints banked under
rl/checkpoints/agentorch-grpo/grpo-27b-lora-prod-v1data/). Restarted from the
SFT policy with `use_kl_loss=True, kl_loss_coef=0.001` (in LoRA mode the ref
policy is the adapter-disabled base — no extra memory) and lr 3e-6.
Decision criterion, recorded before the restart: a KL-anchored run cannot
lose the ~3.7 pts the first 30 unanchored steps gave up.

**gemma RL route decision (2026-08-29)**: verl 0.9 rejected for gemma-4
after three smokes (all user-submitted, merged-gemma31b): 26531 host-RAM OOM
at worker init (8 workers x fp32 31B), 26541 vLLM engine-core init failure
(DistNetworkError) with --mem=0, 26553 `FlashAttention forward only supports
head dimension at most 256` in the log-prob path — an architecture-level wall
(gemma-4 head_dim > 256; same one that forced sdpa in SFT). gemma RL uses TRL
GRPOTrainer (`rl/trl_gemma/`): LoRA r16/a32 on the v1-SFT merges, colocate
vLLM, Tier-1 reward reused, beta=0.001 KL anchor, FSDP2 via accelerate
(Gemma4TextDecoderLayer wrap), sdpa. Order: 26B first, then 31B with the
proven config. Smoke: job 26558.

TRL gemma-26B smoke series (2026-08-29, `rl/trl_gemma/`, all 8xH200):
26558 `accelerate` CLI missing in venv bin → `python -m accelerate.commands.launch`;
26576 transformers 5.15 makes gemma4 `head_dim` per-layer, vllm 0.27.1's config
convertor raises `AmbiguousGlobalPerLayerAttributeError` → run in `.venv-rl`
(transformers 5.10.4; trl 1.10.0 installed --no-deps); 26577 colocate vLLM at
TP=1 loads the full 26B on every GPU, no KV room at 0.25 → `vllm_tensor_parallel_size=8`,
util 0.3; 26578 accelerate `fsdp2_load_full_state_dict` assumes every param is
a DTensor (`'Tensor' has no attribute 'device_mesh'`) → `fsdp_cpu_ram_efficient_loading: false`;
26579 reached the first generation step: TRL `_sync_fsdp2_params_to_vllm` calls
`.full_tensor()` on every `state_dict()` entry incl. buffers → local guard patch
(`hasattr(param, "full_tensor")`, original saved `.orig-1.10.0`);
26580 reached the first forward: accelerate's FSDP2 embed/tail carving puts the
tied `embed_tokens` in a tail group and leaves `lm_head` (same Parameter) to the
root group; torch 2.13 raises `Parameter ... is shared with a parameter already
managed by another FSDP group` → local patch to accelerate 1.14.0 `fsdp_utils.py`
adding lm_head to the same group when tied (torch's own error text prescribes
`fully_shard([module_a, module_b])`; original saved `.orig-1.14.0`).
**26581 (v7) COMPLETED — gemma-4 RL unblocked on TRL**: 4 GRPO steps in 21:44
(8 prompts x 4 gens, colocate vLLM TP8), loss/KL/entropy logged (kl ~0.002-0.003,
grad_norm 0.03-0.16), reward mean 0.146 (std 0.26, completions ~1.3k tokens),
checkpoint-4 saved.

**gemma-26B TRL GRPO production: job 26583** `trl-grpo-gemma26b-v1` (launched
2026-08-29 ~01:20): merged-gemma26b-v1 base, data_trl_v1 500 v1 prompts x 2 epochs,
8 prompts x 8 gens per step (~125 steps), LoRA r16/a32, lr 1e-5, beta 0.001,
max_completion 4096, colocate vLLM TP8 @0.3, save every 20 steps. No in-loop val
(TRL script has none); checkpoints go through the frozen benchmark eval instead.

**RL progress snapshot (2026-08-29 ~18:00)**
- 27B KL-GRPO (26524): 71/124. val (47 prompts, Tier-1 reward) at steps
  0/10/.../70 = 0.527/0.529/0.531/0.523/0.527/0.549/0.518/0.521 — flat within
  the ±0.015 noise band, no sustained gain. verl checkpoints global_step_20/40/60
  (FSDP-sharded full state, 8x13GB). `rl/merge_verl_ckpt.sbatch` converts them on
  a compute node (login-node RAM 125GB < 104GB shards + overhead: the first
  attempt died silently) — step-60 conversion job 26592.
- gemma-26B TRL-GRPO (26583): 194/992 optimizer steps (=~24 GRPO rounds);
  reward mean by window 0.14 → 0.09 → 0.22 → 0.20 → 0.19 → 0.16, KL 0.003-0.005;
  five soft allocator-OOM warnings (recovered each time). Checkpoints every 20
  steps are accelerate DCP shards holding LoRA params only (83MB);
  `rl/trl_gemma/export_adapter.py` converts them to PEFT adapters
  (checkpoint-180 → 470 tensors, 235/235 lora_B nonzero) → `merge_simple.py`
  → frozen benchmark eval. Merge must run in `.venv-rl` (the training env):
  `.venv-train`'s transformers 5.15 wraps some gemma4 linears as
  `Gemma4ClippableLinear`, which PEFT 0.20 refuses as a LoRA target.

**4B RL on the v1 base: job 26595** `grpo-4b-v1-kl` (2026-08-29, borrow QOS —
qos quota is held by the 27B and 26B runs; preemptions are survivable via the
20-step checkpoints). Base `merged-abl-v1` (v1 SFT 2ep, 0.2546), data_rl_v1,
prior 4B production config (full-param, bsz 16, n=8, dyn-bsz 73728, util 0.6)
plus the KL anchor (use_kl_loss, coef 0.001) now standard across models. The
existing 4B RL number (0.2047, +1.2 over its v2 SFT base) stays as a v2-era
data point; this run gives the v1-consistent one.

**Tier-2 execution-replay reward — probed and parked (2026-08-30)**
Goal: align the RL objective with the benchmark's orchestration metric by executing
generated plans instead of symbolic matching. Findings (`rl/tier2/`):
- The benchmark's native simulator cannot seed training recipes: every benchmark
  recipe has a hand-written seeder/verifier (`benchmark.seed_recipe`,
  `benchmark.verifier.verify_<id>`); training recipes raise
  `recipe <id> has no registered seeder` (probe_golden.py, 100/100 variants).
- The only execution path is the training pipeline's expectation-driven
  scripted tools (golden observations from `expect.tool_expectations`; only 60%
  of expectations carry a result dict). `probe_scripted.py` runs the benchmark's
  own symbolic plan executor (`task.runner.AgentRunner._run_symbolic`) against
  such a registry: fast (14 ms/variant) but **golden plans reach full trace
  parity on only 6/100 variants** (tool_selection 16%, order 16%, execution
  36%, arguments 6%).
- Root cause: golden WorkflowPlans use the public task-description tool
  surface (`workato_runtime.declare_variable`, `slack.post_message`,
  `salesforce.search_records`, ...) while `expect` traces use raw connector
  names (`workato_variable.declare_variable`, `slack_bot.post_bot_message`,
  `salesforce.get_custom_object`, `workato_genie.workflow_return_result`).
  The benchmark bridges this with `_task_description_public_gold_projection`
  and stage-07 groundtruth/critic/scoring-registry artifacts that exist only
  for the 650 benchmark recipes; the training corpus stops at stage 06.
- Verdict: an execution reward built now would penalize correct plans (94%
  false negatives on gold). Regenerating stage-07 projections for 1,000
  training recipes is a multi-day pipeline effort with uncertain fidelity —
  out of scope for this cycle; recorded as future work. Tier-1 stays.
- Follow-up (same day, user pointed at `task_description/`): the training
  replay reports (`input_recipes/_execution/<rid>/variant_XX.json`) already carry
  the executed trace in the PUBLIC tool vocabulary, so no IR projection is needed
  for tool names — gold-side alignment after normalizing stop/return rows is 97%
  (replay trace is an ordered subsequence of the golden plan's tools). But
  `probe_v3.py` (golden plan → benchmark symbolic executor with observations
  served from the replay trace, 4,339 replay-passed variants, 183 s) reaches
  only **28% full parity** (selection/order 59%, execution 62%, arguments 32%,
  control path 78%). Root cause: ~40% of gold observations are defaults
  (`{"ok": true}`) because training expectations carry no result subset, so
  data-dependent branches resolve differently from the real replay (e.g.
  110073162: gold v1 `search_rows_sql` → `{ok:true}`, plan takes the zoom
  branch the gold skipped). This is a property of the training fixtures (no
  seeded backend state for training recipes), not of the harness. Below the
  90% golden-parity gate set in advance → Tier-2 is closed for this cycle.

**Last lever queued (2026-08-30, user-approved): 27B v1 SFT at 80k context**,
`qwen27b-v1data-80k-2ep` — identical to the champion recipe (v1, 2 ep, LoRA r16,
lr 1e-4) except max-len 65,536 → 81,920, which admits the long rows the 64k cap
dropped (data_v1_files: 2,789 rows). Auto-submitted on the qos node freed when
the 27B RL run (26524) exits; expected ~17-20 h. Honest expectation: +1-2 pts;
it does not change the "not reaching opus this cycle" conclusion.
(Outcome: 0.3621 — confirmed no gain; see eval table.)

**gemma-31B TRL GRPO smoke: job 26616** (2026-08-31, on the qos node freed by
the 27B SFT-80k run). Same recipe as the 26B production (LoRA r16/a32, beta
0.001, colocate vLLM TP8) on `merged-gemma31b` (v1 SFT, 0.1955), with the
dense model's memory in mind: vLLM budget 0.2, prompts capped at 200k chars
(~50k gemma tokens; production set `data_trl_v1_31b` capped at 210k → 500
rows). Order per the user: 26B first (running), then 31B.

**27B RL round-2 — validity-weighted (queued 2026-08-31, user-approved)**:
goal is the one metric within reach of opus — error_rate (RL step-120 0.2224 vs
opus 0.1916). `rl/reward_validity.py` reuses reward.py's machinery with weights
valid .40 / tools .20 / args .25 / struct .10 / exact .05 (self-test: golden
1.0, invalid 0.0, valid-but-wrong 0.5). Run starts from
`merged-27b-rl-kl-step120`, same KL-anchored LoRA config (lr 3e-6, coef 0.001),
1 epoch (~62 steps); auto-submits when the 31B RL (26630) frees its node.
Success criterion: benchmark error_rate < 0.1916 with orch not degrading
beyond noise; if orch collapses, the run is reported as a negative result.

**Fifth model added (2026-08-31, user request): gemma-4-12B-it.** Base global
score EXISTS in results.csv: **orch 0.1426** / error 0.6578 (complete, 3,220
variants; matches the replan-iter iteration-0, confirming provenance). An
initially submitted duplicate base eval (26654) was cancelled once the row was
found — earlier claim that no baseline existed was a misread of truncated grep
output. SFT v1 2ep @80k sdpa queued on qos
(job 26655, `gemma12b-v1data-2ep`; 80k should fit a dense 12B — fall back to
64k if it OOMs like the 31B). Then the standard chain: merge_simple in
`.venv-rl` → snapshot-config restore → eval → TRL GRPO with the 26B recipe.

**Redirection after the 3ep result (2026-09-01)**: the validity-weighted RL
round-2 (26652) was cancelled at step 5/62 — its goal (error < opus) is already
achieved by the 3ep SFT (0.1708 < 0.1916) and its base model (RL step-120,
0.3740) is superseded. The freed node runs **KL-GRPO on the 3ep champion**
(job 26661, `grpo-27b-3ep-kl`, standard Tier-1 reward, lr 3e-6, KL 0.001):
if RL adds its usual +1-1.5, orch lands ~0.43 — within ~3 pts of opus.

**SFT capacity/optimization sweep (queued 2026-09-01, user-approved)** — the
3ep jump showed the model was under-trained, and RL on the strong base adds
nothing, so the remaining levers are in SFT itself. Two single-variable
controls against the 3ep champion (0.4196; note it came from a 5ep cosine
schedule cut at 60%):
- (A) `qwen27b-v1-80k-3ep-r64`: LoRA r64/α128, native 3ep cosine, lr 1e-4
  — auto-submits when the 12B SFT frees its node.
- (B) `qwen27b-v1-80k-3ep-lr2e4`: LoRA r16/α32, native 3ep cosine, lr 2e-4
  — auto-submits when the 3ep-RL run frees its node.
Winner then gets the >6,144-token-target rows re-admitted. Honest expectation
+2-4 total (0.44-0.46), i.e. within reach of opus's 0.4644 but not assured.
**Sweep outcome (2026-09-03)**: (A) r64 = 0.4217 / err 0.1339 (orch tie, error
−3.7); (B) lr 2e-4 = 0.3857 (−3.4, harmful). The SFT orch ceiling with this
data sits at ~0.42 (90.8% of opus); error rate is solved (0.134 vs opus
0.192). **Final 27B model: `merged-27b-3ep-r64`.** Next lever would be data,
not optimization.

Rejected for this cycle: full fine-tune (27B+80k activations exceed 8xH200
without 8-bit Adam / 2 nodes), data expansion (the local pool is exactly the
3,000 recipes already used), further RL (measured no gain on the strong base).

**External benchmarks (2026-09-03)**: `public_benchmark/other_benchmark/` holds
the vendored WorkflowBench (ID/OOD) and Seal-Tools (in/out-domain, 5-cand and
64-tool) suites with upstream scorers; 28 checkpoints were already scored
(168/168 cells, `results/summary.md`, `results/FINDINGS.md`). The four newest
checkpoints — sft-27b-3ep-r64 (final 27B), sft-27b-3ep-lr2e4,
rl-27b-3ep-step124, rl-4b-v1-step20 — were registered as models.json entries
28-31 and generated via array job 26820; scored with the same pipeline.
Outcome (192/192 cells): the final-candidate `sft-27b-3ep-r64` transfers WORSE
than the r16 3ep model — Seal-Tools 5-cand drops are format lock-in (relaxed
0.964/0.961 ≈ base), but the 64-tool out-domain split is a **real** loss:
relaxed 0.756 vs base 0.976 and vs r16-3ep 0.958. Higher LoRA capacity
over-specializes unseen-tool selection. rl-27b-3ep-step124 and lr2e-4 transfer
like r16-3ep (relaxed out64 0.96). Paper framing: **r16-3ep (0.4196) is the
balanced headline model** (orch tie with r64, error beats opus, transfer
preserved); r64 (0.4217 / error 0.134) is the AgentOrch-specialized variant
with a documented −0.22 transfer cost on the hardest external split.

**Closing inventory (2026-09-03)** — what is still running / newly launched:
- 12B TRL RL v4 (26824): training (rewards 0.06→0.15 by step 10); ~8 min/step
  on the dense 12B → the 48 h limit lands near step 360 of 992; checkpoints
  every 20 steps, final scored as with the 26B.
- 4B v1 RL: borrow preemption ended the run at step 62 (4th attempt);
  step-60 checkpoint converted (26831) and scored as the 4B RL final.
- **Non-global modes**: no trained model had been evaluated in the benchmark's
  interactive modes. The headline 27B (`merged-27b-80k-3ep`) is now running in
  `replan` (26832) and `react` (26833) via `run_eval_mode.sbatch` (same frozen
  harness, `--modes` parametrized) to test transfer of global-only training
  to interactive modes — the claim the external-benchmark README says needs
  corroboration.
- Not run and out of scope: τ²-bench (needs an interactive agent adapter);
  resuming the 26B RL past step 680; local mode.

**Data-version audit (2026-08-28)**: v1-trained = 27B champion, gemma-31B
(26434), 4B ablation winner; v2-trained = gemma-26B 0.1255 and 4B-full 0.1929
(+ its RL step-20 0.2047 built on it). For headline consistency all three
models' final numbers should be v1: 27B ✓, 31B ✓, 4B ✓ (use the ablation
run), gemma-26B needs a v1 SFT rerun before its RL.

**Root cause of the `_unsharded_param` crash** (not a verl bug, not a rename):
the merged 27B checkpoint is the Qwen3_5ForConditionalGeneration wrapper and
carries a vision tower (`model.visual.*`, 333 tensors) plus an MTP head
(`mtp.*`, 15 tensors) that text-only GRPO batches never execute. FSDP2 shards
them, they never all-gather, so `FSDPParam._unsharded_param` is never
initialized; the root post-backward pass then touches every param's
`to_accumulated_grad_if_needed` and crashes on the unused ones (only when
`reduce_dtype` is set, i.e. mixed-precision grad reduce — why SFT never hit
it). torch upstream (pytorch main) already fixed exactly this with a
`getattr(self, "_unsharded_param", None)` early-return guard and a comment
describing this scenario. Fix applied 2026-08-27: backported that public
upstream guard into the local torch 2.13.0 install
(`torch/distributed/fsdp/_fully_shard/_fsdp_param.py`, original saved as
`_fsdp_param.py.orig-2.13.0`); semantically a no-op for every other code path.
Also note the earlier fused-kernels "reward 0.0 correlation" (26412/26415) was
spurious — 2-row val noise; v18/v19 with fused kernels validated at 0.265.

**27B GRPO verdict (2026-08-27 morning, after 12 smokes — superseded by the
root-cause above)**: BLOCKED on verl 0.9 at that point. Rollout+reward fully work (val reward 0.23-0.50); the actor side does
not fit: full-param update transient ~129GB regardless of ulysses/chunking
knobs (SP appears inert in this build for this arch), and the LoRA path OOMs
at actor init against resident vLLM engines. Not a data/reward problem.
Fallback executed: GRPO production on Qwen3-4B (job 26431) and gemma-26B-A4B
smoke (26432) — both small-activation models where the same pipeline fits.
27B RL revisit path: verl downgrade to a release with proven long-context
LoRA recipes (~1 day), documented here so nobody mistakes the absence of a
27B RL score for an undisclosed failure.

## Reproduce

```bash
# data
python3 task_description/export_training_global_aligned.py       # v2 export
python3 prepare_dataset.py --max-context 81920                   # data_v2/
# train (per model)
sbatch sbatch_sft.sh --data data_v2/train.jsonl --max-len 81920 --epochs 1 ...
# merge + eval
python3 merge_adapter.py --adapter checkpoints/<run>/final --out checkpoints/<merged>
sbatch run_sft_global_eval.sbatch <merged_abs_path> <run_name>
```
