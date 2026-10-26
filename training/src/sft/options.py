"""Command-line settings for AgentOrch supervised fine-tuning."""

import argparse
import os
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
TRAIN_ROOT = SRC_DIR.parents[1]
DEFAULT_MODEL = "Qwen/Qwen3.8-27B"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--attn-impl", default="sdpa",
                        help="attention implementation (default: sdpa)")
    parser.add_argument("--data", type=Path,
                        default=TRAIN_ROOT / "data" / "sft_v1_80k" / "train.jsonl")
    parser.add_argument("--output", type=Path,
                        default=TRAIN_ROOT / "output" / "checkpoints" / "sft-lora")
    parser.add_argument("--max-len", type=int, default=81_920)
    parser.add_argument("--max-target-tokens", type=int, default=6144)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--grad-accum", type=int, default=None,
                        help="gradient accumulation steps; default preserves a global batch of 16")
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--log-every", type=int, default=1)
    parser.add_argument("--save-every-steps", type=int, default=100)
    parser.add_argument("--wandb-project", default="agentorch-qwen38-sft",
                        help="wandb project; pass '' to disable logging")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--seed", type=int, default=0,
                        help="seeds torch / CUDA RNGs and the data sampler; LoRA init "
                             "and the shuffle order are reproducible, bf16 multi-GPU "
                             "kernels are not bit-exact")
    parser.add_argument("--model-revision", default=os.environ.get("HF_MODEL_REVISION"),
                        help="pinned Hugging Face revision of --model; defaults to "
                             "$HF_MODEL_REVISION, else the entry for --model in "
                             "base_models.json (recorded in train_config.json)")
    parser.add_argument("--deterministic", action="store_true",
                        help="request deterministic kernels (cudnn.deterministic, "
                             "use_deterministic_algorithms warn_only, CUBLAS_WORKSPACE_CONFIG); "
                             "slower, and still not bit-exact across GPU counts or drivers")
    return parser.parse_args(argv)


def accumulation_steps(world_size: int, requested: int | None = None) -> int:
    """Choose accumulation for a 16-sequence effective training batch."""
    if requested is not None:
        if requested < 1:
            raise ValueError("--grad-accum must be positive")
        return requested
    if world_size < 1 or 16 % world_size:
        raise ValueError("The default global batch of 16 requires a GPU count that divides 16")
    return 16 // world_size
