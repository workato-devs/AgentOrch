"""LLM clients for the eval harness. Stdlib-only (urllib), matching the repo's
live-adapter convention. AnthropicClient is the real client; ScriptedLLM
replays a fixed reply list for offline tests."""

from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from benchmark.config import ENV_FILE

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class LLMError(Exception):
    pass


def _api_complete_many(client, requests):
    """Issue independent API requests concurrently while preserving order."""

    if not requests:
        return []
    workers = max(1, int(_setting("API_CONCURRENCY") or "1"))
    if workers == 1:
        return [client.complete(system, messages) for system, messages in requests]
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="llm-api") as pool:
        futures = [
            pool.submit(client.complete, system, messages)
            for system, messages in requests
        ]
        return [future.result() for future in futures]


def _api_retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float:
    """Honor provider retry headers, falling back to bounded backoff."""

    headers = exc.headers
    for name in ("retry-after-ms", "x-ms-retry-after-ms"):
        value = headers.get(name)
        if value:
            try:
                return max(0.1, min(float(value) / 1000.0, 120.0))
            except ValueError:
                pass
    value = headers.get("retry-after")
    if value:
        try:
            return max(0.1, min(float(value), 120.0))
        except ValueError:
            pass
    return min(2 ** attempt, 60)


def _strip_thinking(text: str) -> str:
    """Remove inline <think>...</think> reasoning from local-model output.

    API thinking is server-side and never reaches the harness; local
    thinking is inline text. Scored content is everything outside the
    think spans; an unterminated span means the model never surfaced an
    answer and yields empty text (scored as a failed generation)."""
    # Some templates open the think block on the prompt side, so the
    # completion carries only the closing tag: everything before the first
    # "</think>" is reasoning.
    if "<think>" not in text:
        if "</think>" in text:
            return text.split("</think>", 1)[1].strip()
        return text
    out = []
    pos = 0
    while True:
        start = text.find("<think>", pos)
        if start < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        end = text.find("</think>", start)
        if end < 0:
            break
        pos = end + len("</think>")
    return "".join(out).strip()


def _take_last_json(text: str) -> str:
    """Return only the last balanced top-level JSON value in ``text``.

    Thinking lanes whose template omits a closing tag interleave reasoning
    (which may quote JSON examples) with the final answer; the answer is
    the last complete JSON value. Declared per lane via HF_TAKE_LAST_JSON;
    non-thinking lanes never set it.
    """
    # Reasoning text freely mixes prose with pseudo-JSON (unquoted keys,
    # ellipses, unclosed braces), which desyncs any single-pass bracket
    # state machine. Instead, attempt a strict parse from every opener,
    # right to left. The answer is the rightmost value that consumes the
    # rest of the text; failing that, the parseable value ending furthest
    # right (outermost on ties).
    decoder = json.JSONDecoder()
    fallback: str | None = None
    fallback_end = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] not in "{[":
            continue
        try:
            _, end = decoder.raw_decode(text, i)
        except ValueError:
            continue
        if not text[end:].strip():
            # The value may be the interior of a wrapper whose closer the
            # model dropped (e.g. ``{"plan": [ ... ]`` with no final ``}``).
            # Keep any unclosed enclosing openers so the downstream
            # missing-closer repair can restore the wrapper.
            return text[_extend_through_unclosed_openers(text, i):]
        if end >= fallback_end:
            fallback = text[i:end]
            fallback_end = end
    return fallback if fallback is not None else text


def _extend_through_unclosed_openers(text: str, start: int) -> int:
    """Walk left from ``start`` through an unambiguous chain of unclosed
    JSON openers: a direct ``[`` , or ``{`` ``"key"`` ``:`` immediately
    preceding. Prose never matches (the key must be quoted and directly
    follow ``{``), so reasoning text cannot be pulled in."""
    while True:
        k = start - 1
        while k >= 0 and text[k].isspace():
            k -= 1
        if k >= 0 and text[k] == "[":
            start = k
            continue
        if k >= 0 and text[k] == ":":
            k -= 1
            while k >= 0 and text[k].isspace():
                k -= 1
            if k >= 0 and text[k] == '"':
                k -= 1
                while k >= 0 and text[k] != '"':
                    k -= 1
                if k > 0 and text[k] == '"':
                    k -= 1
                    while k >= 0 and text[k].isspace():
                        k -= 1
                    if k >= 0 and text[k] == "{":
                        start = k
                        continue
        return start


def _complete_json_prefix(text: str) -> bool:
    """Whether generated text contains one balanced top-level JSON value.

    Thinking spans are excluded: a draft JSON inside <think>...</think>
    must not stop generation before the surfaced answer.
    """
    if "<think>" in text or "</think>" in text:
        text = _strip_thinking(text)

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
            if not stack or (char == "}" and stack[-1] != "{") or (
                char == "]" and stack[-1] != "["
            ):
                return False
            stack.pop()
            if not stack:
                return True
    return False


def _env_file_value(key: str) -> str | None:
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text().splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        name, value = text.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("\"'")
    return None


def _api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY") or _env_file_value("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("missing ANTHROPIC_API_KEY (env or benchmark/.env)")
    return key


class ScriptedLLM:
    def __init__(self, replies: list[str], model: str = "scripted") -> None:
        self.model = model
        self._replies = list(replies)

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        if not self._replies:
            raise LLMError("script exhausted")
        return self._replies.pop(0)

    def rebind_runtime_values(self, replacements: dict[str, str]) -> None:
        """Rebind provisioned IDs in offline gold-control replies.

        Live reference executions and isolated simulator episodes provision
        fresh connector IDs. The evaluator derives this mapping from private
        seed provenance; production model clients intentionally expose no such
        hook.
        """

        ordered = sorted(
            (
                (str(before), str(after))
                for before, after in replacements.items()
                if str(before) and str(before) != str(after)
            ),
            key=lambda item: len(item[0]),
            reverse=True,
        )

        def replace(value):
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace(item) for item in value]
            if isinstance(value, str):
                for before, after in ordered:
                    value = value.replace(before, after)
            return value

        rebound: list[str] = []
        for reply in self._replies:
            try:
                rebound.append(json.dumps(replace(json.loads(reply))))
            except (json.JSONDecodeError, TypeError):
                value = reply
                for before, after in ordered:
                    value = value.replace(before, after)
                rebound.append(value)
        self._replies = rebound


class AnthropicClient:
    # temperature defaults to 0.0: benchmark runs must be as deterministic as
    # the API allows, and reported numbers must state their sampling setup.
    def __init__(self, model: str, api_key: str | None = None,
                 timeout: int = 180, max_tokens: int = 4096,
                 temperature: float = 0.0) -> None:
        self.model = model
        configured_temperature = _setting("ANTHROPIC_TEMPERATURE")
        if configured_temperature is None:
            self.temperature = temperature
        elif configured_temperature.strip().lower() in {"none", "off", "disabled"}:
            self.temperature = None
        else:
            try:
                self.temperature = float(configured_temperature)
            except ValueError as exc:
                raise ValueError(
                    "ANTHROPIC_TEMPERATURE must be a number or one of "
                    "none/off/disabled"
                ) from exc

        configured_thinking = _setting("ANTHROPIC_THINKING")
        self.thinking = (
            configured_thinking.strip().lower()
            if configured_thinking is not None
            else None
        )
        if self.thinking not in {None, "adaptive", "disabled"}:
            raise ValueError(
                "ANTHROPIC_THINKING must be adaptive or disabled when set"
            )

        configured_effort = _setting("ANTHROPIC_EFFORT")
        self.effort = (
            configured_effort.strip().lower()
            if configured_effort is not None
            else None
        )
        if self.effort not in {None, "low", "medium", "high", "max"}:
            raise ValueError(
                "ANTHROPIC_EFFORT must be low, medium, high, or max when set"
            )

        configured_max_tokens = _setting("ANTHROPIC_MAX_TOKENS")
        try:
            self.max_tokens = (
                int(configured_max_tokens)
                if configured_max_tokens is not None
                else int(max_tokens)
            )
        except ValueError as exc:
            raise ValueError("ANTHROPIC_MAX_TOKENS must be an integer") from exc
        if self.max_tokens < 1:
            raise ValueError("ANTHROPIC_MAX_TOKENS must be positive")
        self._key = api_key or _api_key()
        self._timeout = timeout
        self._max_tokens = self.max_tokens
        self._ssl = ssl.create_default_context()
        self.concurrent_batching = (
            (_setting("API_CONCURRENT_BATCHING") or "0").lower()
            in {"1", "true", "yes", "on"}
        )
        self.batch_initial_plans = self.concurrent_batching
        self.initial_plan_batch_size = max(
            1, int(_setting("API_CONCURRENCY") or "1")
        )
        self._request_semaphore = threading.BoundedSemaphore(
            max(1, int(_setting("API_CONCURRENCY") or "1"))
        )
        self._max_attempts = max(1, int(_setting("API_MAX_ATTEMPTS") or "5"))
        # Opt-in prompt caching (ANTHROPIC_PROMPT_CACHE=1). Output-neutral:
        # caching changes billing, never the completion. The one-shot planner
        # prompt is ~60k tokens per variant and, within a recipe, identical up
        # to the GLOBAL+INPUT runtime-input section, so the stable prefix is
        # marked as a cache breakpoint and the volatile tail follows it.
        self.prompt_cache = (
            (_setting("ANTHROPIC_PROMPT_CACHE") or "0").lower()
            in {"1", "true", "yes", "on"}
        )
        self.api_usage = {
            "requests": 0, "input_tokens": 0, "output_tokens": 0,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
        }
        self._usage_lock = threading.Lock()
        self._tls = threading.local()

    @property
    def last_call_completion_tokens(self) -> int | None:
        return getattr(self._tls, "completion_tokens", None)

    @property
    def last_call_prompt_tokens(self) -> int | None:
        """Input tokens billed for this thread's last call (incl. cache reads/writes)."""
        return getattr(self._tls, "prompt_tokens", None)

    # Volatile tail of a GLOBAL+INPUT planner prompt (task/workflow_plan.py);
    # everything before it is shared by every variant of the recipe.
    _CACHE_SPLIT_MARKER = "\n\n## Concrete runtime input\n"

    def _cached_messages(self, messages: list[dict[str, str]]) -> list[dict]:
        """Render messages with one ephemeral cache breakpoint on the stable prefix."""
        rendered: list[dict] = []
        for index, message in enumerate(messages):
            content = message.get("content")
            if index != 0 or not isinstance(content, str):
                rendered.append(dict(message))
                continue
            head, marker, tail = content.partition(self._CACHE_SPLIT_MARKER)
            blocks = [{"type": "text", "text": head, "cache_control": {"type": "ephemeral"}}]
            if marker:
                blocks.append({"type": "text", "text": marker + tail})
            rendered.append({"role": message["role"], "content": blocks})
        return rendered

    def _record_usage(self, payload: dict) -> None:
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            return
        self._tls.completion_tokens = int(usage.get("output_tokens") or 0)
        self._tls.prompt_tokens = sum(
            int(usage.get(key) or 0)
            for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
        with self._usage_lock:
            self.api_usage["requests"] += 1
            for key in ("input_tokens", "output_tokens",
                        "cache_creation_input_tokens", "cache_read_input_tokens"):
                self.api_usage[key] += int(usage.get(key) or 0)

    def _body(self, system: str, messages: list[dict[str, str]]) -> dict:
        body = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": self._cached_messages(messages) if self.prompt_cache else messages,
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.thinking is not None:
            body["thinking"] = {"type": self.thinking}
        if self.effort is not None:
            body["output_config"] = {"effort": self.effort}
        return body

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        self._tls.completion_tokens = None
        self._tls.prompt_tokens = None
        with self._request_semaphore:
            return self._complete_locked(system, messages)

    def _complete_locked(self, system: str, messages: list[dict[str, str]]) -> str:
        body = self._body(system, messages)
        headers = {
            "content-type": "application/json",
            "x-api-key": self._key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
        data = json.dumps(body).encode("utf-8")
        last = ""
        for attempt in range(self._max_attempts):
            request = urllib.request.Request(ANTHROPIC_API, data=data, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(request, context=self._ssl, timeout=self._timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                self._record_usage(payload)
                parts = [b.get("text") or "" for b in payload.get("content") or []
                         if isinstance(b, dict) and b.get("type") == "text"]
                text = "\n".join(p for p in parts if p).strip()
                if not text:
                    raise LLMError("model returned no text")
                return text
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")
                last = f"HTTP {exc.code}: {detail[:200]}"
                if (exc.code == 400
                        and "temperature" in detail and "deprecated" in detail):
                    # Newest Anthropic models reject the temperature param.
                    # Every concurrent request must be able to take this
                    # fallback even if a peer already updated shared state.
                    # Rebuild this request's local payload without temperature.
                    self.temperature = None
                    data = json.dumps(self._body(system, messages)).encode("utf-8")
                    continue
                if (exc.code in (429, 500, 502, 503, 504, 529)
                        and attempt < self._max_attempts - 1):
                    time.sleep(_api_retry_delay(exc, attempt))
                    continue
                raise LLMError(last) from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = f"request failed: {exc}"
                if attempt < self._max_attempts - 1:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                raise LLMError(last) from exc

    def complete_many(
        self, requests: list[tuple[str, list[dict[str, str]]]]
    ) -> list[str]:
        return _api_complete_many(self, requests)


# No default endpoint: set AZURE_OPENAI_ENDPOINT (environment or .env) to the
# Azure OpenAI resource that hosts the deployment.
AZURE_API_VERSION_DEFAULT = "2024-12-01-preview"


def _trust_remote_code() -> bool:
    """Whether the current model requires executing repository code.

    Set per model in the launcher (``HF_TRUST_REMOTE_CODE=1``) for the few
    checkpoints whose tokenizer/config ships as repository code (e.g. GLM-4
    chat models with custom architectures). Off by default."""
    return (_setting("HF_TRUST_REMOTE_CODE") or "0").lower() in {"1", "true", "yes"}


def _render_chat_prompt(
    tokenizer, system: str, messages: list[dict[str, str]]
) -> str | list[int]:
    """Apply the model's chat template with a deterministic system fallback.

    Some instruct templates (e.g. Gemma) reject a ``system`` role outright.
    Those models' documented convention is to fold the system text into the
    first user turn, which is what the fallback does — the information the
    model receives is identical either way.

    mistral-common tokenizer backends (e.g. Mistral-Nemo) declare the
    string rendering (``tokenize=False``) unsafe: re-encoding the returned
    string mangles special tokens and the model generates nothing. For
    those backends the template is applied with ``tokenize=True`` and the
    caller feeds the token ids to the engine directly."""
    tokenizer_class = type(tokenizer).__name__
    tokenize = (
        "MistralCommon" in tokenizer_class          # transformers backend
        or tokenizer_class == "MistralTokenizer"    # vLLM's mistral-common wrapper
        # Lanes whose vLLM front-end tokenization is unsafe under
        # concurrency (e.g. deepseek_v4 tokenizer_mode raising "Already
        # borrowed") declare ids-prompts explicitly.
        or bool(_setting("HF_PROMPT_IDS"))
    )
    # Thinking-mode lanes pass template switches (e.g. enable_thinking,
    # reasoning_effort) through one declared env knob; absent → {} keeps
    # every existing lane byte-identical.
    extra = json.loads(_setting("HF_CHAT_TEMPLATE_KWARGS") or "{}")
    # Optional model-specific system-prompt text is applied before rendering.
    suffix = _setting("HF_SYSTEM_PROMPT_SUFFIX")
    if suffix:
        system = f"{system}\n{suffix}"

    def _normalize(rendered: object) -> str | list[int]:
        # tokenize=True may return a bare id list or a BatchEncoding-style
        # mapping whose input_ids may carry a batch dimension.
        if hasattr(rendered, "get") and not isinstance(rendered, str):
            rendered = rendered.get("input_ids")
        if (
            isinstance(rendered, list)
            and rendered
            and isinstance(rendered[0], list)
        ):
            rendered = rendered[0]
        return rendered  # type: ignore[return-value]

    conversation = [{"role": "system", "content": system}, *messages]
    try:
        return _normalize(tokenizer.apply_chat_template(
            conversation, tokenize=tokenize, add_generation_prompt=True, **extra
        ))
    except Exception:
        merged = [dict(message) for message in messages]
        if merged and merged[0].get("role") == "user":
            merged[0]["content"] = f"{system}\n\n{merged[0]['content']}"
        else:
            merged.insert(0, {"role": "user", "content": system})
        return _normalize(tokenizer.apply_chat_template(
            merged, tokenize=tokenize, add_generation_prompt=True, **extra
        ))


def _setting(key: str) -> str | None:
    return os.environ.get(key) or _env_file_value(key)


class AzureOpenAIClient:
    """Azure OpenAI /chat/completions: the URL embeds the deployment + an
    api-version query param, auth is the `api-key` header. temperature
    defaults to 0.0 (see AnthropicClient)."""

    def __init__(self, model: str, api_key: str | None = None,
                 timeout: int = 180, max_tokens: int = 4096,
                 temperature: float = 0.0, deployment: str | None = None,
                 endpoint: str | None = None, api_version: str | None = None) -> None:
        self.model = model
        self.temperature = temperature
        self._deployment = deployment or _setting("AZURE_OPENAI_DEPLOYMENT") or model
        endpoint = endpoint or _setting("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise LLMError(
                f"missing AZURE_OPENAI_ENDPOINT for Azure model {model!r} "
                "(set OPENAI_API_MODE=direct to use api.openai.com instead)"
            )
        self._endpoint = endpoint.rstrip("/")
        self._api_version = (api_version or _setting("AZURE_OPENAI_API_VERSION")
                             or AZURE_API_VERSION_DEFAULT)
        key = api_key or _setting("OPENAI_API_KEY") or _setting("AZURE_OPENAI_API_KEY")
        if not key:
            raise LLMError(f"missing OPENAI_API_KEY for Azure model {model!r}")
        self._key = key
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._ssl = ssl.create_default_context()
        self.concurrent_batching = (
            (_setting("API_CONCURRENT_BATCHING") or "0").lower()
            in {"1", "true", "yes", "on"}
        )
        self._request_semaphore = threading.BoundedSemaphore(
            max(1, int(_setting("API_CONCURRENCY") or "1"))
        )
        self._max_attempts = max(1, int(_setting("API_MAX_ATTEMPTS") or "5"))

    def _url(self) -> str:
        return (f"{self._endpoint}/openai/deployments/{self._deployment}"
                f"/chat/completions?api-version={self._api_version}")

    def _body(self, system: str, messages: list[dict[str, str]]) -> dict:
        return {
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": self._max_tokens,
            "temperature": self.temperature,
        }

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        with self._request_semaphore:
            return self._complete_locked(system, messages)

    def _complete_locked(self, system: str, messages: list[dict[str, str]]) -> str:
        data = json.dumps(self._body(system, messages)).encode("utf-8")
        headers = {"content-type": "application/json", "api-key": self._key}
        last = ""
        for attempt in range(self._max_attempts):
            request = urllib.request.Request(self._url(), data=data, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(request, context=self._ssl, timeout=self._timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                text = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                text = text.strip()
                if not text:
                    raise LLMError("model returned no text")
                return text
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}"
                if (exc.code in (429, 500, 502, 503, 504)
                        and attempt < self._max_attempts - 1):
                    time.sleep(_api_retry_delay(exc, attempt))
                    continue
                raise LLMError(last) from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = f"request failed: {exc}"
                if attempt < self._max_attempts - 1:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                raise LLMError(last) from exc
        raise LLMError(last or "exhausted retries")

    def complete_many(
        self, requests: list[tuple[str, list[dict[str, str]]]]
    ) -> list[str]:
        return _api_complete_many(self, requests)


class OpenAIDirectClient:
    """Direct OpenAI /v1/chat/completions (api.openai.com, Bearer auth).

    Uses ``max_completion_tokens`` for the output budget. GPT-3/4 chat
    models use greedy sampling without reasoning parameters. Reasoning models
    omit temperature; OPENAI_REASONING_EFFORT overrides the model default,
    with ``none`` retained for the published GPT-5.x lanes."""

    def __init__(self, model: str, api_key: str | None = None,
                 timeout: int = 300, max_tokens: int = 4096) -> None:
        self.model = model
        # GPT-3/4 chat models reject reasoning_effort. For other families,
        # omit it unless configured, retaining the published GPT-5.x protocol.
        non_reasoning = model.lower().startswith(("gpt-3", "gpt-4", "chatgpt-4"))
        self.temperature = 0.0 if non_reasoning else None
        configured_effort = _setting("OPENAI_REASONING_EFFORT")
        if configured_effort:
            configured_effort = configured_effort.strip().lower()
        default_effort = "none" if re.match(r"gpt-5\.[1-9]", model.lower()) else None
        self.effort = None if non_reasoning else (configured_effort or default_effort)
        # Reasoning tokens are billed inside max_completion_tokens; thinking
        # lanes raise the cap the same way ANTHROPIC_MAX_TOKENS does.
        configured = _setting("OPENAI_MAX_TOKENS")
        self.max_tokens = int(configured) if configured else max_tokens
        key = api_key or _setting("OPENAI_API_KEY")
        if not key:
            raise LLMError(f"missing OPENAI_API_KEY for OpenAI model {model!r}")
        self._key = key
        self._timeout = timeout
        self._ssl = ssl.create_default_context()
        self.concurrent_batching = (
            (_setting("API_CONCURRENT_BATCHING") or "0").lower()
            in {"1", "true", "yes", "on"}
        )
        self._request_semaphore = threading.BoundedSemaphore(
            max(1, int(_setting("API_CONCURRENCY") or "1"))
        )
        self._max_attempts = max(1, int(_setting("API_MAX_ATTEMPTS") or "5"))

    def _body(self, system: str, messages: list[dict[str, str]]) -> dict:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "max_completion_tokens": self.max_tokens,
        }
        if self.effort is not None:
            body["reasoning_effort"] = self.effort
        if self.temperature is not None:
            body["temperature"] = self.temperature
        return body

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        with self._request_semaphore:
            return self._complete_locked(system, messages)

    def _complete_locked(self, system: str, messages: list[dict[str, str]]) -> str:
        data = json.dumps(self._body(system, messages)).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self._key}",
        }
        last = ""
        for attempt in range(self._max_attempts):
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=data, method="POST", headers=headers,
            )
            try:
                with urllib.request.urlopen(
                    request, context=self._ssl, timeout=self._timeout
                ) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                text = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                text = text.strip()
                if not text:
                    raise LLMError("model returned no text")
                return text
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}"
                if (exc.code in (429, 500, 502, 503, 504)
                        and attempt < self._max_attempts - 1):
                    time.sleep(_api_retry_delay(exc, attempt))
                    continue
                raise LLMError(last) from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = f"request failed: {exc}"
                if attempt < self._max_attempts - 1:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                raise LLMError(last) from exc
        raise LLMError(last or "exhausted retries")

    def complete_many(
        self, requests: list[tuple[str, list[dict[str, str]]]]
    ) -> list[str]:
        return _api_complete_many(self, requests)


class OpenAICompatClient:
    """OpenAI-compatible /v1/chat/completions client for self-hosted models
    (vLLM on the SLURM cluster). Base URL from LOCAL_LLM_BASE_URL (env or
    benchmark/.env), e.g. http://node-3:8000/v1. temperature pinned 0.0."""

    def __init__(self, model: str, base_url: str | None = None,
                 api_key: str | None = None, timeout: int = 300,
                 max_tokens: int = 4096, temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature
        url = base_url or _setting("LOCAL_LLM_BASE_URL")
        if not url:
            raise LLMError(f"missing LOCAL_LLM_BASE_URL for local model {model!r} "
                           "(set it to your server's API root, e.g. http://localhost:8000/v1)")
        self._url = url.rstrip("/") + "/chat/completions"
        self._key = api_key or _setting("LOCAL_LLM_API_KEY") or "sk-local"
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._ssl = ssl.create_default_context()

    def _body(self, system: str, messages: list[dict[str, str]]) -> dict:
        return {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "system", "content": system}] + messages,
        }

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        data = json.dumps(self._body(system, messages)).encode("utf-8")
        headers = {"content-type": "application/json",
                   "authorization": f"Bearer {self._key}"}
        last = ""
        for attempt in range(5):
            request = urllib.request.Request(self._url, data=data, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(request, context=self._ssl, timeout=self._timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                message = (payload.get("choices") or [{}])[0].get("message") or {}
                text = (message.get("content") or "").strip()
                if not text:
                    raise LLMError("model returned no text")
                return text
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}"
                if exc.code in (429, 500, 502, 503, 504) and attempt < 4:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                raise LLMError(last) from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = f"request failed: {exc}"
                if attempt < 4:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                raise LLMError(last) from exc
        raise LLMError(last or "exhausted retries")


class CodexCLIClient:
    """ChatGPT-authenticated Codex CLI client for benchmark turns.

    This backend is intentionally selected with a ``codex:`` model prefix so
    it cannot be confused with the Azure Chat Completions route.  Each turn
    replays the complete benchmark-owned conversation, pins the exact model
    and reasoning effort, and records the model reported by the CLI.
    """

    backend = "codex_cli"

    def __init__(
        self,
        model: str,
        *,
        effort: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.model = model.removeprefix("codex:")
        self.effort = effort or _setting("CODEX_MODEL_REASONING_EFFORT") or "high"
        self.temperature = None
        self._timeout = timeout or int(_setting("CODEX_MODEL_TIMEOUT") or "900")
        self.total_tokens = 0
        self.calls = 0
        try:
            version = subprocess.run(
                ["codex", "--version"],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise LLMError(f"Codex CLI is unavailable: {exc}") from exc
        if version.returncode != 0:
            raise LLMError("Codex CLI preflight failed: " + version.stderr.strip())
        self.codex_version = version.stdout.strip()

    @staticmethod
    def _metadata(stderr: str, key: str) -> str:
        import re

        match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", stderr)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _tokens(stderr: str) -> int:
        import re

        match = re.search(r"(?m)^tokens used\s*\n\s*([0-9,]+)\s*$", stderr)
        return int(match.group(1).replace(",", "")) if match else 0

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        rendered_messages = "\n\n".join(
            f"{str(item.get('role') or 'user').upper()}:\n{item.get('content') or ''}"
            for item in messages
        )
        prompt = (
            "You are the model inside a controlled automation benchmark. "
            "Do not inspect the filesystem, run shell commands, browse, or use Codex "
            "tools. Respond only to the benchmark conversation.\n\n"
            f"SYSTEM:\n{system}\n\n{rendered_messages}"
        )
        with tempfile.TemporaryDirectory(prefix="agentorch_codex_eval_") as tmp:
            output_path = os.path.join(tmp, "last_message.txt")
            command = [
                "codex",
                "exec",
                "--ephemeral",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                self.model,
                "-c",
                f'model_reasoning_effort="{self.effort}"',
                "-c",
                'model_reasoning_summary="none"',
                "--output-last-message",
                output_path,
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
                    timeout=self._timeout,
                    check=False,
                    env=child_env,
                    # Keep the benchmark model outside the repository.  The
                    # prompt already forbids Codex tools, but an empty working
                    # directory also prevents accidental discovery of task
                    # files or hidden gold through ordinary relative paths.
                    cwd=tmp,
                )
            except subprocess.TimeoutExpired as exc:
                raise LLMError(
                    f"Codex benchmark turn timed out after {self._timeout} seconds"
                ) from exc
            if completed.returncode != 0:
                raise LLMError(
                    f"Codex benchmark turn failed ({completed.returncode}): "
                    + completed.stderr[-2000:].strip()
                )
            returned_model = self._metadata(completed.stderr, "model")
            returned_effort = self._metadata(completed.stderr, "reasoning effort")
            if returned_model != self.model or returned_effort != self.effort:
                raise LLMError(
                    "Codex metadata mismatch: "
                    f"model={returned_model!r}, effort={returned_effort!r}; "
                    f"expected {self.model!r}/{self.effort!r}"
                )
            if not os.path.isfile(output_path):
                raise LLMError("Codex produced no benchmark response")
            text = Path(output_path).read_text(encoding="utf-8").strip()
            if not text:
                raise LLMError("Codex returned an empty benchmark response")
            self.calls += 1
            self.total_tokens += self._tokens(completed.stderr)
            return text


def _native_context_tokens(config) -> int:
    """Context length from a model config, including composite multimodal
    configs whose window lives on ``text_config``."""
    value = getattr(config, "max_position_embeddings", None)
    if not value:
        text_config = getattr(config, "text_config", None)
        if text_config is not None:
            value = getattr(text_config, "max_position_embeddings", None)
    return int(value or 32768)


class TransformersClient:
    """Greedy local Hugging Face inference for SLURM GPU jobs.

    Heavy dependencies are imported lazily so the ordinary simulator and API
    clients remain stdlib-only. One instance is reused for the full eval
    process; ``task.run_eval`` never reloads weights between tasks or modes.
    """

    backend = "transformers"
    do_sample = False

    def __init__(
        self,
        model: str,
        *,
        revision: str | None = None,
        max_new_tokens: int | None = None,
    ) -> None:
        try:
            import torch
            from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise LLMError(
                "local Hugging Face inference requires torch, transformers, "
                "and accelerate"
            ) from exc

        self.model = model
        self.revision = revision or _setting("HF_MODEL_REVISION") or "main"
        self.max_new_tokens = max_new_tokens or int(
            _setting("HF_MAX_NEW_TOKENS") or "4096"
        )
        self.react_max_new_tokens = int(
            _setting("HF_REACT_MAX_NEW_TOKENS") or "8192"
        )
        self.react_soft_max_new_tokens = int(
            _setting("HF_REACT_SOFT_MAX_NEW_TOKENS")
            or "1024"
        )
        self.dtype = "bfloat16"
        self.temperature = 0.0
        self.calls = 0
        self.total_tokens = 0
        self.last_completion_token_counts: list[int] = []
        requested_input = int(_setting("HF_MAX_INPUT_TOKENS") or "122880")
        requested_context = int(
            _setting("HF_MODEL_CONTEXT_TOKENS") or str(requested_input + max(self.max_new_tokens, self.react_max_new_tokens))
        )
        if requested_input > requested_context:
            raise LLMError(
                "HF_MAX_INPUT_TOKENS cannot exceed HF_MODEL_CONTEXT_TOKENS"
            )
        try:
            torch.manual_seed(0)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(0)
                if (_setting("HF_DISABLE_CUDNN_SDP") or "0") == "1":
                    # cuDNN's SDPA kernel fails (mha_graph.execute) on some
                    # very long sequence shapes; keep SDPA on the flash /
                    # mem-efficient backends instead (eager is O(n^2) memory
                    # and OOMs at ~100K-token prompts).
                    torch.backends.cuda.enable_cudnn_sdp(False)
            self._tokenizer = AutoTokenizer.from_pretrained(
                model,
                revision=self.revision,
                use_fast=True,
                trust_remote_code=_trust_remote_code(),
            )
            config = AutoConfig.from_pretrained(
                model,
                revision=self.revision,
                trust_remote_code=_trust_remote_code(),
            )
            native_context = _native_context_tokens(config)
            self.context_extension = None
            if requested_context > native_context and config.model_type == "qwen2":
                # Qwen2.5 Instruct publishes a 128K tokenizer but pins the
                # default model config to 32K.  Its official long-text recipe
                # enables static YaRN with factor 4 for 131,072-token inputs.
                factor = requested_context / native_context
                # Transformers 5 standardizes this under ``rope_parameters``;
                # assigning the deprecated ``rope_scaling`` attribute after
                # config construction leaves Qwen's rotary module without its
                # required ``rope_type`` field.
                config.rope_parameters = {
                    "rope_type": "yarn",
                    "factor": factor,
                    "original_max_position_embeddings": native_context,
                    "rope_theta": float(
                        (getattr(config, "rope_parameters", None) or {}).get(
                            "rope_theta", 1_000_000.0
                        )
                    ),
                }
                config.max_position_embeddings = requested_context
                self.context_extension = {
                    "method": "yarn",
                    "factor": factor,
                    "original_max_position_embeddings": native_context,
                    "max_position_embeddings": requested_context,
                }
            loader_kwargs = dict(
                revision=self.revision,
                config=config,
                dtype=torch.bfloat16,
                device_map="auto",
                low_cpu_mem_usage=True,
                # sdpa default; HF_ATTN_IMPL=eager works around cuDNN
                # SDPA graph-execution failures on specific sequence shapes
                attn_implementation=_setting("HF_ATTN_IMPL") or "sdpa",
                trust_remote_code=_trust_remote_code(),
            )
            try:
                self._model = AutoModelForCausalLM.from_pretrained(
                    model, **loader_kwargs
                )
            except ValueError:
                # Multimodal single-checkpoint architectures (e.g. Muse
                # Glimmer's conditional-generation class) register under
                # the image-text auto class; text-only generation works
                # through the same generate() surface.
                from transformers import AutoModelForImageTextToText

                self._model = AutoModelForImageTextToText.from_pretrained(
                    model, **loader_kwargs
                )
            self._model.eval()
        except Exception as exc:
            raise LLMError(f"failed to load {model}@{self.revision}: {exc}") from exc
        self._torch = torch
        configured = _native_context_tokens(self._model.config)
        self.max_input_tokens = min(configured, requested_input)
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token_id = self._tokenizer.eos_token_id

    def prompt_token_count(self, system: str, messages: list[dict[str, str]]) -> int:
        """Rendered prompt length in tokens (input-token accounting only)."""
        prompt = _render_chat_prompt(self._tokenizer, system, messages)
        if isinstance(prompt, list):
            return len(prompt)
        return len(self._tokenizer(prompt, add_special_tokens=False)["input_ids"])

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        from transformers import StoppingCriteria, StoppingCriteriaList

        try:
            prompt = _render_chat_prompt(self._tokenizer, system, messages)
            if isinstance(prompt, list):
                import torch

                inputs = {
                    "input_ids": torch.tensor([prompt], dtype=torch.long),
                    "attention_mask": torch.ones(
                        (1, len(prompt)), dtype=torch.long
                    ),
                }
            else:
                inputs = self._tokenizer(
                    prompt,
                    return_tensors="pt",
                    add_special_tokens=False,
                )
            input_tokens = int(inputs["input_ids"].shape[-1])
            if input_tokens > self.max_input_tokens:
                raise LLMError(
                    f"prompt has {input_tokens} tokens, exceeding pinned "
                    f"limit {self.max_input_tokens}; truncation is forbidden"
                )
            device = next(self._model.parameters()).device
            inputs = {key: value.to(device) for key, value in inputs.items()}
            tokenizer = self._tokenizer

            class CompleteJSON(StoppingCriteria):
                def __call__(self, input_ids, scores, **kwargs):
                    generated = tokenizer.decode(
                        input_ids[0, input_tokens:],
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=False,
                    )
                    return _complete_json_prefix(generated)

            with self._torch.inference_mode():
                generation_limit = (
                    self.react_max_new_tokens
                    if system.startswith("You are an automation agent.")
                    else self.max_new_tokens
                )
                # Harmony-style channel formats interleave
                # brace-laden analysis text before the surfaced answer, and
                # their channel markers are special tokens invisible to the
                # decoded-text scanner — the balanced-JSON early stop would
                # fire mid-reasoning. Such lanes disable it and generate to
                # the model's own EOS (the generation_config list, e.g.
                # Muse's [200001, 200008], not the single tokenizer id).
                early_stop = (_setting("HF_JSON_EARLYSTOP") or "1") != "0"
                eos_ids = getattr(
                    self._model.generation_config, "eos_token_id", None
                )
                if eos_ids is None:
                    eos_ids = self._tokenizer.eos_token_id
                generate_kwargs = dict(
                    max_new_tokens=generation_limit,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=eos_ids,
                )
                if early_stop:
                    generate_kwargs["stopping_criteria"] = (
                        StoppingCriteriaList([CompleteJSON()])
                    )
                output = self._model.generate(**inputs, **generate_kwargs)
            generated = output[0, input_tokens:]
            # Harmony-style channel formats route the surfaced answer behind
            # an exact header that includes special tokens (Muse:
            # "to=user<|message|>"); split on its last occurrence in the
            # unstripped decode so reasoning never reaches extraction. A
            # plain-text marker ("to=user") is unsafe — it can occur inside
            # the answer's own strings and cut the answer apart. Absent
            # marker (or lanes that never set one): plain stripped decode.
            dump_dir = _setting("HF_DEBUG_DUMP_DIR")
            if dump_dir:
                try:
                    os.makedirs(dump_dir, exist_ok=True)
                    dump_path = os.path.join(
                        dump_dir, f"gen-{os.getpid()}-{self.calls}.txt"
                    )
                    with open(dump_path, "w") as handle:
                        handle.write(
                            self._tokenizer.decode(
                                generated, skip_special_tokens=False
                            )
                        )
                except OSError:
                    pass
            marker = _setting("HF_RESPONSE_SPLIT_MARKER")
            text = None
            channel_isolated = False
            if marker:
                unstripped = self._tokenizer.decode(
                    generated,
                    skip_special_tokens=False,
                )
                if marker in unstripped:
                    tail = unstripped.rsplit(marker, 1)[1]
                    text = re.sub(r"<\|[^<>]*?\|>", " ", tail).strip()
                    channel_isolated = True
            if text is None:
                text = self._tokenizer.decode(
                    generated,
                    skip_special_tokens=True,
                ).strip()
            text = _strip_thinking(text).strip()
            # When the channel split succeeded, the tail IS the surfaced
            # answer — last-JSON extraction could only discard salvageable
            # context (the downstream parser has its own missing-closer
            # repair). Extraction remains for the no-marker fallback.
            if text and _setting("HF_TAKE_LAST_JSON") and not channel_isolated:
                text = _take_last_json(text)
            if not text:
                raise LLMError("model returned no text")
            self.calls += 1
            self.total_tokens += int(generated.shape[-1])
            return text
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"local generation failed: {exc}") from exc


class VLLMClient:
    """Single-GPU offline vLLM client with cross-variant prefix caching."""

    backend = "vllm"
    do_sample = False

    def __init__(
        self,
        model: str,
        *,
        revision: str | None = None,
        max_new_tokens: int | None = None,
    ) -> None:
        try:
            from transformers import AutoConfig
            from vllm import LLM, SamplingParams
            from task.vllm_json_stop import CompleteJSONLogitsProcessor
        except ImportError as exc:
            raise LLMError("local vLLM inference requires vllm") from exc

        self.model = model
        self.batch_initial_plans = True
        self.revision = revision or _setting("HF_MODEL_REVISION") or "main"
        self.max_new_tokens = max_new_tokens or int(
            _setting("HF_MAX_NEW_TOKENS") or "4096"
        )
        self.react_max_new_tokens = int(
            _setting("HF_REACT_MAX_NEW_TOKENS") or "8192"
        )
        self.react_soft_max_new_tokens = int(
            _setting("HF_REACT_SOFT_MAX_NEW_TOKENS")
            or "1024"
        )
        self.dtype = "bfloat16"
        # Greedy by default; HF_TEMPERATURE>0 enables temperature sampling
        # (engine seed stays 0, top_p stays 1.0) for uncertainty sweeps.
        self.temperature = float(_setting("HF_TEMPERATURE") or "0")
        self.calls = 0
        self.total_tokens = 0
        self.last_completion_token_counts: list[int] = []
        self._batch_condition = threading.Condition()
        self._pending_completions: list[dict[str, object]] = []
        self._batch_leader_active = False
        self.concurrent_batching = (
            (_setting("VLLM_CONCURRENT_BATCHING") or "0").lower()
            in {"1", "true", "yes"}
        )
        cache_home = Path(
            os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface"
        )
        snapshot_path = (
            cache_home
            / "hub"
            / ("models--" + model.replace("/", "--"))
            / "snapshots"
            / self.revision
        )
        engine_model = str(snapshot_path) if snapshot_path.is_dir() else model
        requested_input = int(_setting("HF_MAX_INPUT_TOKENS") or "122880")
        requested_context = int(
            _setting("HF_MODEL_CONTEXT_TOKENS") or str(requested_input + max(self.max_new_tokens, self.react_max_new_tokens))
        )
        if requested_input + max(
            self.max_new_tokens, self.react_max_new_tokens
        ) > requested_context:
            raise LLMError(
                "HF_MAX_INPUT_TOKENS + the active generation limit cannot exceed "
                "HF_MODEL_CONTEXT_TOKENS"
            )
        try:
            config = AutoConfig.from_pretrained(
                engine_model,
                revision=None if engine_model != model else self.revision,
                trust_remote_code=_trust_remote_code(),
            )
            native_context = _native_context_tokens(config)
            hf_overrides: dict[str, object] = {}
            self.context_extension = None
            if requested_context > native_context and config.model_type == "qwen2":
                factor = requested_context / native_context
                rope_theta = float(
                    (getattr(config, "rope_parameters", None) or {}).get(
                        "rope_theta", 1_000_000.0
                    )
                )
                hf_overrides = {
                    "max_position_embeddings": requested_context,
                    "rope_parameters": {
                        "rope_type": "yarn",
                        "factor": factor,
                        "original_max_position_embeddings": native_context,
                        "rope_theta": rope_theta,
                    },
                }
                self.context_extension = {
                    "method": "yarn",
                    "factor": factor,
                    "original_max_position_embeddings": native_context,
                    "max_position_embeddings": requested_context,
                }
            self._engine = LLM(
                model=engine_model,
                tokenizer=engine_model,
                revision=None if engine_model != model else self.revision,
                dtype="bfloat16",
                max_model_len=requested_context,
                gpu_memory_utilization=float(
                    _setting("VLLM_GPU_MEMORY_UTILIZATION") or "0.90"
                ),
                # >1 shards checkpoints that exceed one device (70B-class on
                # two H200s); the launcher allocates matching GPUs.
                tensor_parallel_size=int(_setting("VLLM_TENSOR_PARALLEL") or "1"),
                trust_remote_code=_trust_remote_code(),
                enable_prefix_caching=True,
                # Some architectures mandate a KV-cache dtype (e.g.
                # DeepSeek-V4's fp8_ds_mla attention requires fp8); the
                # launcher declares it per model lane.
                kv_cache_dtype=_setting("VLLM_KV_CACHE_DTYPE") or "auto",
                # Async scheduling triggers tokenizer thread-safety races
                # for some tokenizer modes (deepseek_v4); lanes may disable it.
                async_scheduling=(_setting("VLLM_ASYNC_SCHEDULING") or "1") != "0",
                # Architectures newer than the engine registry can run
                # through vLLM's transformers modeling backend when the lane
                # declares it (isolated newer-stack lanes only).
                model_impl=_setting("VLLM_MODEL_IMPL") or "auto",
                seed=0,
                hf_overrides=hf_overrides,
                logits_processors=[CompleteJSONLogitsProcessor],
            )
            self._sampling_params_type = SamplingParams
            self._tokenizer = self._engine.get_tokenizer()
            # Per-thread, per-call counters: shared totals (calls,
            # total_tokens) are useless for one request's cost when
            # trajectories/planning calls run concurrently through the batch.
            self._tls = threading.local()
            # HF fast tokenizers are not thread-safe (concurrent use
            # raises "Already borrowed"); serialize template rendering.
            self._tokenizer_lock = threading.Lock()
        except Exception as exc:
            raise LLMError(f"failed to load {model}@{self.revision} with vLLM: {exc}") from exc
        self.max_input_tokens = requested_input

    @property
    def last_call_completion_tokens(self) -> int | None:
        """Completion tokens of this thread's most recent complete() call."""
        return getattr(self._tls, "completion_tokens", None)

    @property
    def last_call_prompt_tokens(self) -> int | None:
        """Rendered prompt tokens of this thread's most recent complete() call."""
        return getattr(self._tls, "prompt_tokens", None)

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        self._tls.completion_tokens = None
        self._tls.prompt_tokens = None
        if not self.concurrent_batching:
            text = self.complete_many([(system, messages)])[0]
            counts = list(getattr(self, "last_completion_token_counts", []) or [])
            self._tls.completion_tokens = counts[0] if counts else None
            return text
        # Validate this trajectory before joining a shared batch. A context
        # overflow belongs only to this request and must not poison peers.
        self._prepare_prompt(system, messages)
        item: dict[str, object] = {
            "request": (system, messages),
        }
        with self._batch_condition:
            self._pending_completions.append(item)
            while "result" not in item and "exception" not in item:
                if not self._batch_leader_active:
                    self._batch_leader_active = True
                    is_leader = True
                    break
                self._batch_condition.wait()
            else:
                is_leader = False
        if is_leader:
            # Give concurrently starting trajectories a small window to join
            # this scheduler batch. Leadership rotates after every batch so a
            # completed episode can return and be checkpointed immediately.
            time.sleep(float(_setting("VLLM_BATCH_WAIT_SECONDS") or "0.01"))
            with self._batch_condition:
                batch = self._pending_completions
                self._pending_completions = []
            try:
                outputs = self.complete_many_indexed(
                    [entry["request"] for entry in batch]  # type: ignore[list-item]
                )
                counts = list(getattr(self, "last_completion_token_counts", []) or [])
                if len(counts) != len(batch):
                    counts = [None] * len(batch)
                for entry, output, count in zip(batch, outputs, counts, strict=True):
                    # Per-request failures reach only their own trajectory;
                    # batch peers keep their completions.
                    entry["completion_tokens"] = count
                    if isinstance(output, LLMError):
                        entry["exception"] = output
                    else:
                        entry["result"] = output
            except Exception as exc:
                for entry in batch:
                    entry["exception"] = exc
            finally:
                with self._batch_condition:
                    self._batch_leader_active = False
                    self._batch_condition.notify_all()
        with self._batch_condition:
            while "result" not in item and "exception" not in item:
                self._batch_condition.wait()
        self._tls.completion_tokens = item.get("completion_tokens")
        if "exception" in item:
            raise item["exception"]  # type: ignore[misc]
        return str(item["result"])

    def complete_many(
        self,
        requests: list[tuple[str, list[dict[str, str]]]],
    ) -> list[str]:
        """Generate requests in one vLLM scheduler batch, preserving order.

        Raises on the first per-request failure; batch-aware callers should
        use complete_many_indexed so one bad request cannot discard the
        completions of its batch peers."""

        results = self.complete_many_indexed(requests)
        for result in results:
            if isinstance(result, LLMError):
                raise result
        return results  # type: ignore[return-value]

    def complete_many_indexed(
        self,
        requests: list[tuple[str, list[dict[str, str]]]],
    ) -> list:
        """Generate a batch, returning a str or LLMError per request.

        Per-request failures (context overflow, empty completion) land only
        at their own index; an engine-level failure still raises for the
        whole batch."""

        if not requests:
            return []
        results: list = [None] * len(requests)
        prompts: list[object] = []
        params: list[object] = []
        live_indices: list[int] = []
        for index, (system, messages) in enumerate(requests):
            try:
                prompt, generation_limit = self._prepare_prompt(system, messages)
            except LLMError as exc:
                results[index] = exc
                continue
            prompts.append(prompt)
            params.append(
                self._sampling_params_type(
                    temperature=self.temperature,
                    max_tokens=generation_limit,
                )
            )
            live_indices.append(index)
        token_counts: list[int] = [0] * len(requests)
        if live_indices:
            debug_dir = _setting("HF_GEN_DEBUG_DIR")
            debug_path = None
            if debug_dir:
                # Batch-level flight recorder for engine-wedge diagnosis: the
                # last "begin" without a matching "done" is the hung batch.
                try:
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_path = os.path.join(
                        debug_dir,
                        f"genlog-{os.environ.get('SLURM_JOB_ID', os.getpid())}.jsonl",
                    )
                    sizes = [
                        len(p["prompt_token_ids"]) if isinstance(p, dict) else -1
                        for p in prompts
                    ]
                    with open(debug_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps({
                            "event": "begin", "t": time.time(),
                            "n": len(prompts),
                            "max_tokens": [p.max_tokens for p in params],
                            "prompt_tokens": sizes,
                        }) + "\n")
                        fh.flush()
                except OSError:
                    debug_path = None
            try:
                request_outputs = self._engine.generate(
                    prompts, params, use_tqdm=False
                )
            except Exception as exc:
                raise LLMError(f"vLLM generation failed: {exc}") from exc
            if debug_path:
                try:
                    with open(debug_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps({
                            "event": "done", "t": time.time(), "n": len(prompts),
                        }) + "\n")
                        fh.flush()
                except OSError:
                    pass
            for index, request_output in zip(
                live_indices, request_outputs, strict=True
            ):
                completion = request_output.outputs[0]
                token_counts[index] = len(completion.token_ids)
                text = _strip_thinking(completion.text).strip()
                if text and _setting("HF_TAKE_LAST_JSON"):
                    text = _take_last_json(text)
                if not text:
                    # Self-describing failure: distinguish a thinking-budget
                    # overrun (finish_reason=length inside an unterminated
                    # <think> span) from a genuinely empty completion.
                    raw = completion.text or ""
                    dump_dir = _setting("HF_DEBUG_DUMP_DIR")
                    if dump_dir:
                        try:
                            os.makedirs(dump_dir, exist_ok=True)
                            stamp = f"{time.time():.6f}".replace(".", "_")
                            with open(os.path.join(
                                dump_dir, f"notext-{stamp}.txt"
                            ), "w", encoding="utf-8") as fh:
                                fh.write(raw)
                        except OSError:
                            pass
                    results[index] = LLMError(
                        "model returned no text "
                        f"(completion_tokens={len(completion.token_ids)}, "
                        f"finish_reason={getattr(completion, 'finish_reason', None)}, "
                        f"raw_len={len(raw)}, raw_tail={raw[-120:]!r})"
                    )
                    continue
                results[index] = text
        self.last_completion_token_counts = token_counts
        self.total_tokens += sum(token_counts)
        self.calls += sum(1 for r in results if isinstance(r, str))
        return results

    def prompt_token_count(self, system: str, messages: list[dict[str, str]]) -> int:
        """Rendered prompt length in tokens (input-token accounting only)."""
        with self._tokenizer_lock:
            prompt = _render_chat_prompt(self._tokenizer, system, messages)
            if isinstance(prompt, list):
                return len(prompt)
            return len(self._tokenizer(prompt, add_special_tokens=False)["input_ids"])

    def _prepare_prompt(
        self, system: str, messages: list[dict[str, str]]
    ) -> tuple[object, int]:
        with self._tokenizer_lock:
            try:
                prompt = _render_chat_prompt(self._tokenizer, system, messages)
            except LLMError:
                raise
            except Exception as exc:
                # Chat-template rejections (e.g. jinja TemplateError for
                # non-alternating roles) must fail the row, not the process.
                raise LLMError(f"chat template rendering failed: {exc}") from exc
            if isinstance(prompt, list):
                input_tokens = len(prompt)
            else:
                input_tokens = len(
                    self._tokenizer(prompt, add_special_tokens=False)["input_ids"]
                )
        if isinstance(prompt, list):
            prompt = {"prompt_token_ids": prompt}
        self._tls.prompt_tokens = input_tokens
        if input_tokens > self.max_input_tokens:
            raise LLMError(
                f"prompt has {input_tokens} tokens, exceeding pinned "
                f"limit {self.max_input_tokens}; truncation is forbidden"
            )
        generation_limit = (
            self.react_max_new_tokens
            if system.startswith("You are an automation agent.")
            else self.max_new_tokens
        )
        return prompt, generation_limit


def build_client(model: str):
    if model.startswith("compat:"):
        served_model = model.removeprefix("compat:")
        if not served_model:
            raise LLMError("compat: requires a served model name")
        return OpenAICompatClient(served_model)
    if model.startswith("codex:"):
        return CodexCLIClient(model)
    if model.startswith("hf:"):
        client_type = VLLMClient if (_setting("HF_LOCAL_ENGINE") or "transformers").lower() == "vllm" else TransformersClient
        return client_type(model.removeprefix("hf:"))
    low = model.lower()
    if low.startswith(("gpt", "azure", "openai", "o1", "o3", "o4")):
        # OPENAI_API_MODE=direct selects api.openai.com with Bearer auth
        # (GPT-5 family); the default remains the Azure deployment client.
        if (_setting("OPENAI_API_MODE") or "").lower() == "direct":
            return OpenAIDirectClient(model)
        return AzureOpenAIClient(model)
    if low.startswith(("claude", "anthropic")):
        return AnthropicClient(model)
    # self-hosted open-weight models (HF repo ids like zai-org/GLM-5.2-FP8,
    # meta-llama/Llama-3.3-70B-Instruct, Qwen/Qwen2.5-72B-Instruct)
    return OpenAICompatClient(model)
