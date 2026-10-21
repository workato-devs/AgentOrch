# Reproduction utilities

This directory is deliberately separate from the benchmark execution path.

- `offline/` contains score-audit tools for `results.jsonl` and cached plans
  that already exist. They do not call a model.
- `cluster/` contains optional Slurm launchers and the exact campaign settings
  used for published runs. Direct `python -m evaluation.full_eval` execution
  does not depend on them.

The canonical evaluator always writes `results.jsonl`, `trajectories.jsonl`,
and `leaderboard.json` itself. Cross-model paper table construction is not
part of scoring and is intentionally omitted from the community release.

