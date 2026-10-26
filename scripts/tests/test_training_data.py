"""Check GRPO prompt selection and rejection of incomplete datasets."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def builder():
    path = ROOT / "training/src/rl/trl_gemma/make_trl_dataset.py"
    spec = importlib.util.spec_from_file_location("trl_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def messages(path, count):
    rows = []
    for i in range(count):
        rows.append(json.dumps({"messages": [
            {"role": "system", "content": "Generate a complete workflow."},
            {"role": "user", "content": "task " + "x" * i},
            {"role": "assistant", "content": json.dumps({"plan": [], "id": i})},
        ]}))
    path.write_text("\n".join(rows) + "\n")


def test_grpo_selects_exactly_one_thousand_shortest_prompts(tmp_path, monkeypatch):
    module = builder()
    train, validation = tmp_path / "train.jsonl", tmp_path / "eval.jsonl"
    messages(train, 1002)
    messages(validation, 25)
    output = tmp_path / "prepared"
    monkeypatch.setattr("sys.argv", ["builder", "--data", str(train),
                                     "--eval-data", str(validation), "--out", str(output)])
    module.main()
    rows = [json.loads(x) for x in (output / "train.jsonl").read_text().splitlines()]
    assert len(rows) == 1000
    assert {json.loads(row["golden"])["id"] for row in rows} == set(range(1000))
    assert all([m["role"] for m in row["prompt"]] == ["system", "user"] for row in rows)
    assert len((output / "eval.jsonl").read_text().splitlines()) == 24


def test_grpo_rejects_insufficient_prompts_before_writing(tmp_path, monkeypatch):
    module = builder()
    train, validation = tmp_path / "train.jsonl", tmp_path / "eval.jsonl"
    messages(train, 999)
    messages(validation, 25)
    output = tmp_path / "prepared"
    monkeypatch.setattr("sys.argv", ["builder", "--data", str(train),
                                     "--eval-data", str(validation), "--out", str(output)])
    with pytest.raises(ValueError, match="requested 1000 prompts, but only 999"):
        module.main()
    assert not output.exists()
