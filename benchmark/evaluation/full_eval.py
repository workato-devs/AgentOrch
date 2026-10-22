"""Run the canonical full-corpus evaluator on a vendored connector backend."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


PUBLIC_ROOT = Path(__file__).resolve().parents[1]
VERIFICATION_ROOT = PUBLIC_ROOT / "verification"
SUPPORT_ROOT = VERIFICATION_ROOT / "evaluation_support"


def _load_env_file() -> None:
    """Load provider credentials from a dotenv file without overriding the shell.

    Order: $AGENTORCH_ENV_FILE, then <release root>/.env (the directory that
    contains benchmark/), then benchmark/.env. Values already present in the
    environment win, so Slurm launchers that source the file themselves are
    unaffected. Nothing is printed.
    """
    candidates = []
    if os.environ.get("AGENTORCH_ENV_FILE"):
        candidates.append(Path(os.environ["AGENTORCH_ENV_FILE"]))
    candidates += [PUBLIC_ROOT.parent / ".env", PUBLIC_ROOT / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value
        return


def _recipe_ids() -> list[str]:
    manifest = json.loads(
        (PUBLIC_ROOT / "input/manifest.json").read_text(encoding="utf-8")
    )
    return [str(row["recipe_id"]) for row in manifest.get("recipes") or []]


def _validate_data(forwarded: list[str]) -> None:
    """Fail before loading a model if selected evaluation fixtures are absent."""
    selection = argparse.ArgumentParser(add_help=False)
    selection.add_argument("--ids", nargs="*")
    selection.add_argument("--limit", type=int, default=0)
    selection.add_argument("--variants", choices=("0", "nonzero", "all"), default="all")
    options, _ = selection.parse_known_args(forwarded)
    if options.limit < 0:
        raise ValueError("--limit must be zero (all recipes) or positive")
    if not options.ids:
        raise ValueError("--ids must name at least one recipe")
    if len(set(options.ids)) != len(options.ids):
        raise ValueError("--ids contains duplicate recipes")
    manifest = json.loads((PUBLIC_ROOT / "input/manifest.json").read_text(encoding="utf-8"))
    recipes = {str(row["recipe_id"]): row for row in manifest["recipes"]}
    unknown = [recipe for recipe in options.ids if recipe not in recipes]
    if unknown:
        raise ValueError(f"unknown recipe ID(s): {', '.join(unknown)}")
    selected = options.ids[:options.limit] if options.limit else options.ids
    for recipe in selected:
        paths = [PUBLIC_ROOT / "input/recipes" / recipe / "PUBLIC_PACKAGE.json"]
        paths.extend(SUPPORT_ROOT / group / f"{recipe}.json"
                     for group in ("canonical_ir", "workflow_groundtruth", "critic"))
        variants = [str(v).zfill(2) for v in recipes[recipe]["variant_ids"]]
        if options.variants == "all":
            directory = VERIFICATION_ROOT / "dataset/input_recipes" / recipe
            present = {p.name for p in directory.glob("variant_*") if p.is_dir()}
            if present != {f"variant_{v}" for v in variants}:
                raise ValueError(
                    f"incomplete runtime variants for recipe {recipe}. "
                    "Run: python scripts/download_data.py --only benchmark. "
                    "On a fresh clone, use --ids 64112882 for the included sample."
                )
        elif options.variants == "0":
            variants = ["00"]
        else:
            variants = [v for v in variants if v != "00"]
        if not variants:
            raise ValueError(f"no variants selected for recipe {recipe}")
        for variant in variants:
            paths.extend((
                VERIFICATION_ROOT / "dataset/input_recipes" / recipe / f"variant_{variant}" / "input.json",
                VERIFICATION_ROOT / "groundtruth/reference_outputs" / recipe / f"variant_{variant}" / "output.json",
            ))
        missing = next((path for path in paths if not path.is_file()), None)
        if missing is not None:
            raise ValueError(
                f"missing evaluation fixture: {missing.relative_to(PUBLIC_ROOT)}. "
                "Run: python scripts/download_data.py --only benchmark. "
                "On a fresh clone, use --ids 64112882 for the included sample."
            )


def _configure(run_name: str, backend: str, state_namespace: str) -> Path:
    from verification.backend import activate

    eval_root = (PUBLIC_ROOT / "outputs/full_eval" / run_name).resolve()
    state_root = eval_root / "_state_root" / state_namespace
    os.environ["BENCHMARK_EVAL_ROOT"] = str(eval_root)
    os.environ["BENCHMARK_GROUND_TRUTH_DIR"] = str(
        VERIFICATION_ROOT / "groundtruth/reference_outputs"
    )
    os.environ["BENCHMARK_TASK_DESCRIPTION_PACKAGE_DIR"] = str(
        PUBLIC_ROOT / "input/recipes"
    )
    os.environ["BENCHMARK_TASK_DESCRIPTION_WORKFLOW_DIR"] = str(
        SUPPORT_ROOT / "canonical_ir"
    )
    os.environ["BENCHMARK_TASK_DESCRIPTION_GROUNDTRUTH_DIR"] = str(
        SUPPORT_ROOT / "workflow_groundtruth"
    )
    os.environ["BENCHMARK_TASK_DESCRIPTION_CRITIC_DIR"] = str(
        SUPPORT_ROOT / "critic"
    )
    os.environ["BENCHMARK_SCORING_CONTRACT_REGISTRY"] = str(
        SUPPORT_ROOT / "scoring_contract_registry.json"
    )
    activate(backend, output_dir=state_root)
    return eval_root


def main(argv: list[str] | None = None) -> int:
    _load_env_file()
    # Live-stall diagnostics: periodically dump every thread's stack to a
    # file (srun --overlap is disabled on this cluster, so in-process dumps
    # are the only way to see where a silent harness is stuck).
    dump_every = int(os.environ.get("HF_STACK_DUMP_SECONDS", "0") or "0")
    if dump_every > 0:
        import faulthandler
        dump_path = (
            f"{os.environ.get('HF_STACK_DUMP_DIR', '/tmp')}/"
            f"stackdump-{os.environ.get('SLURM_JOB_ID', os.getpid())}.txt"
        )
        _dump_file = open(dump_path, "w")
        faulthandler.dump_traceback_later(
            dump_every, repeat=True, file=_dump_file
        )
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Full Global View (plan_execute) and ReAct evaluation using the "
            "vendored connector runtime and canonical scorer."
        ),
        epilog="""Model and evaluation options (forwarded to the canonical evaluator):
  --model MODEL       hf:<repo-or-path>, compat:<served-model>, or provider model ID
  --modes MODES       plan_execute,react,incremental_workflow,replan,global_input
  --ids ID [ID ...]   select recipes (fresh-clone sample: 64112882)
  --limit N          limit recipe count; 0 means all (default)
  --variants CHOICE  all (default), 0, or nonzero
  --resume           append only tasks not already recorded
  --runs N           repeated evaluations per variant (default: 1)
  --max-replans N    maximum accepted suffix replans (default: 2)
  --replan-protocol  v1 (default) or v2
  --scripted-selftest replay reference trajectories without calling a model

Self-hosted HTTP endpoint: set LOCAL_LLM_BASE_URL (including /v1) and use
--model compat:<served-model>. See benchmark/README.md for complete commands.""",
    )
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--backend", default="simulated", choices=("simulated", "real"))
    parser.add_argument(
        "--state-namespace",
        default=f"process-{os.getpid()}",
        help="isolated mutable connector-state namespace for parallel jobs",
    )
    args, forwarded = parser.parse_known_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_name):
        parser.error("--run-name may contain only letters, digits, dot, underscore, and hyphen")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.state_namespace):
        parser.error("--state-namespace has invalid characters")
    if not any(item == "--model" or item.startswith("--model=") for item in forwarded):
        parser.error("pass the model to the canonical evaluator with --model")
    if not any(item == "--modes" or item.startswith("--modes=") for item in forwarded):
        forwarded.extend(("--modes", "plan_execute,react"))
    if not any(item == "--variants" or item.startswith("--variants=") for item in forwarded):
        forwarded.extend(("--variants", "all"))
    if not any(item == "--task-source" or item.startswith("--task-source=") for item in forwarded):
        forwarded.extend(("--task-source", "task_description"))
    if not any(item == "--tool-surface" or item.startswith("--tool-surface=") for item in forwarded):
        forwarded.extend(("--tool-surface", "broad"))
    if not any(item in {"--ids", "--pilot"} or item.startswith("--ids=") for item in forwarded):
        forwarded.append("--ids")
        forwarded.extend(_recipe_ids())

    if "--pilot" not in forwarded:
        try:
            _validate_data(forwarded)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))

    _configure(args.run_name, args.backend, args.state_namespace)
    from task.run_eval import main as canonical_main

    return canonical_main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
