"""Exercise training launchers without loading GPU libraries or models."""

import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def launch_tree(tmp_path):
    training = tmp_path / "training"
    (training / "data").mkdir(parents=True)
    (training / "scripts").mkdir()
    for name in ("src/sft/sbatch_sft.sh", "src/sft/run_benchmark_eval.sbatch",
                 "src/rl/verl/run_grpo.sbatch", "src/rl/trl_gemma/run_trl_grpo.sbatch",
                 "src/rl/trl_gemma/accelerate_fsdp2.yaml",
                 "src/rl/trl_gemma/accelerate_fsdp2_12b.yaml", "scripts/_preamble.sh", "scripts/env.sh.example"):
        dest = training / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "training" / name, dest)
    interpreter = tmp_path / "python"
    interpreter.write_text(f"#!{sys.executable}\n" +
                           "import json, os, sys\n" +
                           "print(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:], "
                           "'offline': os.environ.get('HF_HUB_OFFLINE')}))\n")
    interpreter.chmod(0o755)
    values = {"AGENTORCH_TRAIN_PYTHON": str(interpreter),
              "AGENTORCH_RL_PYTHON": str(interpreter),
              "AGENTORCH_PYTHON": str(interpreter),
              "AGENTORCH_CONDA_BIN": str(interpreter.parent),
              "AGENTORCH_ENV_FILE": str(tmp_path / "absent.env")}
    (training / "scripts/env.sh").write_text("\n".join(
        f"export {key}={shlex.quote(value)}" for key, value in values.items()) + "\n")
    model = training / "output/checkpoints/model"
    model.mkdir(parents=True)
    return training, model


def launch(training, name, *args, extra_env=None):
    env = {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}
    env["SLURM_GPUS_ON_NODE"] = "8"
    env.update(extra_env or {})
    result = subprocess.run(["bash", str(training / name), *args], cwd=training,
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_sft_resolves_explicit_paths_from_training_directory(launch_tree):
    training, _ = launch_tree
    result = launch(training, "src/sft/sbatch_sft.sh", "--data", "data/custom.jsonl",
                    "--output", "output/checkpoints/custom")
    assert result["cwd"] == str(training)
    assert result["args"][-4:] == ["--data", "data/custom.jsonl", "--output", "output/checkpoints/custom"]
    assert str(training / "src/sft/train_sft_local.py") in result["args"]
    assert result["offline"] == "0"


def test_qwen_grpo_uses_the_training_path_and_paper_optimizer(launch_tree):
    training, _ = launch_tree
    result = launch(training, "src/rl/verl/run_grpo.sbatch", "output/checkpoints/model", "custom")
    assert result["cwd"] == str(training)
    args = result["args"]
    for setting in ("actor_rollout_ref.model.path=output/checkpoints/model",
                    "actor_rollout_ref.actor.optim.lr=3e-6",
                    "actor_rollout_ref.actor.use_kl_loss=True",
                    "actor_rollout_ref.actor.kl_loss_coef=0.001",
                    "data.train_batch_size=16", "actor_rollout_ref.rollout.n=8",
                    "data.max_prompt_length=65536", "data.max_response_length=6144"):
        assert setting in args


@pytest.mark.parametrize("config", [None, "accelerate_fsdp2_12b.yaml"])
def test_gemma_grpo_resolves_model_and_accelerate_config(launch_tree, config):
    training, _ = launch_tree
    config_args = ["--accel-config", config] if config else []
    result = launch(training, "src/rl/trl_gemma/run_trl_grpo.sbatch", *config_args,
                    "--model", "output/checkpoints/model")
    assert result["cwd"] == str(training)
    args = result["args"]
    path = Path(args[args.index("--config_file") + 1])
    assert path.is_absolute() and path.is_file()
    assert args[-2:] == ["--model", "output/checkpoints/model"]


def test_checkpoint_evaluation_resolves_model_before_changing_directory(launch_tree):
    training, model = launch_tree
    result = launch(training, "src/sft/run_benchmark_eval.sbatch", "output/checkpoints/model", "evaluation")
    assert result["cwd"] == str(training.parent)
    args = result["args"]
    assert args[args.index("--model") + 1] == f"hf:{model}"


def test_sft_default_batch_remains_sixteen_across_gpu_counts():
    path = ROOT / "training/src/sft/options.py"
    spec = importlib.util.spec_from_file_location("sft_options", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module.parse_args([])
    assert (args.max_len, args.lr, args.lora_r, args.lora_alpha) == (81920, 1e-4, 16, 32)
    for gpus in (1, 2, 4, 8, 16):
        assert module.accumulation_steps(gpus) * gpus == 16
    with pytest.raises(ValueError):
        module.accumulation_steps(3)


def test_direct_grpo_launch_uses_current_environment_without_site_file(launch_tree):
    training, model = launch_tree
    (training / "scripts/env.sh").unlink()
    result = launch(training, "src/rl/verl/run_grpo.sbatch", str(model), "direct",
                    extra_env={"AGENTORCH_RL_PYTHON": str(training.parent / "python")})
    assert result["cwd"] == str(training)
    assert result["args"][:2] == ["-m", "verl.trainer.main_ppo"]
    assert f"actor_rollout_ref.model.path={model}" in result["args"]
