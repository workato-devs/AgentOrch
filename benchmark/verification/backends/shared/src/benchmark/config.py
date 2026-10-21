from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ._paths import BENCHMARK_ROOT, WORKSPACE_ROOT

ROOT = BENCHMARK_ROOT.parent
ENV_FILE = BENCHMARK_ROOT / ".env"
# BENCHMARK_OUTPUT_DIR redirects ALL generated state (seeds, outputs, mock
# state files) — used by the eval harness so agent runs never touch the
# committed ground-truth output/ tree.
OUTPUT_DIR = Path(os.environ["BENCHMARK_OUTPUT_DIR"]) if os.environ.get("BENCHMARK_OUTPUT_DIR") else BENCHMARK_ROOT / "output"
DATASET_DIR = (
    Path(os.environ["BENCHMARK_DATASET_DIR"])
    if os.environ.get("BENCHMARK_DATASET_DIR")
    else WORKSPACE_ROOT / "dataset"
)
CODE_FLOW_DIR = DATASET_DIR / "input_recipes"
TASK_SPEC_DIR = DATASET_DIR / "task_specs"
WORKATO_DB_TABLE_DIR = OUTPUT_DIR / "_state" / "workato_db_tables"
LOOKUP_TABLE_DIR = OUTPUT_DIR / "_state" / "lookup_tables"


def variant_label(variant: int | str | None) -> str | None:
    if variant is None or variant == "":
        return None
    if isinstance(variant, int):
        return f"variant_{variant:02d}"
    text = str(variant)
    if text.startswith("variant_"):
        return text
    if text.isdigit():
        return f"variant_{int(text):02d}"
    return text


def recipe_output_dir(recipe_id: str, variant: int | str | None = None) -> Path:
    base = OUTPUT_DIR / str(recipe_id)
    label = variant_label(variant)
    return base / label if label else base


def seed_file(recipe_id: str, variant: int | str | None = None) -> Path:
    return recipe_output_dir(recipe_id, variant) / "seed.json"


def output_file(recipe_id: str, variant: int | str | None = None) -> Path:
    return recipe_output_dir(recipe_id, variant) / "output.json"


def verify_file(recipe_id: str, variant: int | str | None = None) -> Path:
    return recipe_output_dir(recipe_id, variant) / "verify.json"


def workato_db_table_file(recipe_id: str, variant: int | str | None = None) -> Path:
    base = WORKATO_DB_TABLE_DIR / str(recipe_id)
    label = variant_label(variant)
    return (base / label if label else base) / "tables.json"


def lookup_table_file(recipe_id: str, variant: int | str | None = None) -> Path:
    base = LOOKUP_TABLE_DIR / str(recipe_id)
    label = variant_label(variant)
    return (base / label if label else base) / "tables.json"


@dataclass(frozen=True)
class Env:
    slack_bot_token: str
    slack_channel_override: str
    sheets_spreadsheet_id: str
    sheets_tab: str
    snowflake_account: str
    snowflake_user: str
    snowflake_role: str
    snowflake_pat: str
    snowflake_private_key_path: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_schema: str


def load_env() -> Env:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")

    for key in (
        "SLACK_BOT_TOKEN",
        "SLACK_CHANNEL_OVERRIDE",
        "SHEETS_SPREADSHEET_ID",
        "SHEETS_TAB",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_ROLE",
        "SNOWFLAKE_PAT",
        "SNOWFLAKE_PRIVATE_KEY_PATH",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ):
        if os.environ.get(key):
            values[key] = os.environ[key]

    return Env(
        slack_bot_token=values.get("SLACK_BOT_TOKEN", ""),
        slack_channel_override=values.get("SLACK_CHANNEL_OVERRIDE", ""),
        sheets_spreadsheet_id=values.get("SHEETS_SPREADSHEET_ID", ""),
        sheets_tab=values.get("SHEETS_TAB", ""),
        snowflake_account=values.get("SNOWFLAKE_ACCOUNT", ""),
        snowflake_user=values.get("SNOWFLAKE_USER", ""),
        snowflake_role=values.get("SNOWFLAKE_ROLE", ""),
        snowflake_pat=values.get("SNOWFLAKE_PAT", ""),
        snowflake_private_key_path=values.get("SNOWFLAKE_PRIVATE_KEY_PATH", ""),
        snowflake_warehouse=values.get("SNOWFLAKE_WAREHOUSE", ""),
        snowflake_database=values.get("SNOWFLAKE_DATABASE", ""),
        snowflake_schema=values.get("SNOWFLAKE_SCHEMA", ""),
    )
