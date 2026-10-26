# Simulated connector backend

This is the vendored `simulated` overlay for the current 650-recipe public
benchmark. Shared recipes and execution code live under `../shared/src`.
No connector credentials or network access are required.

Do not put this source root directly on `PYTHONPATH` alongside the other
backend. Run it through:

```bash
PYTHONPATH=benchmark python -m verification.connector_runner \
  --backend simulated --recipe-id 64112882 --variant 0
```

`CONNECTOR_CAPABILITIES.md` documents supported tools and external side effects.
