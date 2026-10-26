# Reproduction utilities

`offline/` recomputes aggregate scores from existing evaluation records or
re-executes cached Global plans without model inference. `cluster/` provides
a Slurm entry point for the canonical evaluator.

Run outputs are created by `evaluation.full_eval`. The
[evaluation guide](../README.md) describes setup, protocols, and output files.
