# Training experiments

All results use the canonical AgentOrch evaluator with the simulated backend
and all 3,220 benchmark variants. Scores below are proportions in `[0, 1]`.
The [source table](training.csv) includes confidence intervals and hyperparameters.

## Training protocol

SFT learns serialized complete workflows using LoRA and loss on the assistant
response. GRPO uses a symbolic-match reward without executing sampled workflows
during training. Qwen runs use verl; Gemma runs use TRL. Data preparation,
training commands, checkpoint merging, and environment configuration are in
the [training guide](../README.md).

The reported Qwen3.8-27B SFT checkpoint is step 474 from a five-epoch cosine
schedule. It corresponds to three passes through the prepared data.
A separate three-epoch schedule follows a different learning-rate curve.

## Checkpoint comparison

| Checkpoint | Mode | Data | SFT epochs | LoRA | SFT LR | Orchestration | Final | Error rate |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| sft-27b-3ep-r64 | global | v1 | 3 | r64/a128 | 1e-4 | 0.4217 | 0.1826 | 0.1339 |
| sft-27b-80k-3ep | global | v1 | 3 | r16/a32 | 1e-4 | 0.4196 | 0.1848 | 0.1708 |
| sft-27b-80k-4ep | global | v1 | 4 | r16/a32 | 1e-4 | 0.4108 | 0.1832 | 0.1863 |
| sft-27b-80k-5ep | global | v1 | 5 | r16/a32 | 1e-4 | 0.4019 | 0.1758 | 0.1978 |
| sft-27b-3ep-lr2e4 | global | v1 | 3 | r16/a32 | 2e-4 | 0.3857 | 0.1627 | 0.1724 |
| sft-27b-80k-2ep | global | v1 | 2 | r16/a32 | 1e-4 | 0.3621 | 0.1655 | 0.2425 |
| sft-27b-64k-2ep | global | v1 | 2 | r16/a32 | 1e-4 | 0.3594 | 0.1596 | 0.2388 |
| sft-27b-v2-1ep | global | v2 | 1 | r16/a32 | 1e-4 | 0.3092 | 0.1382 | 0.3317 |
| rl-27b-3ep-step40 | global | v1 | 3 | r16/a32 | 1e-4 | 0.4162 | 0.1823 | 0.1733 |
| rl-27b-3ep-step60 | global | v1 | 3 | r16/a32 | 1e-4 | 0.4132 | 0.1795 | 0.1786 |
| rl-27b-3ep-step124 | global | v1 | 3 | r16/a32 | 1e-4 | 0.4114 | 0.1826 | 0.1938 |
| rl-27b-kl-step120 | global | v1 | 2 | r16/a32 | 1e-4 | 0.374 | 0.1705 | 0.2224 |
| rl-27b-kl-step60 | global | v1 | 2 | r16/a32 | 1e-4 | 0.3706 | 0.1643 | 0.2165 |
| rl-27b-kl-step80 | global | v1 | 2 | r16/a32 | 1e-4 | 0.3702 | 0.1708 | 0.2211 |
| rl-27b-kl-step100 | global | v1 | 2 | r16/a32 | 1e-4 | 0.3641 | 0.1674 | 0.2292 |
| sft-27b-80k-3ep | replan | v1 | 3 | r16/a32 | 1e-4 | 0.4208 | 0.1876 | 0.172 |
| sft-27b-80k-3ep | react | v1 | 3 | r16/a32 | 1e-4 | 0.5112 | 0.3016 | 0.0121 |
| sft-27b-80k-3ep | local | v1 | 3 | r16/a32 | 1e-4 | 0.2861 | 0.1295 | 0.4696 |
| sft-4b-v1-2ep | global | v1 | 2 | r16/a32 | 1e-4 | 0.2546 | 0.1078 | 0.4099 |
| sft-4b-v2-2ep | global | v2 | 2 | r16/a32 | 1e-4 | 0.2096 | 0.087 | 0.4807 |
| sft-4b-v2-1ep | global | v2 | 1 | r16/a32 | 1e-4 | 0.1929 | 0.0804 | 0.5733 |
| rl-4b-v1-step60 | global | v1 | 2 | r16/a32 | 1e-4 | 0.2716 | 0.1071 | 0.3612 |
| rl-4b-v1-step20 | global | v1 | 2 | r16/a32 | 1e-4 | 0.2495 | 0.0978 | 0.405 |
| rl-4b-step20 | global | v2 | 1 | r16/a32 | 1e-4 | 0.2047 | 0.0761 | 0.5335 |
| sft-gemma26b-v1-2ep | global | v1 | 2 | r16/a32 | 1e-4 | 0.1989 | 0.0845 | 0.5661 |
| sft-gemma26b-v2-1ep | global | v2 | 1 | r16/a32 | 1e-4 | 0.1255 | 0.0512 | 0.6938 |
| rl-gemma26b-step680 | global | v1 | 2 | r16/a32 | 1e-4 | 0.2393 | 0.0935 | 0.4823 |
| rl-gemma26b-step180 | global | v1 | 2 | r16/a32 | 1e-4 | 0.2052 | 0.0814 | 0.5543 |
| sft-gemma31b-v1-1ep | global | v1 | 1 | r16/a32 | 1e-4 | 0.1955 | 0.0978 | 0.5717 |
| rl-gemma31b-final | global | v1 | 1 | r16/a32 | 1e-4 | 0.191 | 0.0922 | 0.5655 |
| sft-gemma12b-v1-2ep | global | v1 | 2 | r16/a32 | 1e-4 | 0.1792 | 0.0851 | 0.6394 |
| rl-gemma12b-final | global | v1 | 2 | r16/a32 | 1e-4 | 0.2166 | 0.0854 | 0.5276 |

## Findings

- The Qwen3.8-27B epoch sweep reaches its highest reported r16 score at the
  three-pass checkpoint; the four- and five-pass checkpoints score lower.
- Increasing LoRA rank to r64 gives a similar AgentOrch score but weaker
  Seal-Tools transfer than the selected r16 checkpoint.
- On Qwen3-4B, the v1 data configuration outperforms the v2 configuration.
- GRPO improves several SFT bases, with the largest reported gain on
  Gemma-4-26B-A4B. It does not improve the selected Qwen3.8-27B SFT model.
- Global-only training improves the 27B Global and Replan scores while
  reducing its ReAct and Local scores.

Checkpoint sweeps were evaluated on the benchmark and used in selecting
reported checkpoints. These comparisons are not results from a separate
hidden model-selection test.

## Reproduction details

Base model versions are recorded in
[base_models.json](../src/sft/base_models.json). The trainer records its
seed, arguments, and library versions in `train_config.json`. Prepared-data
budgets and per-checkpoint settings are in [training.csv](training.csv).
Required RL library fixes are included as
[patches](../src/rl/patches/README.md).

Qwen wrapper checkpoints require the dedicated merge utility so that
adapter weights attach to the correct text-model tensors. Gemma training
uses SDPA; the 31B configuration uses a smaller context budget and a smaller
subset of the source recipes. See the training guide for commands.

External transfer results are in [external/](external/summary.md).
