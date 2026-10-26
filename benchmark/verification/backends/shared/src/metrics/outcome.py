"""Observable outcome scoring under the canonical-trace policy.

Primary ``outcome_pass`` requires exact canonical terminal and side-effect
call representations plus the expected observable state.  The historical
normalized semantic outcome is retained as ``outcome_semantic_pass`` for
diagnosis only; it cannot promote a non-canonical output to correctness.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from benchmark.verifier import _check

TERMINAL_TOOLS = {
    "workato_api_platform.return_response",
    "workato_recipe_function.return_result",
    "workato_service.send_reply",
    "workato_service.call_service",
    "workato_genie.workflow_return_result",
    "workato_pub_sub.publish_to_topic",
}

_MOCK_STATE_BACKENDS = ("workato_db_table", "lookup_table")

# Live backends with NO snapshot/read-back tool (Slack posts, Jira issues,
# Drive folders): the observable outcome IS the outbound call the live API
# accepted, so successful mutating calls are compared as side-effect outputs.
# Registry call logs contain successful calls only (failed calls raise before
# logging), so retries never double-count.
SIDE_EFFECT_TOOLS = {
    "slack.post_message",
    "slack.post_reply",
    "slack.update_blocks_by_block_id",
    "slack.delete_message",
    "slack_bot.open_bot_app_home",
    "slack_bot.block_kit_modals",
    "slack_bot.generate_menu_options",
    "jira.create_issue",
    "jira.delete_issue",
    "google_drive.create_folder",
    "workato_runtime.log_message",
}

# State-transition operations whose required effect can disappear from the final
# snapshot. A stop->start restart begins and ends in "running", and rerunning a
# job is an event rather than a durable row. These are compared as an ORDERED
# successful-event trace; reads such as get_recipe/list_jobs remain irrelevant.
TRANSIENT_EVENT_TOOLS = {
    "workato_app.stop_recipe",
    "workato_app.start_recipe",
    "workato_app.rerun_jobs",
}


def _transient_event_args(tool: str, args: dict[str, Any]) -> Any:
    normalized = normalize_terminal_value(args or {})
    if not isinstance(normalized, dict):
        return normalized
    # Explicit connector defaults are semantically the same as omission.
    if tool == "workato_app.stop_recipe" and normalized.get("force") is False:
        normalized = dict(normalized)
        normalized.pop("force", None)
    return normalized


def _transient_events(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tool": str(call.get("tool") or ""),
            "args": _transient_event_args(
                str(call.get("tool") or ""),
                call.get("args") or {},
            ),
        }
        for call in calls or []
        if str(call.get("tool") or "") in TRANSIENT_EVENT_TOOLS
    ]

# Slack message timestamps are minted by Slack per run and thread/update/
# delete args carry them; dropped SYMMETRICALLY like Salesforce record ids.
_SLACK_TS_RE = re.compile(r"^\d{10}\.\d{3,6}$")
_TS_KEYS = {"ts", "message_ts", "thread_ts", "event_ts"}


def _stable_side_effect_args(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in _TS_KEYS:
                continue
            if isinstance(item, str) and _SLACK_TS_RE.fullmatch(item):
                continue
            out[key] = _stable_side_effect_args(item)
        return out
    if isinstance(value, list):
        return [_stable_side_effect_args(item) for item in value]
    return value


def _effective_slack_side_effect_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize connector encodings that render the same Slack message.

    The simulated Slack surface accepts a compact one-section ``blocks`` form.
    When that section repeats ``text`` exactly, it changes only the transport
    representation: the visible section and fallback text carry identical
    bytes.  Keep every other Block Kit payload strict.
    """

    normalized = _stable_side_effect_args(args)
    if tool == "slack_bot.open_bot_app_home":
        from benchmark.argument_semantics import canonical_slack_home_args

        return canonical_slack_home_args(normalized)
    if tool not in {"slack.post_message", "slack.post_reply"}:
        return normalized
    if not isinstance(normalized, dict):
        return normalized
    blocks = normalized.get("blocks")
    text = normalize_terminal_value(normalized.get("text"))
    block = blocks[0] if isinstance(blocks, list) and len(blocks) == 1 else None
    if (
        isinstance(block, dict)
        and set(block).issubset({"type", "section_text"})
        and block.get("type") in (None, "section")
        and normalize_terminal_value(block.get("section_text")) == text
    ):
        normalized = dict(normalized)
        normalized.pop("blocks", None)
    return normalized


def _side_effect_outputs(calls: list[dict[str, Any]]) -> Counter:
    out: Counter = Counter()
    for call in calls or []:
        tool = str(call.get("tool") or "")
        if tool in SIDE_EFFECT_TOOLS:
            normalized = normalize_terminal_value(
                {
                    "tool": tool,
                    "args": _effective_slack_side_effect_args(
                        tool,
                        call.get("args") or {},
                    ),
                }
            )
            out[json.dumps(normalized, sort_keys=True, default=str)] += 1
    return out


def _exact_side_effect_outputs(calls: list[dict[str, Any]]) -> Counter:
    """Canonical-JSON side-effect calls without semantic coercion."""

    out: Counter = Counter()
    for call in calls or []:
        tool = str(call.get("tool") or "")
        if tool not in SIDE_EFFECT_TOOLS:
            continue
        out[
            json.dumps(
                {"tool": tool, "args": call.get("args") or {}},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        ] += 1
    return out


def _exact_transient_events(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordered transient events with exact, uncoerced argument objects."""

    return [
        {
            "tool": str(call.get("tool") or ""),
            "args": call.get("args") or {},
        }
        for call in calls or []
        if str(call.get("tool") or "") in TRANSIENT_EVENT_TOOLS
    ]

# Salesforce fields that can never match across two faithful live runs: audit
# stamps and org auto-number counters advance on every run, and record ids are
# minted fresh. Dropped SYMMETRICALLY from gold and agent snapshots.
_SF_VOLATILE_FIELD_KEYS = {
    "Id", "CreatedDate", "LastModifiedDate", "SystemModstamp",
    "LastViewedDate", "LastReferencedDate", "LastActivityDate",
    "CaseNumber", "ContractNumber", "OrderNumber", "OrderItemNumber",
    "ContractLineItemNumber", "IsClosed", "IsWon", "IsDeleted",
}
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15}(?:[A-Za-z0-9]{3})?$")


def _sf_stable_fields(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if (
                key in _SF_VOLATILE_FIELD_KEYS
                or key == ""
                or str(key).startswith(".")
                or "." in str(key)
                or item is None
                or item == {}
                or (
                    isinstance(item, dict)
                    and (
                        str(key).endswith("__r")
                        or str(key) in {"Product2", "PricebookEntry"}
                    )
                )
            ):
                continue
            if isinstance(item, str) and _SF_ID_RE.fullmatch(item):
                continue  # record-id-shaped value: fresh every live run
            normalized_item = _sf_stable_fields(item)
            if normalized_item == {}:
                continue
            out[key] = normalized_item
        # The simulator can expose a managed-package custom field under both
        # its physical namespaced spelling (``Pkg__Field__c``) and the
        # connector's convenience alias (``Field__c``). Keep the physical
        # key when both carry the same value; conflicting aliases remain and
        # correctly fail state equivalence.
        for key, item in list(out.items()):
            match = re.fullmatch(r"[A-Za-z0-9]+__(.+__c)", str(key))
            alias = match.group(1) if match else None
            if alias and alias in out and out[alias] == item:
                out.pop(alias)
        return out
    if isinstance(value, list):
        return [_sf_stable_fields(item) for item in value]
    return value


def _normalized_rows(rows: list[Any], drop: tuple[str, ...] = ("_row_id",)) -> Counter:
    """Multiset of rows with positional artifacts (`_row_id`, sheets
    `row_number`) dropped; row order and insertion history do not matter,
    values and provenance (`_created_by`/`_modified_by`) do."""
    out: Counter = Counter()
    for row in rows or []:
        if isinstance(row, dict):
            slim = {k: v for k, v in row.items() if k not in drop}
            if row.get("_created_by") == "agent":
                # Workato's Record ID is a connector-managed output. Legacy
                # gold recipes sometimes explicitly asked the connector to
                # stamp it while an equivalent public call lets the connector
                # manage identity implicitly. It is not business state for a
                # newly created row; seeded IDs remain observable.
                slim.pop("record_id", None)
                slim.pop("11fbe9a6_a16d_4d7e_86ea_afe42ec03005", None)
            out[json.dumps(slim, sort_keys=True, default=str)] += 1
        else:
            out[json.dumps(row, default=str)] += 1
    return out


_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)


def _canonical_snowflake_value(value: Any) -> Any:
    """Canonicalize SQL rows across live and deterministic backends.

    Unquoted Snowflake field names are case-insensitive.  The live harness can
    return both upper- and lower-case aliases for one column, while the
    deterministic client returns one lower-case key.  Datetime bindings can
    also round-trip either as UTC-offset strings or offset-free UTC values.
    """

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).casefold()
            normalized_item = _canonical_snowflake_value(item)
            if (
                normalized_key in result
                and result[normalized_key] != normalized_item
            ):
                # Conflicting case aliases are materially different and
                # remain visible to the equality check.
                result[f"{normalized_key}#case_conflict"] = normalized_item
            else:
                result[normalized_key] = normalized_item
        return result
    if isinstance(value, list):
        return [_canonical_snowflake_value(item) for item in value]
    if isinstance(value, str) and len(value) >= 2:
        # Workato's Snowflake connector accepts SQL-quoted transport literals
        # (often produced by Ruby ``.quote``), whereas the public benchmark
        # tool accepts the semantic scalar. Snowflake stores the latter.
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
    if isinstance(value, str) and _ISO_DATETIME_RE.fullmatch(value):
        iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(iso_value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.isoformat(timespec="microseconds").rstrip("0").rstrip(".")
    return value


def _normalized_snowflake_rows(rows: list[Any]) -> Counter:
    return _normalized_rows(
        [
            _canonical_snowflake_value(row)
            for row in rows or []
        ]
    )


def _canonical_state_tables(snapshot: dict[str, Any]) -> dict[str, dict[str, Counter]]:
    """Normalize every state-carrying snapshot section — mock backends AND
    live backends (Salesforce/Snowflake/Google Sheets) — into
    backend -> table/sobject -> row-multiset, with run-volatile identifiers
    dropped so two faithful live runs canonicalize identically
    (benmark_rules.md 'What is being measured': final result AND backend
    state)."""
    snapshot = snapshot or {}
    out: dict[str, dict[str, Counter]] = {}
    for backend in _MOCK_STATE_BACKENDS:
        tables = (snapshot.get(backend) or {}).get("tables")
        if tables is None:
            continue
        out[backend] = {str(t): _normalized_rows(rows or [])
                        for t, rows in tables.items()}
    sf_records = (snapshot.get("salesforce") or {}).get("records")
    if sf_records is not None:
        buckets: dict[str, Counter] = {}
        for record in sf_records or []:
            record = record if isinstance(record, dict) else {}
            sobject = str(record.get("sobject") or "")
            fields = _sf_stable_fields(record.get("fields") or {})
            buckets.setdefault(sobject, Counter())[
                json.dumps(fields, sort_keys=True, default=str)] += 1
        out["salesforce"] = buckets
    snow_tables = (snapshot.get("snowflake") or {}).get("tables")
    if snow_tables is None:
        snow_tables = (snapshot.get("snowflake_live") or {}).get("tables")
    if snow_tables is not None:
        out["snowflake"] = {str(t): _normalized_snowflake_rows(rows or [])
                            for t, rows in snow_tables.items()}
    sheets = snapshot.get("google_sheets")
    if sheets is None and isinstance(snapshot.get("rows"), list) and "headers" in snapshot:
        sheets = snapshot  # legacy shape: sheets snapshot merged at top level
    if isinstance(sheets, dict) and sheets.get("rows") is not None:
        out["google_sheets"] = {"rows": _normalized_rows(
            sheets.get("rows") or [], drop=("_row_id", "row_number"))}
    return out


def _state_checks(gold_snapshot: dict[str, Any], agent_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """One check per backend table the GOLD snapshot asserts (gold gating:
    a backend absent from the gold snapshot was never captured by that
    recipe's ground truth and cannot be scored). Within an asserted backend,
    agent-side extra tables/rows fail the check."""
    checks = []
    gold_state = _canonical_state_tables(gold_snapshot)
    agent_state = _canonical_state_tables(agent_snapshot)
    for backend in sorted(gold_state):
        gold_tables = gold_state[backend]
        agent_tables = agent_state.get(backend) or {}
        for table_id in sorted(set(gold_tables) | set(agent_tables)):
            gold_rows = gold_tables.get(table_id) or Counter()
            agent_rows = agent_tables.get(table_id) or Counter()
            checks.append(_check(
                f"final_state_{backend}_{table_id}_matches",
                gold_rows == agent_rows,
                {"backend": backend, "table_id": table_id,
                 "missing_rows": sorted((gold_rows - agent_rows).elements())[:5],
                 "extra_rows": sorted((agent_rows - gold_rows).elements())[:5]},
            ))
    return checks


def _terminal_outputs(calls: list[dict[str, Any]]) -> Counter:
    out: Counter = Counter()
    for call in calls or []:
        tool = str(call.get("tool") or "")
        if tool in TERMINAL_TOOLS:
            out[json.dumps({"tool": tool, "args": call.get("args") or {}},
                           sort_keys=True, default=str)] += 1
    return out


_NUMERIC_STRING_RE = re.compile(r"-?\d+(\.\d+)?")


def normalize_terminal_value(x: Any) -> Any:
    """Canonicalize a terminal-output value for semantic comparison: trim and
    collapse insignificant whitespace, parse JSON-formatted strings into
    structured values, normalize numeric representations (`10`, `10.0`, `"10"`
    are equivalent), and sort object keys."""
    if isinstance(x, str):
        s = x.strip()
        if s and s[0] in "{[" :
            # Only JSON-container strings re-parse; bare scalars keep the
            # numeric-string path below (json.loads("10") would also work but
            # would silently coerce "true"/"null" strings too — containers are
            # the shape agents actually serialize differently).
            try:
                return normalize_terminal_value(json.loads(s))
            except (ValueError, TypeError):
                pass
        if _NUMERIC_STRING_RE.fullmatch(s):
            f = float(s)
            return int(f) if f.is_integer() else round(f, 8)
        return re.sub(r"\s+", " ", s)
    if isinstance(x, bool):
        return x
    if isinstance(x, float):
        return int(x) if x.is_integer() else round(x, 8)
    if isinstance(x, dict):
        return {str(k): normalize_terminal_value(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, list):
        return [normalize_terminal_value(v) for v in x]
    return x


def _path_matches(
    path: tuple[str, ...], patterns: set[tuple[str, ...]] | None
) -> bool:
    return bool(
        patterns
        and any(
            len(pattern) == len(path)
            and all(expected == "*" or expected == actual for expected, actual in zip(pattern, path))
            for pattern in patterns
        )
    )


def _coerce_declared_booleans(
    value: Any,
    patterns: set[tuple[str, ...]] | None,
    path: tuple[str, ...] = (),
) -> Any:
    """Normalize string booleans only where the public interface says boolean.

    Bare ``"true"``/``"false"`` values remain strings everywhere else. This
    preserves strict semantics for text fields while allowing a Workato raw
    action spelling to compare with the typed JSON value promised to callers.
    """

    if isinstance(value, dict):
        return {
            key: _coerce_declared_booleans(item, patterns, path + (str(key),))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _coerce_declared_booleans(item, patterns, path + (str(index),))
            for index, item in enumerate(value)
        ]
    if _path_matches(path, patterns) and isinstance(value, str):
        lowered = value.strip().casefold()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return value


def _normalized_terminal_outputs(
    calls: list[dict[str, Any]],
    terminal_boolean_paths: dict[str, set[tuple[str, ...]]] | None = None,
) -> Counter:
    out: Counter = Counter()
    structural_return_tools = {
        "workato_recipe_function.return_result",
        "workato_genie.workflow_return_result",
    }
    # A WorkflowPlan ``return`` is control flow, not a second business
    # delivery, when it merely restates a value already emitted by an
    # output-bearing tool.  Keep the candidates deliberately narrow: tool
    # results plus the public reply/response body of terminal tools.  This
    # does not let a structural return substitute for a required terminal
    # tool, because there is no preceding emitted value in that case.
    prior_output_values: list[Any] = []
    for call in calls or []:
        tool = str(call.get("tool") or "")
        if tool in TERMINAL_TOOLS:
            args = _coerce_declared_booleans(
                call.get("args") or {},
                (terminal_boolean_paths or {}).get(tool),
            )
            if tool in structural_return_tools:
                returned = normalize_terminal_value(
                    args.get("result") if isinstance(args, dict) else None
                )
                # An empty structural return and natural plan completion have
                # the same caller-visible value. Returning the exact result of
                # a preceding terminal tool is likewise a control-flow
                # restatement, not a second output.
                if returned in (None, {}) or returned in prior_output_values:
                    continue
            normalized = normalize_terminal_value({"tool": tool, "args": args})
            if tool == "workato_service.call_service":
                # Deterministic raw replay records the callee's reply inside
                # the call arguments, while the model-visible tool correctly
                # exposes it only as the result.  Compare the invocation
                # surface here; exact fixtures independently bind each
                # flow_id/request pair to its reply.
                normalized.get("args", {}).pop("reply", None)
            if (
                tool == "workato_service.send_reply"
                and normalized.get("args", {}).get("reply") == {}
            ):
                normalized["args"].pop("reply")
            if tool == "workato_api_platform.return_response":
                args = normalized.get("args", {})
                headers = args.get("response_headers")
                if isinstance(headers, dict) and headers:
                    normalized_headers = {
                        str(key).strip().casefold(): str(value).strip().casefold()
                        for key, value in headers.items()
                    }
                    content_type = normalized_headers.get("content-type", "")
                    if (
                        set(normalized_headers) == {"content-type"}
                        and content_type.split(";", 1)[0].strip()
                        == "application/json"
                    ):
                        # Explicitly spelling the default JSON content type is
                        # a legal representation of the same public response.
                        args.pop("response_headers", None)
                if (
                    args.get("http_status_code") == 204
                    and args.get("response") in (None, {})
                ):
                    args.pop("response", None)
            out[json.dumps(normalized, sort_keys=True, default=str)] += 1
        if tool in TERMINAL_TOOLS | SIDE_EFFECT_TOOLS and tool not in structural_return_tools:
            result = normalize_terminal_value(call.get("result"))
            if result not in (None, {}):
                prior_output_values.append(result)
            call_args = normalize_terminal_value(call.get("args") or {})
            if isinstance(call_args, dict):
                if tool == "workato_service.send_reply":
                    if "reply" in call_args:
                        prior_output_values.append(call_args["reply"])
                    reply_envelope = dict(call_args)
                    if reply_envelope.get("reply") in (None, {}):
                        reply_envelope.pop("reply", None)
                    if reply_envelope:
                        prior_output_values.append(reply_envelope)
                elif (
                    tool == "workato_api_platform.return_response"
                    and "response" in call_args
                ):
                    prior_output_values.append(call_args["response"])
    return out


def _numbers_close(gold: Any, pred: Any) -> bool:
    return abs(gold - pred) <= max(1e-6, abs(gold) * 1e-6)


def _leaves(x: Any, prefix: tuple = ()) -> list[tuple[tuple, Any]]:
    if isinstance(x, dict):
        out: list[tuple[tuple, Any]] = []
        for key, value in x.items():
            out.extend(_leaves(value, prefix + (str(key),)))
        return out or [(prefix, {})]
    if isinstance(x, list):
        out = []
        for idx, value in enumerate(x):
            out.extend(_leaves(value, prefix + (idx,)))
        return out or [(prefix, [])]
    return [(prefix, x)]


def structural_similarity(gold: Any, pred: Any) -> float:
    """Leaf-level F1 between two normalized structures; numeric leaves match
    within a small relative tolerance."""
    gold_leaves = _leaves(gold)
    pred_leaves = dict(_leaves(pred))
    if not gold_leaves and not pred_leaves:
        return 1.0
    matched = 0
    for path, value in gold_leaves:
        if path not in pred_leaves:
            continue
        other = pred_leaves[path]
        if value == other:
            matched += 1
        elif (isinstance(value, (int, float)) and not isinstance(value, bool)
              and isinstance(other, (int, float)) and not isinstance(other, bool)
              and _numbers_close(value, other)):
            matched += 1
    total = max(len(gold_leaves), len(pred_leaves))
    return matched / total if total else 1.0


def _diff_reason(gold: Any, pred: Any) -> str:
    """Classify the first divergence between one gold and one agent output:
    missing-field / extra-field / numeric / structural."""
    gold_map = dict(_leaves(gold))
    pred_map = dict(_leaves(pred))
    if set(gold_map) - set(pred_map):
        return "missing-field"
    if set(pred_map) - set(gold_map):
        return "extra-field"
    for path, value in gold_map.items():
        other = pred_map[path]
        if value == other:
            continue
        if (isinstance(value, (int, float)) and not isinstance(value, bool)
                and isinstance(other, (int, float)) and not isinstance(other, bool)):
            if not _numbers_close(value, other):
                return "numeric"
            continue
        return "structural"
    return "structural"


def compare_terminal_outputs(
    gold_calls: list[dict[str, Any]],
    agent_calls: list[dict[str, Any]],
    *,
    terminal_boolean_paths: dict[str, set[tuple[str, ...]]] | None = None,
) -> dict[str, Any]:
    """Return exact terminal fidelity plus normalized semantic diagnostics."""
    gold_exact = _terminal_outputs(gold_calls)
    agent_exact = _terminal_outputs(agent_calls)
    gold_norm = _normalized_terminal_outputs(gold_calls, terminal_boolean_paths)
    agent_norm = _normalized_terminal_outputs(agent_calls, terminal_boolean_paths)
    exact_pass = gold_exact == agent_exact
    if gold_norm == agent_norm:
        return {"terminal_exact_pass": exact_pass,
                "terminal_normalized_pass": True,
                "terminal_similarity_score": 1.0,
                "terminal_diff_reason": None if exact_pass else "formatting-only",
                "mode": "exact" if exact_pass else "normalized_exact"}
    # Unmatched outputs: pair greedily by best structural similarity and grade.
    missing = [json.loads(s) for s in (gold_norm - agent_norm).elements()]
    extra = [json.loads(s) for s in (agent_norm - gold_norm).elements()]
    n_matched_exactly = sum((gold_norm & agent_norm).values())
    pair_scores: list[float] = []
    reason = None
    remaining = list(extra)
    for gold_item in missing:
        if not remaining:
            reason = reason or "missing-output"
            pair_scores.append(0.0)
            continue
        best_idx = max(range(len(remaining)),
                       key=lambda i: structural_similarity(gold_item, remaining[i]))
        best = remaining.pop(best_idx)
        pair_scores.append(structural_similarity(gold_item, best))
        reason = reason or _diff_reason(gold_item, best)
    if remaining:
        reason = reason or "extra-output"
        pair_scores.extend(0.0 for _ in remaining)
    total = n_matched_exactly + len(pair_scores)
    score = ((n_matched_exactly + sum(pair_scores)) / total) if total else 1.0
    # Pass requires EVERY output paired and EVERY leaf matched (numeric leaves
    # within float tolerance). Approximate similarity is a graded diagnostic
    # only — a 99%-right response is still a wrong final result
    # (benmark_rules.md: 'final result correctness').
    full_match = bool(pair_scores) and not remaining and all(
        s >= 1.0 - 1e-9 for s in pair_scores)
    return {"terminal_exact_pass": exact_pass,
            "terminal_normalized_pass": full_match,
            "terminal_similarity_score": round(score, 4),
            "terminal_diff_reason": reason if not full_match else "numeric-tolerance",
            "mode": "structural_similarity"}


def _f1(gold: Counter, agent: Counter) -> float:
    """Multiset F1: how much of the gold the agent realized (recall) balanced
    against how much of what it produced was correct (precision). Both empty
    -> perfect 1.0 (nothing was required, nothing was produced)."""
    gold_n, agent_n = sum(gold.values()), sum(agent.values())
    if gold_n == 0 and agent_n == 0:
        return 1.0
    overlap = sum((gold & agent).values())
    if overlap == 0:
        return 0.0
    precision = overlap / agent_n
    recall = overlap / gold_n
    return 2 * precision * recall / (precision + recall)


def _sequence_f1(gold: list[Any], agent: list[Any]) -> float:
    """Order-aware F1 using longest-common-subsequence overlap."""

    if not gold and not agent:
        return 1.0
    previous = [0] * (len(agent) + 1)
    for gold_item in gold:
        current = [0]
        for idx, agent_item in enumerate(agent, 1):
            if gold_item == agent_item:
                current.append(previous[idx - 1] + 1)
            else:
                current.append(max(previous[idx], current[-1]))
        previous = current
    overlap = previous[-1]
    if overlap == 0:
        return 0.0
    precision = overlap / len(agent)
    recall = overlap / len(gold)
    return 2 * precision * recall / (precision + recall)


def state_accuracy(
    gold_calls: list[dict[str, Any]],
    gold_snapshot: dict[str, Any],
    agent_calls: list[dict[str, Any]],
    agent_snapshot: dict[str, Any],
    *,
    terminal_boolean_paths: dict[str, set[tuple[str, ...]]] | None = None,
) -> float:
    """Graded outcome score in [0, 1]: mean of per-table row-multiset F1 plus
    the terminal-output multiset F1. Separates 'planned well, slipped on one
    value' (high score, outcome_pass False) from 'no plan at all' (near 0).
    A perfect run scores exactly 1.0 and always coincides with outcome_pass."""
    components: list[float] = []
    gold_state = _canonical_state_tables(gold_snapshot or {})
    agent_state = _canonical_state_tables(agent_snapshot or {})
    for backend in sorted(gold_state):
        gold_tables = gold_state[backend]
        agent_tables = agent_state.get(backend) or {}
        for table_id in sorted(set(gold_tables) | set(agent_tables)):
            components.append(_f1(gold_tables.get(table_id) or Counter(),
                                  agent_tables.get(table_id) or Counter()))
    gold_out = _normalized_terminal_outputs(gold_calls, terminal_boolean_paths)
    agent_out = _normalized_terminal_outputs(agent_calls, terminal_boolean_paths)
    if gold_out or agent_out:
        components.append(_f1(gold_out, agent_out))
    gold_effects = _side_effect_outputs(gold_calls)
    agent_effects = _side_effect_outputs(agent_calls)
    if gold_effects or agent_effects:
        components.append(_f1(gold_effects, agent_effects))
    gold_events = _transient_events(gold_calls)
    agent_events = _transient_events(agent_calls)
    if gold_events or agent_events:
        components.append(_sequence_f1(gold_events, agent_events))
    if not components:
        # no state backends and no terminal outputs anywhere: a pure no-op
        # task; the agent matches gold iff it also produced nothing.
        return 1.0
    return round(sum(components) / len(components), 4)


def evaluate_outcome(
    gold_calls: list[dict[str, Any]],
    gold_snapshot: dict[str, Any],
    agent_calls: list[dict[str, Any]],
    agent_snapshot: dict[str, Any],
    *,
    terminal_boolean_paths: dict[str, set[tuple[str, ...]]] | None = None,
) -> dict[str, Any]:
    state_checks = _state_checks(gold_snapshot or {}, agent_snapshot or {})
    terminal = compare_terminal_outputs(
        gold_calls,
        agent_calls,
        terminal_boolean_paths=terminal_boolean_paths,
    )
    gold_out = _normalized_terminal_outputs(gold_calls, terminal_boolean_paths)
    agent_out = _normalized_terminal_outputs(agent_calls, terminal_boolean_paths)
    primary_checks = list(state_checks)
    semantic_checks = list(state_checks)
    primary_checks.append(_check(
        "terminal_outputs_match",
        terminal["terminal_exact_pass"],
        {"mode": "canonical_exact",
         "terminal_exact_pass": terminal["terminal_exact_pass"],
         "terminal_normalized_pass": terminal["terminal_normalized_pass"],
         "terminal_similarity_score": terminal["terminal_similarity_score"],
         "terminal_diff_reason": terminal["terminal_diff_reason"],
         "missing_outputs": sorted((gold_out - agent_out).elements())[:3],
         "extra_outputs": sorted((agent_out - gold_out).elements())[:3]},
    ))
    semantic_checks.append(_check(
        "terminal_outputs_match_semantically",
        terminal["terminal_normalized_pass"],
        {"mode": terminal["mode"]},
    ))
    gold_effects_exact = _exact_side_effect_outputs(gold_calls)
    agent_effects_exact = _exact_side_effect_outputs(agent_calls)
    if gold_effects_exact or agent_effects_exact:
        primary_checks.append(_check(
            "side_effect_outputs_match",
            gold_effects_exact == agent_effects_exact,
            {
                "mode": "canonical_exact",
                "missing_side_effects": sorted(
                    (gold_effects_exact - agent_effects_exact).elements()
                )[:3],
                "extra_side_effects": sorted(
                    (agent_effects_exact - gold_effects_exact).elements()
                )[:3],
            },
        ))
    gold_effects = _side_effect_outputs(gold_calls)
    agent_effects = _side_effect_outputs(agent_calls)
    if gold_effects or agent_effects:
        semantic_checks.append(_check(
            "side_effect_outputs_match_semantically",
            gold_effects == agent_effects,
            {},
        ))
    gold_events = _exact_transient_events(gold_calls)
    agent_events = _exact_transient_events(agent_calls)
    transient_event_checked = bool(gold_events or agent_events)
    transient_event_pass = (
        gold_events == agent_events if transient_event_checked else None
    )
    if transient_event_checked:
        primary_checks.append(_check(
            "transient_events_match",
            bool(transient_event_pass),
            {
                "expected_events": gold_events,
                "actual_events": agent_events,
            },
        ))
    gold_events_semantic = _transient_events(gold_calls)
    agent_events_semantic = _transient_events(agent_calls)
    if gold_events_semantic or agent_events_semantic:
        semantic_checks.append(_check(
            "transient_events_match_semantically",
            gold_events_semantic == agent_events_semantic,
            {},
        ))
    return {"outcome_pass": all(c["ok"] for c in primary_checks),
            "outcome_semantic_pass": all(c["ok"] for c in semantic_checks),
            "checks": primary_checks,
            "semantic_checks": semantic_checks,
            "terminal_exact_pass": terminal["terminal_exact_pass"],
            "terminal_normalized_pass": terminal["terminal_normalized_pass"],
            "terminal_similarity_score": terminal["terminal_similarity_score"],
            "terminal_diff_reason": terminal["terminal_diff_reason"],
            "transient_event_checked": transient_event_checked,
            "transient_event_pass": transient_event_pass,
            "transient_event_expected_count": len(gold_events),
            "transient_event_actual_count": len(agent_events),
            "state_accuracy": state_accuracy(
                gold_calls,
                gold_snapshot,
                agent_calls,
                agent_snapshot,
                terminal_boolean_paths=terminal_boolean_paths,
            )}


# Raw authoring-layer recipe returns. Canonical outcome comparison replaces
# them (and symbolic plan-level ``return`` stops) with the uniform synthetic
# call below so Global/Local plans and ReAct traces expose the same semantic
# terminal output.
STRUCTURAL_RETURN_TOOLS = frozenset({
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
})


def synthetic_return_call(value: Any) -> dict[str, Any]:
    """Represent plan-level return uniformly for semantic outcome scoring."""

    from copy import deepcopy

    return {
        "tool": "workato_recipe_function.return_result",
        "args": {"result": deepcopy(value)},
        "result": {"ok": True, "result": deepcopy(value)},
    }


def public_output_boolean_argument_paths(
    public_output_schema: dict[str, Any] | None,
) -> set[tuple[str, ...]]:
    """Return API response argument paths declared as public booleans.

    Workato raw recipes can retain ``"true"``/``"false"`` spellings even
    when the declared API response contract applies boolean conversion.  The
    public contract is the authority for semantic argument/outcome typing;
    raw spellings remain available through the separate raw-fidelity checks.
    """

    paths: set[tuple[str, ...]] = set()

    def visit(field: Any, path: tuple[str, ...]) -> None:
        if not isinstance(field, dict):
            return
        field_type = str(field.get("type") or "").casefold()
        if field_type == "boolean" or "boolean_conversion" in {
            str(field.get("parse_output") or ""),
            str(field.get("render_input") or ""),
        }:
            paths.add(path)
        properties = field.get("properties") or []
        if not isinstance(properties, list):
            return
        child_prefix = path + (("*",) if field_type == "array" else ())
        for child in properties:
            if not isinstance(child, dict) or not child.get("name"):
                continue
            visit(child, child_prefix + (str(child["name"]),))

    for response in (public_output_schema or {}).get("declared_responses") or []:
        if not isinstance(response, dict):
            continue
        for field in response.get("body_schema") or []:
            if not isinstance(field, dict) or not field.get("name"):
                continue
            visit(field, ("response", str(field["name"])))
    return paths
