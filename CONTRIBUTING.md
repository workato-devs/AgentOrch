# Contributing to AgentOrch

Contributions to model integration, evaluation tools, training workflows, and
documentation are welcome. Include a reproducible example and explain the
behavior changed by your pull request.

## Development setup

Use Python 3.12. The CPU checks need no GPU, model credentials, or downloaded
benchmark data:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest scripts/tests -q
python scripts/check_repository.py --smoke
```

For HTTP model evaluation, install
[`benchmark/requirements-api.txt`](benchmark/requirements-api.txt). For local
GPU inference, use [`benchmark/requirements.txt`](benchmark/requirements.txt).
Training dependencies belong in separate environments as described in the
[training guide](training/README.md#set-up).

## Pull requests

Describe the affected commands, recipe IDs, or model integrations and include
the validation you ran. Add regression coverage for changes to executable
behavior. Keep credentials, checkpoints, and generated run outputs out of Git.

Benchmark comparisons depend on consistent prompts, dataset membership,
simulator behavior, and scoring. Explain changes to those components and their
impact on comparability. Preserve the original source results when correcting
a generated table.

Regenerate the combined leaderboard after updating its source tables:

```bash
python scripts/build_combined_leaderboard.py
```

Use `--check` to verify that the combined tables are current without writing
them. GitHub Actions runs repository checks, sample execution, and regression
tests on pushes and pull requests.

## Reporting issues

Include the command, environment, backend, model ID, recipe ID, and a minimal
error excerpt. Remove credentials and private data. Follow
[`SECURITY.md`](SECURITY.md) for vulnerabilities or suspected data exposure.
