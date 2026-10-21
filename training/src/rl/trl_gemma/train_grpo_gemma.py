"""GRPO on AgentOrch plan generation for gemma-4 models via TRL.

verl 0.9 does not support gemma-4 (no fused/ulysses registry entries; two
smoke attempts died in worker init — see EXPERIMENTS.md), so the gemma RL leg
uses the public TRL GRPOTrainer instead. Same Tier-1 symbolic-match reward as
the verl runs (rl/reward.py), same v1 prompts, LoRA r16/a32 on the v1-SFT
merged checkpoint.

Launch via accelerate (see run_trl_grpo.sbatch).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig
from trl import GRPOConfig, GRPOTrainer

HERE = Path(__file__).resolve().parent
TRAIN_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from reward import compute_score  # noqa: E402  (src/rl/reward.py, veRL signature)


def plan_reward(prompts, completions, golden=None, **kwargs):
    rewards = []
    for comp, gold in zip(completions, golden):
        text = comp[-1]["content"] if isinstance(comp, list) else comp
        rewards.append(compute_score("agentorch_plan", text, gold, None))
    return rewards


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=str(TRAIN_ROOT / "output" / "checkpoints"
                                          / "merged-gemma26b-v1"))
    p.add_argument("--data", type=Path, default=TRAIN_ROOT / "data" / "rl_trl_v1")
    p.add_argument("--run-name", default="trl-grpo-gemma26b-v1")
    p.add_argument("--max-rows", type=int, default=0)
    p.add_argument("--num-generations", type=int, default=8)
    p.add_argument("--batch-prompts", type=int, default=8,
                   help="prompts per GRPO step (generation_batch_size = this * num_generations)")
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--epochs", type=float, default=2.0)
    p.add_argument("--max-completion", type=int, default=4096)
    p.add_argument("--vllm-mem", type=float, default=0.3)
    p.add_argument("--vllm-tp", type=int, default=8,
                   help="colocate vLLM tensor parallel; 1 would put the full model on every GPU")
    p.add_argument("--save-steps", type=int, default=20)
    a = p.parse_args()

    train = load_dataset("json", data_files=str(a.data / "train.jsonl"), split="train")
    if a.max_rows:
        train = train.select(range(min(a.max_rows, len(train))))

    out_dir = TRAIN_ROOT / "output" / "rl_checkpoints" / "trl" / a.run_name
    cfg = GRPOConfig(
        output_dir=str(out_dir),
        run_name=a.run_name,
        num_train_epochs=a.epochs,
        learning_rate=a.lr,
        per_device_train_batch_size=1,
        generation_batch_size=a.batch_prompts * a.num_generations,
        num_generations=a.num_generations,
        max_completion_length=a.max_completion,
        beta=0.001,  # KL anchor to the SFT policy — the 27B run's drift lesson
        bf16=True,
        gradient_checkpointing=True,
        use_vllm=True,
        vllm_mode="colocate",
        vllm_gpu_memory_utilization=a.vllm_mem,
        vllm_tensor_parallel_size=a.vllm_tp,
        logging_steps=1,
        save_steps=a.save_steps,
        save_strategy="steps",
        report_to=["wandb"],
        model_init_kwargs={"attn_implementation": "sdpa", "dtype": "bfloat16"},
    )
    peft_cfg = LoraConfig(r=16, lora_alpha=32, target_modules="all-linear",
                          exclude_modules=r".*(vision|visual).*",
                          task_type="CAUSAL_LM")
    trainer = GRPOTrainer(
        model=a.model,
        reward_funcs=plan_reward,
        args=cfg,
        train_dataset=train,
        peft_config=peft_cfg,
    )
    trainer.train()
    trainer.save_model(str(out_dir / "final"))


if __name__ == "__main__":
    main()
