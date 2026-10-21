#!/bin/bash
#SBATCH --job-name=agentorch-external-eval
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=200G
#SBATCH --time=08:00:00
#SBATCH --output=output/logs/extern-%A_%a.out
#
# Evaluate one model (array index -> harness/models.json entry) on all four
# external splits with a single vLLM engine load.
#
#   cd training && sbatch --array=0-33 src/external_eval/harness/run_external_eval.sbatch
#
# Model paths in models.json may use ${HF_HOME} and ${TRAIN_ROOT}; they are
# expanded here. Resumable: rerunning an array task skips task_ids already
# present in generations.jsonl.
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../../../scripts/_preamble.sh"
BASE="$TRAIN_ROOT/src/external_eval"
PY="$AGENTORCH_PYTHON"
cd "$BASE"

export TRANSFORMERS_OFFLINE=1
export VLLM_USE_FLASHINFER_SAMPLER=0
if [[ -n "${AGENTORCH_CUDA_HOME:-}" ]]; then
  export CUDA_HOME="$AGENTORCH_CUDA_HOME"; export PATH="$CUDA_HOME/bin:$PATH"
  export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}$CUDA_HOME/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
fi

IDX=${SLURM_ARRAY_TASK_ID:?array index required}
read -r MODEL_ID MODEL_DIR TP < <("$PY" -c "
import json, os
m = json.load(open('harness/models.json'))[$IDX]
print(m['model_id'], os.path.expandvars(m['path']), m['tp'])
")

echo "=== [$IDX] $MODEL_ID"
echo "=== dir: $MODEL_DIR"
echo "=== node: $(hostname)  job: ${SLURM_JOB_ID}  started: $(date -Is)"

exec "$PY" harness/generate.py \
  --model-id "$MODEL_ID" \
  --model-dir "$MODEL_DIR" \
  --tp "$TP" \
  --task tasks/workflowbench_id_test.jsonl \
          tasks/workflowbench_ood_dev.jsonl \
          tasks/sealtools_test_in_domain.jsonl \
          tasks/sealtools_test_out_domain.jsonl \
          tasks/sealtools_test_in_domain_64.jsonl \
          tasks/sealtools_test_out_domain_64.jsonl
