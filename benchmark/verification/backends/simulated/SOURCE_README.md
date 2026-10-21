# Simulated connector benchmark

This version has the same 803 recipes, raw executor, action names, tool schemas,
seed format, and verifiers as `../real`. External calls are replaced at one
backend seam:

- Common recipes, runtime code, agent strategies, and metrics are loaded from
  `../shared`.
- `src/benchmark/simulated_tools.py` registers the unchanged tool surface.
- `src/benchmark/simulated_connectors.py` provides local Slack, Jira,
  Salesforce, Google Sheets, Google Drive, and Snowflake clients.
- Workato tables and lookup tables retain the benchmark's existing local
  implementations.

No connector credentials, CLIs, or network access are required. Each seed/run
rehydrates deterministic connector state from its seed file.

```bash
PYTHONPATH=src python3 -m benchmark.seed_recipe 100039154 --variant 0
PYTHONPATH=src python3 -m benchmark.run_recipe 100039154 --variant 0
PYTHONPATH=src python3 -m pytest src/tests
```

The simulator intentionally supports the API and query shapes exercised by the
benchmark corpus; unsupported Salesforce or Snowflake query constructs fail
explicitly instead of guessing.

The Agent SDK tests require `claude-agent-sdk`. The four connector-independent
test modules run without that optional dependency.
