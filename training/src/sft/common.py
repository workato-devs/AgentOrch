"""Shared helpers for the AgentOrch training code (paths, token counting)."""

from __future__ import annotations

import os
from pathlib import Path

# training/ is two levels above this file (training/src/sft/common.py).
TRAIN_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = TRAIN_ROOT / "data"
OUTPUT_ROOT = TRAIN_ROOT / "output"

# Default SFT messages file produced by src/data/build_sft_messages.py from
# training/input + training/groundtruth (v1 data, used by every headline run).
SFT_MESSAGES_V1 = DATA_ROOT / "sft_messages_v1.jsonl"

TOKENIZER_MODEL = os.environ.get("AGENTORCH_TOKENIZER", "Qwen/Qwen3.8-27B")


def make_token_counter():
    """Count tokens with the selected base model's tokenizer."""
    from transformers import AutoTokenizer

    revision = model_revision(TOKENIZER_MODEL)
    tok = AutoTokenizer.from_pretrained(TOKENIZER_MODEL, revision=revision)

    def count(text: str) -> int:
        return len(tok(text, add_special_tokens=False).input_ids)

    return count, f"{TOKENIZER_MODEL} tokenizer"


def row_tokens(messages: list[dict], count) -> int:
    return sum(count(m["content"]) for m in messages)


def model_revision(model: str, requested: str | None = None) -> str | None:
    """Resolve a base model version for training, tokenization, and merging."""
    import json

    if Path(model).is_dir():
        return None
    if requested or os.environ.get("HF_MODEL_REVISION"):
        return requested or os.environ["HF_MODEL_REVISION"]
    pins = json.loads((Path(__file__).parent / "base_models.json").read_text())
    return pins.get(model, {}).get("revision")
