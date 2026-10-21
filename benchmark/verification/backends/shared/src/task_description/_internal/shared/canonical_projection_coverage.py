"""Deterministic coverage inventory for recipe-to-tool argument projections.

This report is intentionally static.  It answers whether a raw recipe action
has a recipe-independent adapter to the argument shape emitted by
``RawWorkatoRuntime``; it does not infer support from an evaluator pass rate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .canonical_tool_arguments import (
    canonical_tool_arguments,
    projection_support,
)
from .tool_catalog import ToolCatalog


def _hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_projection_coverage(
    project_root: Path,
    stage1_dir: Path,
) -> dict[str, Any]:
    catalog = ToolCatalog.from_benchmark(project_root)
    by_pair: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "node_count": 0,
            "recipe_ids": set(),
            "projection_errors": [],
            "node_refs": [],
        }
    )
    source_hashes: list[dict[str, str]] = []

    for path in sorted(stage1_dir.glob("*.json"), key=lambda item: item.name):
        payload = json.loads(path.read_text(encoding="utf-8"))
        recipe_id = str(payload.get("recipe_id") or path.stem)
        source_hashes.append(
            {
                "recipe_id": recipe_id,
                "canonical_ir_hash": str(payload.get("canonical_ir_hash") or ""),
            }
        )
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict) or node.get("kind") == "trigger":
                continue
            raw_tool = str(node.get("tool_name") or "")
            if not raw_tool:
                continue
            canonical_tool = catalog.canonical_tool(raw_tool, node)
            declared = projection_support(
                canonical_tool,
                raw_tool,
                node.get("arguments") or {},
            )
            row = by_pair[(raw_tool, canonical_tool, declared)]
            row["node_count"] += 1
            row["recipe_ids"].add(recipe_id)
            row["node_refs"].append(
                {"recipe_id": recipe_id, "node_id": str(node.get("node_id") or "")}
            )
            try:
                canonical_tool_arguments(
                    canonical_tool,
                    node.get("arguments") or {},
                    redact_dynamic_values=False,
                    source_tool=raw_tool,
                    input_schema=node.get("input_schema"),
                    source_node=node,
                )
            except Exception as exc:  # report must fail closed, not disappear
                row["projection_errors"].append(
                    {
                        "recipe_id": recipe_id,
                        "node_id": str(node.get("node_id") or ""),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    rows: list[dict[str, Any]] = []
    for (raw_tool, canonical_tool, declared), data in sorted(by_pair.items()):
        errors = sorted(
            data["projection_errors"],
            key=lambda item: (item["recipe_id"], item["node_id"]),
        )
        status = "projection_error" if errors else declared
        if status == "exact":
            blocker_class = None
        elif raw_tool in {
            "slack.post_message_to_channel",
            "slack_bot.post_bot_message",
            "slack_bot.post_bot_reply_v2",
            "workato_service.call_service",
        }:
            blocker_class = "raw_executor_private_argument_injection"
        elif status == "unsupported":
            blocker_class = "invalid_benchmark_contract_missing_raw_executor_adapter"
        else:
            blocker_class = "symbolic_projection_gap"
        rows.append(
            {
                "source_tool": raw_tool,
                "canonical_tool": canonical_tool,
                "support": status,
                "static_projection_can_match_runtime": status == "exact",
                "blocker_class": blocker_class,
                "node_count": data["node_count"],
                "recipe_count": len(data["recipe_ids"]),
                "recipe_ids": sorted(data["recipe_ids"]),
                "blocking_nodes": (
                    sorted(
                        data["node_refs"],
                        key=lambda item: (item["recipe_id"], item["node_id"]),
                    )
                    if status != "exact"
                    else []
                ),
                "projection_errors": errors,
            }
        )

    node_counts: dict[str, int] = defaultdict(int)
    pair_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        node_counts[row["support"]] += row["node_count"]
        pair_counts[row["support"]] += 1
    total_nodes = sum(node_counts.values())
    payload: dict[str, Any] = {
        "schema_version": "canonical-argument-projection-coverage-v1",
        "authority": (
            "raw recipe is the sole static ground truth; support=exact means "
            "the recipe alone determines RawWorkatoRuntime call arguments"
        ),
        "stage1_source_hash": _hash(source_hashes),
        "summary": {
            "source_tool_pairs": len(
                {(row["source_tool"], row["canonical_tool"]) for row in rows}
            ),
            "projection_classes": len(rows),
            "nodes": total_nodes,
            "pair_counts_by_support": dict(sorted(pair_counts.items())),
            "node_counts_by_support": dict(sorted(node_counts.items())),
            "exact_node_fraction": (
                node_counts.get("exact", 0) / total_nodes if total_nodes else 0.0
            ),
            "all_exact": bool(rows)
            and all(row["support"] == "exact" for row in rows),
        },
        "tools": rows,
    }
    payload["report_hash"] = _hash(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--stage1-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_projection_coverage(
        args.project_root.resolve(), args.stage1_dir.resolve()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
