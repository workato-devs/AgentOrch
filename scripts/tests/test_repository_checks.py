"""Regression checks for validation that must preserve existing artifacts."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_table_check_reports_stale_tables_without_rewriting(tmp_path, monkeypatch):
    builder = load_script("build_combined_leaderboard")
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUT_CSV", tmp_path / "combined.csv")
    monkeypatch.setattr(builder, "OUT_MD", tmp_path / "combined.md")
    monkeypatch.setattr("sys.argv", ["builder"])
    assert builder.main() == 0
    monkeypatch.setattr("sys.argv", ["builder", "--check"])
    assert builder.main() == 0
    builder.OUT_CSV.write_bytes(b"existing research results\n")
    before = {p: p.read_bytes() for p in (builder.OUT_CSV, builder.OUT_MD)}
    assert builder.main() == 1
    assert all(p.read_bytes() == content for p, content in before.items())
    builder.OUT_MD.unlink()
    assert builder.main() == 1
    assert not builder.OUT_MD.exists()


def test_smoke_preserves_existing_outputs_and_caches(tmp_path, monkeypatch):
    checker = load_script("check_repository")
    monkeypatch.setattr(checker, "BENCH", tmp_path)
    existing = [tmp_path / "outputs/connector-runtime/run.json",
                tmp_path / "outputs/existing-smoke/run.json",
                tmp_path / "__pycache__/keep.pyc"]
    for path in existing:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"keep")

    def run(command, **kwargs):
        if "verification.connector_runner" in command:
            output = Path(command[command.index("--output-dir") + 1])
            assert output.is_relative_to(tmp_path / "outputs")
            assert output.parent.name.startswith("benchmark-check-")
        return SimpleNamespace(returncode=0, stdout='{"n": 1, "verifier_ok": true}', stderr="")

    monkeypatch.setattr(checker.subprocess, "run", run)
    checker.check_smoke()
    assert not checker.FAILS
    assert all(path.read_bytes() == b"keep" for path in existing)
    assert sorted(p.name for p in (tmp_path / "outputs").iterdir()) == [
        "connector-runtime", "existing-smoke"]
