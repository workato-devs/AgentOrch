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

Model weights are not part of this release. Every published checkpoint is
identified in `results/training.csv` (`checkpoint` column) and
`results/EXPERIMENTS.md`, together with the training job, evaluation run and
the archived `leaderboard.json` in `results/leaderboards/`.
