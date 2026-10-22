# output/

Everything a training run produces goes here; nothing in this directory is
committed.

```
output/logs/                       Slurm stdout of the launchers
output/checkpoints/<run>-lora/     LoRA adapters written by src/sft/train_sft_local.py
output/checkpoints/merged-<run>/   merged, benchmark-ready models (src/sft/merge_adapter.py)
output/rl_checkpoints/verl/<run>/  verl GRPO checkpoints (global_step_N/actor)
output/rl_checkpoints/trl/<run>/   TRL GRPO checkpoints (checkpoint-N)
```

Run outputs are kept locally. Downloadable checkpoints are linked in the
[project README](../../README.md#models) and the `hf_repo` column of
`results/training.csv`. The experiment summary and archived aggregates are in
`results/EXPERIMENTS.md` and `results/leaderboards/`.
