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

# Hosted fine-tuning price per 1M trained tokens by base-model size tier
# (used only for the cost estimate in prepare_dataset.py's report).
SFT_PRICE_PER_M = {"<=16B": 0.50, "16.1B-80B": 3.00, "80B-300B": 6.00, ">300B": 10.00}

TOKENIZER_MODEL = os.environ.get("AGENTORCH_TOKENIZER", "Qwen/Qwen3.8-27B")


def make_token_counter():
    """Prefer the real Qwen tokenizer (exact filtering); fall back to cl100k."""
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)

        def count(text: str) -> int:
            return len(tok(text, add_special_tokens=False).input_ids)

        return count, f"{TOKENIZER_MODEL} tokenizer (exact)"
    except Exception:
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")

            def count(text: str) -> int:
                return len(enc.encode(text, disallowed_special=()))

            return count, "tiktoken cl100k_base (~±10% vs Qwen)"
        except ImportError:
            return (lambda text: int(len(text) / 3.6) + 1), "chars/3.6 heuristic"


def row_tokens(messages: list[dict], count) -> int:
    return sum(count(m["content"]) for m in messages)
