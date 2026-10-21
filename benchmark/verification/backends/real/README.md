# Real connector backend

This is the vendored `real` overlay for the current 650-recipe public
benchmark. Shared recipes and execution code live under `../shared/src`.
Copy `.env.example` to `.env` and configure only the live connectors being exercised. Never commit credentials.

Do not put this source root directly on `PYTHONPATH` alongside the other
backend. Run it through:

```bash
PYTHONPATH=benchmark python -m verification.connector_runner \
  --backend real --recipe-id 64112882 --variant 0
```

`CONNECTOR_CAPABILITIES.md` documents supported tools and external side
effects. `SOURCE_README.md` preserves the source tree's original documentation
for provenance.
