"""vLLM stop processor matching the Transformers complete-JSON criterion."""

from __future__ import annotations

from collections.abc import Callable
import os
import threading
import re

import torch
from transformers import AutoTokenizer
from vllm import SamplingParams
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor


class CompleteJSONLogitsProcessor(AdapterLogitsProcessor):
    """Force EOS immediately after one balanced top-level JSON value."""

    def __init__(self, vllm_config, device: torch.device, is_pin_memory: bool):
        super().__init__(vllm_config, device, is_pin_memory)
        model_config = vllm_config.model_config
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_config.tokenizer,
            trust_remote_code=model_config.trust_remote_code,
            local_files_only=True,
        )
        eos_token_id = self.tokenizer.eos_token_id
        if eos_token_id is None:
            raise ValueError("complete-JSON stopping requires an EOS token")
        self.eos_token_id = int(eos_token_id)
        # One tokenizer instance serves every request closure; fast
        # tokenizers are not thread-safe under the engine's async
        # scheduling (concurrent decode raises "Already borrowed").
        self._decode_lock = threading.Lock()

    def is_argmax_invariant(self) -> bool:
        return False

    def new_req_logits_processor(
        self, params: SamplingParams
    ) -> Callable[[list[int], torch.Tensor], torch.Tensor]:
        tokenizer = self.tokenizer
        decode_lock = self._decode_lock
        eos_token_id = self.eos_token_id
        seen = 0
        stack: list[str] = []
        in_string = False
        escaped = False
        started = False
        complete = False
        react_hard_limit = int(os.environ.get("HF_REACT_MAX_NEW_TOKENS", "0"))
        react_soft_limit = int(
            os.environ.get("HF_REACT_SOFT_MAX_NEW_TOKENS", "0")
        )
        apply_soft_limit = bool(
            react_soft_limit
            and react_hard_limit
            and params.max_tokens == react_hard_limit
        )
        # Templates that open the think block on the prompt side stream
        # reasoning first; nothing before the closing tag may stop
        # generation, and JSON scanning starts after it.
        thinking_prefix = bool(os.environ.get("HF_THINKING_PREFIX"))
        think_closed = not thinking_prefix
        # Rolling tails for the incremental </think> and long-action
        # searches: joining and re-scanning the full transcript every step
        # is O(n^2) per stream and stalls large thinking batches (650
        # concurrent 30K-token streams); only the previous chunk's last
        # pattern-length-minus-one chars can complete a match split across
        # chunks.
        think_tail = ""
        long_action_seen = False
        long_action_tail = ""
        long_action = re.compile(
            r'"tool"\s*:\s*"(?:snowflake\.(?:run_custom_sql|search_rows_sql|upsert_rows_batch)'
            r'|google_sheets\.add_spreadsheet_row_v4)"'
        )

        def process(output_ids: list[int], logits: torch.Tensor) -> torch.Tensor:
            nonlocal seen, in_string, escaped, started, complete, think_closed
            nonlocal think_tail, long_action_seen, long_action_tail
            if not complete and len(output_ids) > seen:
                with decode_lock:
                    text = tokenizer.decode(
                        output_ids[seen:],
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=False,
                    )
                seen = len(output_ids)
                if not long_action_seen:
                    la_probe = long_action_tail + text
                    if long_action.search(la_probe):
                        long_action_seen = True
                    else:
                        long_action_tail = la_probe[-120:]
                if not think_closed:
                    probe = think_tail + text
                    close = probe.find("</think>")
                    if close < 0:
                        think_tail = probe[-(len("</think>") - 1):]
                        return logits
                    think_closed = True
                    text = probe[close + len("</think>"):]
                for char in text:
                    if not started:
                        if char in "{[":
                            started = True
                            stack.append(char)
                        continue
                    if in_string:
                        if escaped:
                            escaped = False
                        elif char == "\\":
                            escaped = True
                        elif char == '"':
                            in_string = False
                        continue
                    if char == '"':
                        in_string = True
                    elif char in "{[":
                        stack.append(char)
                    elif char in "}]":
                        if not stack or (
                            char == "}" and stack[-1] != "{"
                        ) or (char == "]" and stack[-1] != "["):
                            break
                        stack.pop()
                        if not stack:
                            complete = True
                            break
            if (
                not complete
                and apply_soft_limit
                and len(output_ids) >= react_soft_limit
                and think_closed
                and not long_action_seen
            ):
                complete = True
            if complete:
                logits.fill_(-float("inf"))
                logits[eos_token_id] = 0.0
            return logits

        return process
