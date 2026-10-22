# Verification runtimes

This directory contains evaluator-private state plus two execution layers:

- `smoke/` is a dependency-light protocol runtime for two recipes. It keeps
  unit tests and model-adapter smoke checks fast.
- `backends/` is the full connector runtime, vendored from the repository's
  shared, simulated, and real benchmark source roots.

The full overlays intentionally share the Python package name `benchmark`.
Use `backend.activate()` or `connector_runner`; do not add both backend source
roots to `PYTHONPATH`.

```bash
PYTHONPATH=benchmark \
  python -m verification.connector_runner \
  --backend simulated --recipe-id 64112882 --variant 0
```

The command performs the recipe's canonical seed phase, runs its raw workflow
against the selected connectors, and executes its verifier. Mutable output is
written under `benchmark/outputs/connector-runtime/` unless an explicit
`--output-dir` is supplied.

## Real connectors

Copy `backends/real/.env.example` to `backends/real/.env` and fill only the
connectors required for a run. The real backend may create, update, or delete
external benchmark-owned resources as declared in
`backends/real/CONNECTOR_CAPABILITIES.md`. Its existing ownership, seeding,
verification, and cleanup guards remain active.

## Runtime layout

The shared recipe executor, simulated connectors, and optional live
connectors are included under `backends/`. Their source layout is recorded
in `backends/manifest.json`. Dataset and reference fixtures are downloaded
with `python scripts/download_data.py --only benchmark`.
