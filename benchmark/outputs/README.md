# outputs/

Run outputs land here; nothing in this directory is committed.

```
outputs/full_eval/<run-name>/<model>/<mode>/
  results.jsonl        one scored record per recipe-variant (plan, verdicts, scores)
  trajectories.jsonl   the full simulated execution per variant
  leaderboard.json     the aggregate: primary metrics with bootstrap CIs
  artifacts/           frozen-plan artifacts (planning modes)
outputs/connector-runtime/   mutable simulator state written by the connector runner
outputs/slurm_logs/          Slurm stdout of the launchers in scripts/
```

The aggregates behind every published row are already in
`results/leaderboards/<model>__<mode>.json`, so the tables in `results/` can be
audited without re-running anything. The full per-variant archive (about 80 GB)
is distributed separately; unpack it here and the offline reproduction
commands in the README work unchanged.
