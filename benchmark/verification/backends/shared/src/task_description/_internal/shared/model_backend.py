from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..paths import PROJECT_ROOT
from .pipeline_common import PipelineError


DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MODEL_PROVIDER = "anthropic"
DEFAULT_EFFORT = "high"
DEFAULT_DOTENV_PATH = os.environ.get(
    "AGENTORCH_DOTENV_PATH",
    str(PROJECT_ROOT / ".env"),
)


@dataclass(frozen=True)
class ModelRequest:
    stage: str
    recipe_id: str
    system_prompt: str
    input_payload: dict[str, Any]
    output_contract: dict[str, Any]
    model_name: str
    prompt_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "recipe_id": self.recipe_id,
            "system_prompt": self.system_prompt,
            "input": self.input_payload,
            "output_contract": self.output_contract,
            "model": self.model_name,
            "prompt_version": self.prompt_version,
        }


def _parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        first_newline = candidate.find("\n")
        last_fence = candidate.rfind("```")
        if first_newline != -1 and last_fence > first_newline:
            candidate = candidate[first_newline + 1 : last_fence].strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"model returned invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PipelineError("model response must be a JSON object")
    return value


def _usage_dict(usage: Any) -> dict[str, int]:
    fields = (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    )
    return {
        name: int(getattr(usage, name, 0) or 0)
        for name in fields
    }


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _openai_usage_dict(usage: Any) -> dict[str, int]:
    dumped = _model_dump(usage)
    input_details = dumped.get("input_tokens_details") or {}
    output_details = dumped.get("output_tokens_details") or {}
    return {
        "input_tokens": int(dumped.get("input_tokens") or 0),
        "output_tokens": int(dumped.get("output_tokens") or 0),
        "total_tokens": int(dumped.get("total_tokens") or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens") or 0),
        "reasoning_output_tokens": int(
            output_details.get("reasoning_tokens") or 0
        ),
    }


def _schema_name(request: ModelRequest) -> str:
    value = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        f"{request.stage}_{request.recipe_id}",
    )
    return value[:64] or "workflow_output"


class OpenAIResponsesStructuredModel:
    """OpenAI Responses API backend with strict JSON Schema output.

    Construction performs an exact Models API lookup. An unavailable or
    unauthorized model is a hard failure; this class never changes the model
    ID or falls back to another provider.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL,
        effort: str = DEFAULT_EFFORT,
        dotenv_path: str = DEFAULT_DOTENV_PATH,
        max_tokens: int = 16000,
        timeout_seconds: int = 600,
    ) -> None:
        try:
            from dotenv import load_dotenv
            from openai import OpenAI
        except ImportError as exc:
            raise PipelineError(
                "OpenAI generation requires packages from "
                "task_description/requirements.txt"
            ) from exc

        load_dotenv(dotenv_path)
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise PipelineError(
                f"OPENAI_API_KEY was not loaded from {dotenv_path}"
            )

        self.model_name = model_name
        self.effort = effort
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        exact = self.client.models.retrieve(model_name)
        if str(getattr(exact, "id", "")) != model_name:
            raise PipelineError(
                f"Models API returned {getattr(exact, 'id', None)!r} for "
                f"required exact model {model_name!r}; no fallback will be used"
            )
        dumped = _model_dump(exact)
        self.model_capabilities_snapshot = {
            key: dumped[key]
            for key in ("id", "object", "created", "owned_by")
            if key in dumped
        }

    def _invoke(
        self,
        request: ModelRequest,
        *,
        repair_errors: list[str] | None = None,
        invalid_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "workflow_input": request.input_payload,
            "response_requirements": (
                "Return only the JSON object constrained by the supplied "
                "structured-output schema."
            ),
        }
        if repair_errors is not None:
            payload["repair_request"] = {
                "validation_errors": repair_errors,
                "invalid_output": invalid_output,
                "instruction": (
                    "Correct every listed error while preserving supported "
                    "workflow semantics. Do not add unsupported claims."
                ),
            }
        response = self.client.responses.create(
            model=self.model_name,
            instructions=request.system_prompt,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            reasoning={"effort": self.effort},
            max_output_tokens=self.max_tokens,
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(request),
                    "schema": request.output_contract,
                    "strict": True,
                }
            },
        )
        returned_model = str(getattr(response, "model", "") or "")
        if returned_model != self.model_name:
            raise PipelineError(
                f"{request.stage} returned model {returned_model!r}, expected "
                f"exactly {self.model_name!r}; output rejected"
            )
        status = str(getattr(response, "status", "") or "")
        if status and status != "completed":
            details = _model_dump(
                getattr(response, "incomplete_details", None)
            )
            raise PipelineError(
                f"{request.stage} response status is {status!r}: {details}"
            )
        output_text = str(getattr(response, "output_text", "") or "")
        if not output_text:
            raise PipelineError(
                f"{request.stage} returned no structured output text"
            )
        result = _parse_json_object(output_text)
        result["_model_provenance"] = {
            "backend": "openai_responses_structured_outputs",
            "model": returned_model,
            "model_capabilities_snapshot": self.model_capabilities_snapshot,
            "effort": self.effort,
            "prompt_version": request.prompt_version,
            "request_id": str(getattr(response, "id", "") or ""),
            "status": status,
            "usage": _openai_usage_dict(getattr(response, "usage", None)),
            "repair_call": repair_errors is not None,
            "store": False,
        }
        return result

    def generate(self, request: ModelRequest) -> dict[str, Any]:
        return self._invoke(request)

    def repair(
        self,
        request: ModelRequest,
        invalid_output: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        return self._invoke(
            request,
            repair_errors=errors,
            invalid_output=invalid_output,
        )


class CodexStructuredModel:
    """ChatGPT-authenticated Codex CLI structured-output backend.

    This is an explicit backend for hosts whose OpenAI API key is unavailable
    but whose Codex CLI is logged in. Each invocation pins the exact model and
    reasoning effort, supplies a JSON Schema, and rejects output unless the
    CLI metadata confirms both requested values.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL,
        effort: str = DEFAULT_EFFORT,
        max_tokens: int = 16000,
        timeout_seconds: int = 600,
    ) -> None:
        self.model_name = model_name
        self.effort = effort
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        try:
            version = subprocess.run(
                ["codex", "--version"],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PipelineError(f"Codex CLI is unavailable: {exc}") from exc
        if version.returncode != 0:
            raise PipelineError(
                "Codex CLI preflight failed: " + version.stderr.strip()
            )
        self.codex_version = version.stdout.strip()
        self.model_capabilities_snapshot = {
            "id": model_name,
            "provider": "openai",
            "interface": "codex_exec_output_schema",
            "codex_cli_version": self.codex_version,
            "exact_model_assertion": "verified_from_each_invocation_metadata",
        }

    @staticmethod
    def _metadata_value(stderr: str, key: str) -> str:
        match = re.search(
            rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$",
            stderr,
        )
        return match.group(1).strip() if match else ""

    @staticmethod
    def _token_usage(stderr: str) -> dict[str, int]:
        match = re.search(
            r"(?m)^tokens used\s*\n\s*([0-9,]+)\s*$",
            stderr,
        )
        return {
            "total_tokens": (
                int(match.group(1).replace(",", "")) if match else 0
            )
        }

    def _invoke(
        self,
        request: ModelRequest,
        *,
        repair_errors: list[str] | None = None,
        invalid_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "workflow_input": request.input_payload,
            "response_requirements": (
                "Return only the JSON object constrained by the supplied "
                "structured-output schema. Do not call tools."
            ),
        }
        if repair_errors is not None:
            payload["repair_request"] = {
                "validation_errors": repair_errors,
                "invalid_output": invalid_output,
                "instruction": (
                    "Correct every listed error while preserving supported "
                    "workflow semantics. Do not add unsupported claims."
                ),
            }
        prompt = (
            request.system_prompt
            + "\n\nThe following JSON is the complete generation input:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
        with tempfile.TemporaryDirectory(prefix="recipe_codex_model_") as tmp:
            tmp_path = Path(tmp)
            schema_path = tmp_path / "output_schema.json"
            output_path = tmp_path / "output.json"
            schema_path.write_text(
                json.dumps(request.output_contract, ensure_ascii=False),
                encoding="utf-8",
            )
            command = [
                "codex",
                "exec",
                "--ephemeral",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                self.model_name,
                "-c",
                f'model_reasoning_effort="{self.effort}"',
                "-c",
                "model_reasoning_summary=\"none\"",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-",
            ]
            child_env = dict(os.environ)
            child_env.pop("OPENAI_API_KEY", None)
            try:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    env=child_env,
                )
            except subprocess.TimeoutExpired as exc:
                raise PipelineError(
                    f"{request.stage} Codex call timed out after "
                    f"{self.timeout_seconds} seconds"
                ) from exc
            if completed.returncode != 0:
                raise PipelineError(
                    f"{request.stage} Codex call failed with exit code "
                    f"{completed.returncode}: {completed.stderr[-4000:].strip()}"
                )
            returned_model = self._metadata_value(
                completed.stderr, "model"
            )
            returned_effort = self._metadata_value(
                completed.stderr, "reasoning effort"
            )
            if returned_model != self.model_name:
                raise PipelineError(
                    f"{request.stage} Codex metadata reported model "
                    f"{returned_model!r}, expected {self.model_name!r}; "
                    "output rejected"
                )
            if returned_effort != self.effort:
                raise PipelineError(
                    f"{request.stage} Codex metadata reported reasoning effort "
                    f"{returned_effort!r}, expected {self.effort!r}; "
                    "output rejected"
                )
            if not output_path.is_file():
                raise PipelineError(
                    f"{request.stage} Codex call produced no final output file"
                )
            result = _parse_json_object(
                output_path.read_text(encoding="utf-8")
            )
            result["_model_provenance"] = {
                "backend": "codex_cli_structured_outputs",
                "model": returned_model,
                "model_capabilities_snapshot": (
                    self.model_capabilities_snapshot
                ),
                "effort": returned_effort,
                "prompt_version": request.prompt_version,
                "request_id": self._metadata_value(
                    completed.stderr, "session id"
                ),
                "provider": self._metadata_value(
                    completed.stderr, "provider"
                ),
                "usage": self._token_usage(completed.stderr),
                "repair_call": repair_errors is not None,
            }
        return result

    def generate(self, request: ModelRequest) -> dict[str, Any]:
        return self._invoke(request)

    def repair(
        self,
        request: ModelRequest,
        invalid_output: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        return self._invoke(
            request,
            repair_errors=errors,
            invalid_output=invalid_output,
        )


class AnthropicStructuredModel:
    """Strict Claude structured-output client used by semantic stages.

    Construction performs the required Models API preflight. The requested
    model must be returned under its exact ID; aliases and fallback models are
    intentionally rejected.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL,
        effort: str = DEFAULT_EFFORT,
        dotenv_path: str = DEFAULT_DOTENV_PATH,
        max_tokens: int = 16000,
        timeout_seconds: int = 600,
    ) -> None:
        try:
            from anthropic import Anthropic
            from dotenv import load_dotenv
        except ImportError as exc:
            raise PipelineError(
                "Anthropic generation requires packages from "
                "task_description/requirements.txt"
            ) from exc

        load_dotenv(dotenv_path)
        import os

        try:
            api_key = os.environ["ANTHROPIC_API_KEY"]
        except KeyError as exc:
            raise PipelineError(
                f"ANTHROPIC_API_KEY was not loaded from {dotenv_path}"
            ) from exc
        if not api_key:
            raise PipelineError("ANTHROPIC_API_KEY is empty")

        self.model_name = model_name
        self.effort = effort
        self.max_tokens = max_tokens
        self.client = Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
        )
        models = list(self.client.models.list(limit=100))
        exact = next(
            (
                item
                for item in models
                if str(getattr(item, "id", "")) == model_name
            ),
            None,
        )
        if exact is None:
            raise PipelineError(
                f"required Anthropic model {model_name!r} is unavailable; "
                "no fallback model will be used"
            )
        dumped = (
            exact.model_dump(mode="json")
            if hasattr(exact, "model_dump")
            else {"id": model_name}
        )
        self.model_capabilities_snapshot = {
            key: dumped[key]
            for key in (
                "id",
                "display_name",
                "created_at",
                "type",
                "capabilities",
            )
            if key in dumped
        }

    def _invoke(
        self,
        request: ModelRequest,
        *,
        repair_errors: list[str] | None = None,
        invalid_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "workflow_input": request.input_payload,
            "response_requirements": (
                "Return only the JSON object constrained by the supplied "
                "structured-output schema."
            ),
        }
        if repair_errors is not None:
            payload["repair_request"] = {
                "validation_errors": repair_errors,
                "invalid_output": invalid_output,
                "instruction": (
                    "Correct every listed error while preserving supported "
                    "workflow semantics. Do not add unsupported claims."
                ),
            }
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            cache_control={"type": "ephemeral"},
            system=request.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        payload, ensure_ascii=False, sort_keys=True
                    ),
                }
            ],
            output_config={
                "effort": self.effort,
                "format": {
                    "type": "json_schema",
                    "schema": request.output_contract,
                },
            },
        )
        text_blocks = [
            str(getattr(block, "text", ""))
            for block in response.content
            if getattr(block, "type", "") == "text"
        ]
        if not text_blocks:
            raise PipelineError(
                f"{request.stage} returned no structured text content"
            )
        result = _parse_json_object("".join(text_blocks))
        result["_model_provenance"] = {
            "backend": "anthropic_structured_outputs",
            "model": str(getattr(response, "model", self.model_name)),
            "model_capabilities_snapshot": self.model_capabilities_snapshot,
            "effort": self.effort,
            "prompt_version": request.prompt_version,
            "request_id": str(getattr(response, "id", "")),
            "stop_reason": str(getattr(response, "stop_reason", "")),
            "usage": _usage_dict(response.usage),
            "repair_call": repair_errors is not None,
            "prompt_cache": {
                "enabled": True,
                "mode": "automatic",
                "ttl": "5m",
            },
        }
        return result

    def generate(self, request: ModelRequest) -> dict[str, Any]:
        return self._invoke(request)

    def repair(
        self,
        request: ModelRequest,
        invalid_output: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        return self._invoke(
            request,
            repair_errors=errors,
            invalid_output=invalid_output,
        )


class CommandJsonModel:
    """Test/development wrapper retaining the provider-neutral interface."""

    def __init__(self, command: str, timeout_seconds: int = 300) -> None:
        argv = shlex.split(command)
        if not argv:
            raise PipelineError("model command cannot be empty")
        self.argv = argv
        self.timeout_seconds = timeout_seconds

    def generate(self, request: ModelRequest) -> dict[str, Any]:
        completed = subprocess.run(
            self.argv,
            input=json.dumps(request.as_dict(), ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise PipelineError(
                "model command failed with exit code "
                f"{completed.returncode}: {completed.stderr.strip()}"
            )
        response = _parse_json_object(completed.stdout)
        response.setdefault(
            "_model_provenance",
            {
                "model": request.model_name,
                "prompt_version": request.prompt_version,
                "backend": "command",
            },
        )
        return response

    def repair(
        self,
        request: ModelRequest,
        invalid_output: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        repair_request = ModelRequest(
            stage=f"{request.stage}_repair",
            recipe_id=request.recipe_id,
            system_prompt=(
                request.system_prompt
                + "\nRepair the supplied invalid output and resolve every "
                "validation error."
            ),
            input_payload={
                **request.input_payload,
                "invalid_output": invalid_output,
                "validation_errors": errors,
            },
            output_contract=request.output_contract,
            model_name=request.model_name,
            prompt_version=request.prompt_version,
        )
        return self.generate(repair_request)


def add_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model-command",
        help="optional JSON model wrapper used only for tests/development",
    )
    parser.add_argument(
        "--model-provider",
        default=DEFAULT_MODEL_PROVIDER,
        choices=["codex", "openai", "anthropic"],
        help=(
            "explicit model backend; codex uses the locally authenticated "
            "Codex CLI, openai uses the Responses API, and anthropic preserves "
            "the historical Claude path"
        ),
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL,
        help="exact model ID; unavailable IDs fail without fallback",
    )
    parser.add_argument(
        "--effort",
        default=DEFAULT_EFFORT,
        choices=["low", "medium", "high", "max"],
    )
    parser.add_argument(
        "--dotenv-path",
        default=DEFAULT_DOTENV_PATH,
    )
    parser.add_argument("--model-timeout", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=16000)


def model_from_args(args: argparse.Namespace) -> Any:
    if getattr(args, "model_command", None):
        return CommandJsonModel(
            args.model_command,
            timeout_seconds=args.model_timeout,
        )
    provider = getattr(args, "model_provider", DEFAULT_MODEL_PROVIDER)
    if provider == "codex":
        return CodexStructuredModel(
            model_name=args.model_name,
            effort=args.effort,
            max_tokens=args.max_tokens,
            timeout_seconds=args.model_timeout,
        )
    if provider == "openai":
        return OpenAIResponsesStructuredModel(
            model_name=args.model_name,
            effort=args.effort,
            dotenv_path=args.dotenv_path,
            max_tokens=args.max_tokens,
            timeout_seconds=args.model_timeout,
        )
    if provider == "anthropic":
        return AnthropicStructuredModel(
            model_name=args.model_name,
            effort=args.effort,
            dotenv_path=args.dotenv_path,
            max_tokens=args.max_tokens,
            timeout_seconds=args.model_timeout,
        )
    raise PipelineError(f"unsupported model provider {provider!r}")


def generate_with_one_repair(
    model: Any,
    request: ModelRequest,
    validator: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate once and permit exactly one validation-repair call."""
    attempts: list[dict[str, Any]] = []
    result = model.generate(request)
    errors = list(validator(result))
    attempts.append(
        {
            "attempt": 1,
            "kind": "generation",
            "valid": not errors,
            "errors": errors,
            "provenance": result.get("_model_provenance") or {},
        }
    )
    if not errors:
        return result, attempts
    if not hasattr(model, "repair"):
        raise PipelineError(
            f"{request.stage} structured output failed validation and the "
            "backend has no repair method: " + "; ".join(errors)
        )
    repaired = model.repair(request, result, errors)
    repair_errors = list(validator(repaired))
    attempts.append(
        {
            "attempt": 2,
            "kind": "repair",
            "valid": not repair_errors,
            "errors": repair_errors,
            "provenance": repaired.get("_model_provenance") or {},
        }
    )
    if repair_errors:
        rejection = PipelineError(
            f"{request.stage} repair failed validation: "
            + "; ".join(repair_errors)
        )
        rejection.structured_generation_failure = {
            "stage": request.stage,
            "recipe_id": request.recipe_id,
            "prompt_version": request.prompt_version,
            "model": request.model_name,
            "attempts": attempts,
            "first_output": result,
            "repair_output": repaired,
            "final_validation_errors": repair_errors,
        }
        raise rejection
    return repaired, attempts
