# Slurm evaluation

From the repository root, select an environment containing the dependencies
in `benchmark/requirements-api.txt` or `benchmark/requirements.txt`:

```bash
cp benchmark/reproduction/cluster/env.sh.example benchmark/reproduction/cluster/env.sh
mkdir -p benchmark/outputs/slurm_logs
sbatch benchmark/reproduction/cluster/run_evaluation.sbatch \
  compat:my-served-model my-model plan_execute,react
```

Edit `env.sh` to select your interpreter. Configure model endpoints or provider
credentials as described in the [evaluation guide](../../README.md).
For local weights, request GPUs with your cluster's `sbatch` options and use
`hf:<org>/<model>` or `hf:/absolute/checkpoint/path`. For example:

```bash
sbatch --gres=gpu:1 benchmark/reproduction/cluster/run_evaluation.sbatch \
  hf:JesseLiu/agentorch-sft-4b-v1-2ep local-model plan_execute,react
```

The optional third argument selects evaluator modes, including
`incremental_workflow` (Local) and `global_input` (Input-Conditioned Global).
Subsequent arguments are forwarded to the evaluator, such as `--ids 64112882`.
Replan uses the complete-workflow revision commands in the evaluation guide.
