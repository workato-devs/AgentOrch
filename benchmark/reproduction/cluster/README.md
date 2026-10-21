# Optional Slurm launchers

These files encode the cluster shapes, model revisions, decoding limits, and
campaign modes used for the reported experiments. They are convenience and
provenance material; the benchmark can be run without Slurm.

From the release root:

```bash
cp benchmark/reproduction/cluster/env.sh.example \
   benchmark/reproduction/cluster/env.sh
$EDITOR benchmark/reproduction/cluster/env.sh

benchmark/reproduction/cluster/small_model/Qwen3-4B-Instruct-2507.sh \
  my-run 1 plan_execute,react
```

The local `env.sh` is ignored by Git. Keep credentials in the release-root
`.env` or another file selected by `AGENTORCH_ENV_FILE`; do not commit them.

