from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Any

from .pipeline_common import PipelineError, read_json, stable_json_hash


REQUIRED_HUMAN_ARTIFACT_CHECKS = (
    "A_is_faithful_to_raw_recipe",
    "C_is_evidence_grounded",
    "P_is_branch_complete",
    "Q_is_execution_time_task",
    "Q_is_semantically_complete",
    "Q_has_no_unsupported_claim",
    "Q_has_no_implementation_or_variant_leakage",
    "all_selected_variant_outputs_reviewed",
    "critic_findings_are_correct",
)


def review_artifacts_to_read(
    recipe_id: str,
    artifact_root: Path,
    input_root: Path,
) -> dict[str, str]:
    return {
        "raw_recipe": str(input_root / recipe_id / "raw_recipe.md"),
        "source_package": str(
            artifact_root / "00_source_packages" / f"{recipe_id}.json"
        ),
        "A": str(artifact_root / "01_canonical_ir" / f"{recipe_id}.json"),
        "C": str(artifact_root / "02_annotations" / f"{recipe_id}.json"),
        "P": str(artifact_root / "03_task_plans" / f"{recipe_id}.json"),
        "Q_and_D": str(
            artifact_root / "08_final" / "tasks" / f"{recipe_id}.json"
        ),
        "critic": str(
            artifact_root / "06_semantic_validation" / f"{recipe_id}.json"
        ),
        "variant_validation": str(
            artifact_root / "07_variant_validation" / f"{recipe_id}.json"
        ),
    }


def _evidence_path(value: Any, artifact_root: Path) -> Path:
    path = Path(str(value or ""))
    if not str(path):
        raise PipelineError("human-review evidence contains an empty path")
    if not path.is_absolute():
        path = artifact_root.parents[1] / path
    return path


def selected_variant_evidence(
    recipe_id: str,
    artifact_root: Path,
    dynamic: dict[str, Any],
    selected_variant_ids: list[str],
) -> list[dict[str, Any]]:
    reports = {
        str(item.get("variant_id") or ""): item
        for item in dynamic.get("variants") or []
        if isinstance(item, dict)
    }
    q_only_reports = {
        str(item.get("variant_id") or ""): item
        for item in (dynamic.get("q_only_solvability") or {}).get(
            "variants"
        )
        or []
        if isinstance(item, dict)
    }
    evidence: list[dict[str, Any]] = []
    for variant_id in selected_variant_ids:
        report = reports.get(variant_id)
        if not report:
            raise PipelineError(
                f"{recipe_id} Stage 7 lacks selected variant {variant_id}"
            )
        q_only_report = q_only_reports.get(variant_id)
        if not q_only_report:
            raise PipelineError(
                f"{recipe_id} Stage 7 lacks Q-only variant {variant_id}"
            )
        input_path = _evidence_path(report.get("input_path"), artifact_root)
        output_path = _evidence_path(report.get("output_path"), artifact_root)
        q_only_path = _evidence_path(
            q_only_report.get("result_path"),
            artifact_root,
        )
        missing = [
            str(path)
            for path in (input_path, output_path, q_only_path)
            if not path.is_file()
        ]
        if missing:
            raise PipelineError(
                f"{recipe_id} missing selected-variant review evidence: "
                + ", ".join(missing)
            )
        evidence.append(
            {
                "variant_id": variant_id,
                "input_path": str(input_path),
                "input_hash": stable_json_hash(read_json(input_path)),
                "gold_output_path": str(output_path),
                "gold_output_hash": stable_json_hash(read_json(output_path)),
                "q_only_result_path": str(q_only_path),
                "q_only_result_hash": stable_json_hash(
                    read_json(q_only_path)
                ),
            }
        )
    return evidence


def review_artifact_bindings(
    recipe_id: str,
    artifact_root: Path,
    raw_recipe_path: Path,
    source_recipe_hash: str,
    task_hash: str,
    normalized_workflow_hash: str,
    A_hash: str,
    C_hash: str,
    P_hash: str,
    D_hash: str,
    semantic_validation: dict[str, Any],
    dynamic: dict[str, Any],
    selected_variant_ids: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not raw_recipe_path.is_file():
        raise PipelineError(
            f"{recipe_id} raw recipe is missing: {raw_recipe_path}"
        )
    current_source_hash = hashlib.sha256(raw_recipe_path.read_bytes()).hexdigest()
    if current_source_hash != source_recipe_hash:
        raise PipelineError(
            f"{recipe_id} Stage 0 source hash differs from the raw recipe"
        )
    variant_evidence = selected_variant_evidence(
        recipe_id,
        artifact_root,
        dynamic,
        selected_variant_ids,
    )
    bindings = {
        "source_recipe_hash": current_source_hash,
        "task_description_hash": task_hash,
        "normalized_workflow_hash": normalized_workflow_hash,
        "A_hash": A_hash,
        "C_hash": C_hash,
        "P_hash": P_hash,
        "D_hash": D_hash,
        "semantic_validation_hash": semantic_validation.get(
            "semantic_validation_hash"
        ),
        "semantic_validation_artifact_hash": stable_json_hash(
            semantic_validation
        ),
        "variant_validation_hash": stable_json_hash(dynamic),
        "selected_variant_ids_hash": stable_json_hash(selected_variant_ids),
        "selected_variant_evidence_hash": stable_json_hash(variant_evidence),
    }
    missing = [key for key, value in bindings.items() if not value]
    if missing:
        raise PipelineError(
            f"{recipe_id} review bindings are incomplete: {', '.join(missing)}"
        )
    return bindings, variant_evidence


def human_review_evidence(
    review: dict[str, Any] | None,
    expected_recipe_id: str | None,
) -> dict[str, Any]:
    schema_valid = (
        (review or {}).get("schema_version") == "human-review-template"
    )
    artifact_checks = (review or {}).get("artifact_checks") or {}
    non_boolean_checks = [
        key
        for key in REQUIRED_HUMAN_ARTIFACT_CHECKS
        if not isinstance(artifact_checks.get(key), bool)
    ]
    failed_checks = [
        key
        for key in REQUIRED_HUMAN_ARTIFACT_CHECKS
        if artifact_checks.get(key) is False
    ]
    critic_assessment = (review or {}).get("critic_assessment") or {}
    critic_flags_explicit = all(
        isinstance(critic_assessment.get(key), bool)
        for key in ("false_positive", "false_negative")
    )
    critic_clear = (
        critic_assessment.get("false_positive") is False
        and critic_assessment.get("false_negative") is False
    )
    failure_categories = (review or {}).get("failure_categories")
    categories_explicit = isinstance(failure_categories, list)
    no_failures = categories_explicit and not failure_categories
    reviewed_by = (review or {}).get("reviewed_by")
    reviewer_present = isinstance(reviewed_by, str) and bool(
        reviewed_by.strip()
    )
    reviewed_at = (review or {}).get("reviewed_at")
    timestamp_valid = False
    if isinstance(reviewed_at, str) and reviewed_at.strip():
        try:
            parsed = dt.datetime.fromisoformat(
                reviewed_at.strip().replace("Z", "+00:00")
            )
            timestamp_valid = parsed.tzinfo is not None
        except ValueError:
            timestamp_valid = False
    recipe_matches = (
        expected_recipe_id is None
        or str((review or {}).get("recipe_id") or "") == expected_recipe_id
    )
    decision_complete = bool(
        review
        and schema_valid
        and not non_boolean_checks
        and critic_flags_explicit
        and categories_explicit
        and reviewer_present
        and timestamp_valid
        and recipe_matches
    )
    rejection_signal = bool(
        failed_checks
        or critic_assessment.get("false_positive") is True
        or critic_assessment.get("false_negative") is True
        or (categories_explicit and bool(failure_categories))
    )
    acceptance_complete = bool(
        decision_complete
        and not failed_checks
        and critic_clear
        and no_failures
    )
    return {
        "decision_complete": decision_complete,
        "acceptance_complete": acceptance_complete,
        "rejection_signal": rejection_signal,
        "non_boolean_artifact_checks": non_boolean_checks,
        "failed_artifact_checks": failed_checks,
        "critic_flags_explicit": critic_flags_explicit,
        "critic_assessment_clear": critic_clear,
        "failure_categories_explicit": categories_explicit,
        "failure_categories_empty": no_failures,
        "reviewer_present": reviewer_present,
        "reviewed_at_valid": timestamp_valid,
        "recipe_id_matches": recipe_matches,
        "schema_valid": schema_valid,
    }
