"""Exercise the public evaluator from a clone containing only the shipped sample.

The loopback model server uses test-only reference replies. No provider keys,
GPU, model download, or real business service is used by these checks.
"""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "benchmark/verification/backends/shared/src"
SIMULATED = ROOT / "benchmark/verification/backends/simulated/src"


@pytest.fixture
def clients(monkeypatch):
    monkeypatch.syspath_prepend(str(SHARED))
    monkeypatch.syspath_prepend(str(SIMULATED))
    spec = importlib.util.spec_from_file_location("community_clients", SHARED / "task/llm_client.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_setting", lambda key: None)
    return module


@pytest.mark.parametrize("name", ["gpt-custom", "claude-custom", "org/model", "/models/local"])
def test_explicit_compatible_route_keeps_served_model_name(clients, monkeypatch, name):
    monkeypatch.setattr(clients, "_setting", {"LOCAL_LLM_BASE_URL": "http://localhost:8000/v1"}.get)
    client = clients.build_client("compat:" + name)
    assert isinstance(client, clients.OpenAICompatClient)
    assert client._body("system", [])["model"] == name
    assert client._url == "http://localhost:8000/v1/chat/completions"


@pytest.mark.parametrize("model,reasoning,temperature", [
    ("gpt-4o", None, 0.0), ("gpt-4.1", None, 0.0),
    ("gpt-5.6-sol", "none", None), ("o3", None, None),
])
def test_direct_openai_request_parameters(clients, model, reasoning, temperature):
    client = clients.OpenAIDirectClient(model, api_key="test-key")
    body = client._body("system", [])
    assert body.get("reasoning_effort") == reasoning
    assert body.get("temperature") == temperature
    assert ("reasoning_effort" in body) == (reasoning is not None)
    assert body["max_completion_tokens"] == 4096


def test_vllm_defaults_reserve_space_for_generation(clients, monkeypatch):
    settings = {"HF_HOME": "/nonexistent/community-test-cache"}
    monkeypatch.setattr(clients, "_setting", settings.get)
    calls = []

    class Engine:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def get_tokenizer(self):
            return object()

    config = SimpleNamespace(model_type="test", max_position_embeddings=131072)
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoConfig=SimpleNamespace(from_pretrained=lambda *a, **kw: config)))
    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(LLM=Engine, SamplingParams=object))
    monkeypatch.setitem(sys.modules, "task.vllm_json_stop", SimpleNamespace(
        CompleteJSONLogitsProcessor=object))
    client = clients.VLLMClient("test/model")
    assert calls[0]["max_model_len"] == 131072
    assert client.max_input_tokens == 122880
    assert client.max_new_tokens == 4096
    assert client.react_max_new_tokens == 8192
    settings["HF_MODEL_CONTEXT_TOKENS"] = "122880"
    with pytest.raises(clients.LLMError, match="cannot exceed"):
        clients.VLLMClient("test/model")
    assert len(calls) == 1


@pytest.mark.parametrize("max_tokens,stopped", [(8192, True), (4096, False)])
def test_default_vllm_soft_cap_applies_only_to_react(monkeypatch, max_tokens, stopped):
    for key in ("HF_REACT_MAX_NEW_TOKENS", "HF_REACT_SOFT_MAX_NEW_TOKENS", "HF_THINKING_PREFIX"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=object))
    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(SamplingParams=object))
    monkeypatch.setitem(sys.modules, "vllm.v1.sample.logits_processor", SimpleNamespace(AdapterLogitsProcessor=object))
    spec = importlib.util.spec_from_file_location("community_stop", SHARED / "task/vllm_json_stop.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    processor = object.__new__(module.CompleteJSONLogitsProcessor)
    processor.tokenizer = SimpleNamespace(decode=lambda *a, **kw: "unfinished output")
    processor.eos_token_id = 2
    processor._decode_lock = threading.Lock()

    class Logits(dict):
        forced_stop = False

        def fill_(self, value):
            self.forced_stop = True

    logits = Logits()
    process = processor.new_req_logits_processor(SimpleNamespace(max_tokens=max_tokens))
    process([0] * 1024, logits)
    assert logits.forced_stop == stopped
    if stopped:
        assert logits[2] == 0.0


@pytest.fixture(scope="module")
def community_repo(tmp_path_factory):
    repo = tmp_path_factory.mktemp("community") / "AgentOrch"
    subprocess.run(["git", "clone", "--shared", "--quiet", str(ROOT), str(repo)], check=True)
    additions = subprocess.check_output(
        ["git", "ls-files", "--modified", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    for raw in set(additions.split(b"\0")) - {b""}:
        rel = os.fsdecode(raw)
        if (ROOT / rel).is_file():
            dest = repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
        elif (repo / rel).is_file():
            (repo / rel).unlink()
    return repo


def evaluate(repo, *args, extra_env=None):
    # Do not inherit credentials, endpoint selection, or private data paths.
    env = {k: os.environ[k] for k in ("PATH", "HOME", "SYSTEMROOT") if k in os.environ}
    env.update(PYTHONPATH="benchmark", PYTHONDONTWRITEBYTECODE="1", API_MAX_ATTEMPTS="1")
    env.update(extra_env or {})
    return subprocess.run([sys.executable, "-m", "evaluation.full_eval", *args],
                          cwd=repo, env=env, capture_output=True, text=True, timeout=120)


def test_help_describes_custom_models_and_run_options(community_repo):
    result = evaluate(community_repo, "--help")
    assert result.returncode == 0, result.stderr
    assert all(flag in result.stdout for flag in ("compat:", "--ids", "--resume", "--variants"))


@pytest.mark.parametrize("selection,message", [
    ([], "download_data.py --only benchmark"),
    (["--ids", "not-a-recipe"], "unknown recipe"),
    (["--ids", "64112882", "64112882"], "duplicate recipes"),
    (["--ids", "64112882", "--limit", "-1"], "--limit must"),
])
def test_bad_data_selection_fails_before_model_connection(community_repo, selection, message):
    result = evaluate(community_repo, "--run-name", "bad-input", "--model", "compat:gpt-custom", *selection)
    assert result.returncode == 2
    assert message in result.stderr
    assert "missing LOCAL_LLM_BASE_URL" not in result.stderr


def test_all_protocols_score_every_shipped_variant(community_repo):
    result = evaluate(
        community_repo, "--run-name", "canonical-control", "--model", "scripted-selftest",
        "--ids=64112882", "--variants", "all", "--scripted-selftest",
        "--modes", "plan_execute,react,incremental_workflow,replan,global_input")
    assert result.returncode == 0, result.stderr
    root = community_repo / "benchmark/outputs/full_eval/canonical-control/scripted-selftest"
    for mode in ("plan_execute", "react", "incremental_workflow", "replan", "global_input"):
        board = json.loads((root / mode / "leaderboard.json").read_text())
        assert board["n"] == 5
        assert board["orchestration_accuracy"] == 1.0
        assert board["error_rate"] == 0.0
        assert board["meta"]["scripted_selftest"] is True


def test_custom_http_model_scores_and_resumes_without_repeating_requests(community_repo):
    helper = """
import json
from evaluation.full_eval import _configure
_configure('http-fixture', 'simulated', 'fixture')
from task.run_eval import _scripted_initial_plan_artifact
print(json.dumps(_scripted_initial_plan_artifact('64112882')['plan']))
"""
    env = {**os.environ, "PYTHONPATH": "benchmark", "PYTHONDONTWRITEBYTECODE": "1"}
    plan = json.loads(subprocess.check_output([sys.executable, "-c", helper],
                                             cwd=community_repo, env=env, text=True))
    gold = json.loads((community_repo / "benchmark/verification/groundtruth/reference_outputs/64112882/variant_00/output.json").read_text())
    replies = [json.dumps({"plan": plan})] + [json.dumps({"tool": c["tool"], "args": c["args"]})
                                  for c in gold["tool_calls"]]
    replies.append(json.dumps({"tool": "finish", "args": {}}))
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, self.headers.get("Authorization"), request))
            payload = json.dumps({"choices": [{"message": {"role": "assistant", "content": replies.pop(0)}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    endpoint_env = {"LOCAL_LLM_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
                    "LOCAL_LLM_API_KEY": "test-key"}
    args = ("--run-name", "http-model", "--model", "compat:gpt-custom", "--ids", "64112882",
            "--variants", "0", "--modes", "plan_execute,react")
    try:
        result = evaluate(community_repo, *args, extra_env=endpoint_env)
        assert result.returncode == 0, result.stderr
        root = community_repo / "benchmark/outputs/full_eval/http-model/compat:gpt-custom"
        for mode in ("plan_execute", "react"):
            board = json.loads((root / mode / "leaderboard.json").read_text())
            assert board["n"] == 1
            assert board["orchestration_accuracy"] == 1.0, result.stdout
            assert board["error_rate"] == 0.0
            assert board["meta"]["scripted_selftest"] is False
        assert len(requests) >= 3
        assert all(path == "/v1/chat/completions" and auth == "Bearer test-key"
                   and body["model"] == "gpt-custom" for path, auth, body in requests)
        before = len(requests)
        rows = {mode: (root / mode / "results.jsonl").read_bytes() for mode in ("plan_execute", "react")}
        resumed = evaluate(community_repo, *args, "--resume", extra_env=endpoint_env)
        assert resumed.returncode == 0, resumed.stderr
        assert len(requests) == before
        assert all((root / mode / "results.jsonl").read_bytes() == content for mode, content in rows.items())
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize("module,mode", [
    ("experiments.replan_iter", "replan_iter"),
    ("experiments.replan_iter_heldout", "replan_iter_heldout"),
])
def test_replan_runs_from_dotenv_and_scores_three_revision_rounds(community_repo, module, mode):
    helper = """
import json
from evaluation.full_eval import _configure
_configure('revision-fixture', 'simulated', 'fixture')
from task.run_eval import _scripted_initial_plan_artifact
print(json.dumps(_scripted_initial_plan_artifact('64112882')['plan']))
"""
    env = {k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}
    env.update(PYTHONPATH="benchmark", PYTHONDONTWRITEBYTECODE="1", API_MAX_ATTEMPTS="1")
    plan = json.loads(subprocess.check_output([sys.executable, "-c", helper],
                                             cwd=community_repo, env=env, text=True))
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = json.dumps({"choices": [{"message": {"content": json.dumps({"plan": plan})}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    dotenv = community_repo / ".env"
    dotenv.write_text(f"LOCAL_LLM_BASE_URL=http://127.0.0.1:{server.server_port}/v1\n"
                      "LOCAL_LLM_API_KEY=test-key\n")
    run = f"revision-{mode}"
    command = [sys.executable, "-m", module, "--run-name", run,
               "--model", "compat:gpt-custom", "--ids", "64112882"]
    try:
        result = subprocess.run(command, cwd=community_repo, env=env,
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        curve = json.loads((community_repo / "benchmark/outputs/full_eval" / run /
                            "compat:gpt-custom" / mode / "curve.json").read_text())
        assert curve["rounds"] == 3
        assert len(curve["curve"]) == 4
        for row in curve["curve"]:
            board = row if mode == "replan_iter" else row["all"]
            assert board["n"] == 5
            assert board["orchestration_accuracy"] == 1.0
        assert len(requests) == 4
        assert all(request["model"] == "gpt-custom" for request in requests)
    finally:
        dotenv.unlink(missing_ok=True)
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
