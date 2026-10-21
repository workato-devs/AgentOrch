"""Model adapters, including a Hugging Face Inference API adapter."""

from __future__ import annotations

import json
import os
import re
import ast
from pathlib import Path
from typing import Any, Protocol


# The 1B checkpoint currently has no live routed provider. This 3B checkpoint
# is the smallest Llama Instruct model with a live Hugging Face provider at
# the time this adapter was added.
DEFAULT_HF_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
ENV_FILE = Path(os.environ.get("AGENTORCH_ENV_FILE") or (Path(__file__).resolve().parents[3] / ".env"))
if not ENV_FILE.is_file():
    ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _local_env_value(name: str) -> str | None:
    """Read one local benchmark setting without exporting or logging secrets."""
    if not ENV_FILE.is_file():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'") or None
    return None


class Planner(Protocol):
    """Planning-only models receive only a model-visible view JSON."""

    def propose_plan(self, task: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]: ...


class InteractiveAgent(Protocol):
    """Interactive models receive public task data and tool observations."""

    def start(self, task: dict[str, Any], *, mode: str,
              tool_specs: list[dict[str, Any]] | None = None) -> None: ...

    def act(self, observation: dict[str, Any] | None) -> dict[str, Any]: ...


def make_run_record(*, recipe_id: str, variant_id: str, mode: str,
                    model_id: str, model_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "agentorch-public-run",
        "recipe_id": str(recipe_id),
        "variant_id": str(variant_id),
        "mode": mode,
        "model_id": model_id,
        "model_input": model_input,
        "plan": None,
        "trajectory": [],
        "final_answer": None,
        "status": "started",
    }


def _json_response(text: str) -> Any:
    """Extract one JSON object or array from a chat-model response."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    candidates = [cleaned]
    # Small models sometimes emit prose or several JSON editor operations in
    # one response. Scan balanced top-level values so the caller can consume
    # the first operation without a greedy regex merging multiple objects.
    start: int | None = None
    stack: list[str] = []
    in_string = False
    escaped = False
    for index, char in enumerate(cleaned):
        if start is None:
            if char in "{[":
                start = index
                stack = [char]
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
            if not stack or (char == "}" and stack[-1] != "{") or (char == "]" and stack[-1] != "["):
                start = None
                stack = []
                continue
            stack.pop()
            if not stack and start is not None:
                candidate = cleaned[start:index + 1]
                if candidate != cleaned:
                    candidates.append(candidate)
                start = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Small instruction models sometimes emit a Python dict/list
            # (`{'tool': ...}`) despite being asked for JSON. literal_eval is
            # non-executing and handles that formatting without accepting code.
            try:
                value = ast.literal_eval(candidate)
            except (SyntaxError, ValueError):
                continue
            if isinstance(value, (dict, list)):
                return value
    preview = cleaned.replace("\n", " ")[:500]
    raise ValueError(f"model response did not contain parseable JSON: {preview!r}")


def _has_complete_json(text: str) -> bool:
    """Return true once prose-prefixed output contains one balanced JSON value."""
    stack: list[str] = []
    in_string = False
    escaped = False
    started = False
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
            if not stack or (char == "}" and stack[-1] != "{") or (char == "]" and stack[-1] != "["):
                return False
            stack.pop()
            if not stack:
                return True
    return False


def interactive_action_schema(tool_specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the one-action protocol from the simulator's public tool schemas.

    Each branch binds one tool name to that tool's argument schema.  The only
    evaluator controls exposed to the model are ``finish`` and ``stop``.
    """
    branches: list[dict[str, Any]] = []
    for spec in tool_specs:
        name = spec.get("name")
        input_schema = spec.get("input_schema")
        if not isinstance(name, str) or not isinstance(input_schema, dict):
            raise ValueError("each public tool spec requires name and input_schema")
        branches.append({
            "type": "object",
            "properties": {
                "thought": {"type": "string", "maxLength": 256},
                "tool": {"const": name},
                "args": input_schema,
            },
            "required": ["tool", "args"],
            "additionalProperties": False,
        })
    branches.extend([
        {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "maxLength": 256},
                "tool": {"const": "finish"},
                "args": {"type": "object", "maxProperties": 0},
            },
            "required": ["tool", "args"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "maxLength": 256},
                "tool": {"const": "stop"},
                "args": {
                    "type": "object",
                    "properties": {
                        "stop_reason": {"type": "string"},
                        "stop_with_error": {"type": "boolean"},
                    },
                    "required": ["stop_reason", "stop_with_error"],
                    "additionalProperties": False,
                },
            },
            "required": ["tool", "args"],
            "additionalProperties": False,
        },
    ])
    return {"oneOf": branches}


def _lmfe_compatible_schema(value: Any) -> Any:
    """Make unconstrained ``{}`` nodes explicit for lm-format-enforcer 0.11.

    ``{}`` means any JSON value in JSON Schema.  The installed parser expects
    an explicit type, so this preserves the same semantics as a type union.
    """
    if isinstance(value, list):
        return [_lmfe_compatible_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    if not value:
        return {"type": ["string", "number", "boolean", "object", "array", "null"]}
    return {key: _lmfe_compatible_schema(item) for key, item in value.items()}


class HuggingFaceAdapter:
    """Text-JSON agent backed by ``huggingface_hub.InferenceClient``.

    Tokens come only from ``HF_TOKEN`` or ``HUGGINGFACEHUB_API_TOKEN`` and
    are never written into run records.
    """

    def __init__(self, *, model: str = DEFAULT_HF_MODEL, token: str | None = None,
                 provider: str = "auto", max_tokens: int = 1024,
                 temperature: float = 0.0) -> None:
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise RuntimeError(
                "install the client first: python -m pip install -U huggingface_hub"
            ) from exc
        token = (token or os.environ.get("HF_TOKEN")
                 or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
                 or _local_env_value("HF_TOKEN")
                 or _local_env_value("HUGGINGFACEHUB_API_TOKEN"))
        if not token:
            raise RuntimeError("set HF_TOKEN before using the Hugging Face adapter")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = InferenceClient(model=model, token=token, provider=provider)
        self.messages: list[dict[str, str]] = []

    def _complete(self, messages: list[dict[str, str]], *,
                  json_schema: dict[str, Any] | None = None) -> Any:
        try:
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        except Exception as exc:
            if "not supported by any provider you have enabled" in str(exc):
                raise RuntimeError(
                    f"{self.model!r} has no enabled Hugging Face Inference Provider "
                    "for this account. Enable a provider for the model in Hugging "
                    "Face Inference Providers, then set HF_PROVIDER to that provider "
                    "(for example, featherless-ai)."
                ) from exc
            raise
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise RuntimeError("Hugging Face API returned an empty non-text completion")
        return _json_response(content)

    def propose_plan(self, task: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
        if isinstance(task.get("system_prompt"), str) and isinstance(task.get("user_prompt"), str):
            return self._complete([
                {"role": "system", "content": task["system_prompt"]},
                {"role": "user", "content": task["user_prompt"]},
            ])
        return self._complete([
            {"role": "system", "content": (
                "You are a workflow planner. Return strict RFC 8259 JSON only: either a list of "
                "ordered {tool, args} steps or an object with a steps list. Do not "
                "use information not present in the task."
            )},
            {"role": "user", "content": json.dumps(task, sort_keys=True)},
        ])

    def propose_incremental_plan(self, task: dict[str, Any], *, max_turns: int = 32) -> dict[str, Any]:
        """Build one Local-view plan through the public append-only editor."""
        messages = [
            {"role": "system", "content": task["system_prompt"]},
            {"role": "user", "content": task["user_prompt"]},
        ]
        plan: list[dict[str, Any]] = []
        draft_nodes: dict[str, dict[str, Any]] = {}
        next_id = 1
        regions = {
            "if": {"then", "else"},
            "foreach": {"body"},
            "repeat": {"body"},
            "try": {"body", "catch"},
        }
        for _ in range(max_turns):
            operation = self._complete(messages)
            if not isinstance(operation, dict):
                feedback = {"accepted": False, "error": "editor operation must be an object"}
            elif operation.get("type") == "finish_plan":
                return {"plan": plan}
            elif operation.get("type") != "append_node":
                feedback = {"accepted": False, "error": "type must be append_node or finish_plan"}
            else:
                parent = operation.get("parent")
                node = operation.get("node")
                target: list[dict[str, Any]] | None = None
                if not isinstance(node, dict):
                    feedback = {"accepted": False, "error": "node must be an object"}
                else:
                    node = json.loads(json.dumps(node))
                    allowed_regions = regions.get(str(node.get("kind")), set())
                    for region in allowed_regions:
                        node.pop(region, None)
                    if parent == "root":
                        target = plan
                    elif isinstance(parent, str) and "." in parent:
                        draft_id, region = parent.split(".", 1)
                        owner = draft_nodes.get(draft_id)
                        if owner is not None and region in regions.get(str(owner.get("kind")), set()):
                            target = owner.setdefault(region, [])
                    if target is None:
                        feedback = {"accepted": False, "error": f"invalid parent: {parent!r}"}
                    else:
                        target.append(node)
                        draft_id = f"d{next_id}"
                        next_id += 1
                        draft_nodes[draft_id] = node
                        feedback = {
                            "accepted": True,
                            "draft_id": draft_id,
                            "current_draft": {"plan": plan},
                        }
            messages.append({"role": "assistant", "content": json.dumps(operation)})
            messages.append({"role": "user", "content": json.dumps(feedback)})
        return {"plan": plan}

    def start(self, task: dict[str, Any], *, mode: str,
              tool_specs: list[dict[str, Any]] | None = None) -> None:
        self.action_schema = interactive_action_schema(tool_specs or [])
        if isinstance(task.get("system_prompt"), str) and isinstance(task.get("user_prompt"), str):
            self.messages = [
                {"role": "system", "content": task["system_prompt"]},
                {"role": "user", "content": task["user_prompt"]},
            ]
            return
        self.messages = [
            {"role": "system", "content": (
                f"You are an interactive workflow agent running in {mode} mode. "
                "Return only one JSON object each turn: {\"tool\": \"...\", "
                "\"args\": {...}}, optionally with \"plan\"; or "
                "{\"final_answer\": ...} when finished."
            )},
            {"role": "user", "content": json.dumps(task, sort_keys=True)},
        ]

    def act(self, observation: dict[str, Any] | None) -> dict[str, Any]:
        if observation is not None:
            self.messages.append({"role": "user", "content": json.dumps({"observation": observation})})
        decision = self._complete(self.messages, json_schema=self.action_schema)
        if not isinstance(decision, dict):
            raise ValueError("interactive model response must be a JSON object")
        self.messages.append({"role": "assistant", "content": json.dumps(decision)})
        return decision


class LocalHuggingFaceAdapter(HuggingFaceAdapter):
    """Run a gated Hugging Face checkpoint directly on the allocated GPU."""

    def __init__(self, *, model: str = DEFAULT_HF_MODEL, token: str | None = None,
                 max_tokens: int = 1024, temperature: float = 0.0) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "local inference requires torch, transformers, and accelerate"
            ) from exc
        token = (token or os.environ.get("HF_TOKEN")
                 or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
                 or _local_env_value("HF_TOKEN")
                 or _local_env_value("HUGGINGFACEHUB_API_TOKEN"))
        if not token:
            raise RuntimeError("set HF_TOKEN before loading a gated local model")
        self.model_name = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.tokenizer = AutoTokenizer.from_pretrained(model, token=token)
        self.model = AutoModelForCausalLM.from_pretrained(
            model, token=token, torch_dtype="auto", device_map="auto",
        )
        self.model.eval()
        self.torch = torch
        self.messages: list[dict[str, str]] = []
        self._format_enforcer_tokenizer_data: Any = None

    def _complete(self, messages: list[dict[str, str]], *,
                  json_schema: dict[str, Any] | None = None) -> Any:
        from transformers import StoppingCriteria, StoppingCriteriaList

        encoded = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_tensors="pt", return_dict=True,
        )
        device = next(self.model.parameters()).device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        prompt_tokens = encoded["input_ids"].shape[1]
        tokenizer = self.tokenizer

        class CompleteJSON(StoppingCriteria):
            def __call__(self, input_ids: Any, scores: Any, **kwargs: Any) -> bool:
                completion = tokenizer.decode(
                    input_ids[0, prompt_tokens:],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
                return _has_complete_json(completion)

        prefix_allowed_tokens_fn = None
        if json_schema is not None:
            # lm-format-enforcer 0.11 imports this base class from its old
            # Transformers location. Transformers 5 moved it to
            # tokenization_utils_base; supply the compatibility alias without
            # changing either installed package.
            from transformers import PreTrainedTokenizerBase
            import transformers.tokenization_utils as tokenization_utils
            if not hasattr(tokenization_utils, "PreTrainedTokenizerBase"):
                tokenization_utils.PreTrainedTokenizerBase = PreTrainedTokenizerBase
            from lmformatenforcer import JsonSchemaParser
            from lmformatenforcer.integrations.transformers import (
                build_token_enforcer_tokenizer_data,
                build_transformers_prefix_allowed_tokens_fn,
            )
            if self._format_enforcer_tokenizer_data is None:
                self._format_enforcer_tokenizer_data = build_token_enforcer_tokenizer_data(
                    self.tokenizer
                )
            prefix_allowed_tokens_fn = build_transformers_prefix_allowed_tokens_fn(
                self._format_enforcer_tokenizer_data,
                JsonSchemaParser(_lmfe_compatible_schema(json_schema)),
            )

        with self.torch.inference_mode():
            generated = self.model.generate(
                **encoded,
                max_new_tokens=self.max_tokens,
                do_sample=self.temperature > 0,
                temperature=self.temperature if self.temperature > 0 else None,
                pad_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=StoppingCriteriaList([CompleteJSON()]),
                prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
            )
        completion = generated[0, encoded["input_ids"].shape[1]:]
        return _json_response(self.tokenizer.decode(completion, skip_special_tokens=True))


def build_hf_adapter() -> HuggingFaceAdapter:
    """Factory for ``--adapter evaluation.model_corpus:build_hf_adapter``."""
    model = os.environ.get("HF_MODEL") or _local_env_value("HF_MODEL") or DEFAULT_HF_MODEL
    max_tokens = int(os.environ.get("HF_MAX_TOKENS") or _local_env_value("HF_MAX_TOKENS") or "1024")
    temperature = float(os.environ.get("HF_TEMPERATURE") or _local_env_value("HF_TEMPERATURE") or "0")
    backend = (os.environ.get("HF_BACKEND") or _local_env_value("HF_BACKEND") or "inference").lower()
    if backend == "local":
        return LocalHuggingFaceAdapter(model=model, max_tokens=max_tokens, temperature=temperature)
    if backend != "inference":
        raise ValueError("HF_BACKEND must be 'inference' or 'local'")
    return HuggingFaceAdapter(
        model=model,
        provider=os.environ.get("HF_PROVIDER") or _local_env_value("HF_PROVIDER") or "auto",
        max_tokens=max_tokens,
        temperature=temperature,
    )
