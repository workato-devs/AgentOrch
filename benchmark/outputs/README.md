# Evaluation outputs

The evaluator creates these files for each run:

```text
full_eval/<run>/<model>/<mode>/
  results.jsonl        per-variant scores and verdicts
  trajectories.jsonl   execution observations
  leaderboard.json     aggregate metrics and confidence intervals
  artifacts/           workflow and execution artifacts
connector-runtime/     simulator state for connector_runner
slurm_logs/            Slurm output
```

Reported aggregates are stored in `benchmark/results/leaderboards/`.
Run the evaluator to produce per-variant records for a new model.
