# Optional experiment drivers

These modules implement research ablations built on top of the canonical
evaluator. They are not required for a standard Global View or ReAct model
evaluation.

- `replan_iter.py`: repeated offline plan revision using execution feedback.
- `replan_iter_heldout.py`: the same procedure with separate feedback and
  held-out variants.
- `global_input_selfcheck.py`: CPU integrity check for the Global+Input mode.
- `global_input_status.py`: Slurm campaign progress reporting.
- `compare_replan_v2_smoke.py`, `select_replan_v2_smoke_ids.py`, and the
  fixture directories: smoke-selection and comparison utilities.
- `merge_local_view_shards.py`: merges Local View campaign shards.

For ordinary evaluation, run:

```bash
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-run --backend simulated --model <model> \
  --modes plan_execute,react --variants all --resume
```

