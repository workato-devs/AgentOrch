# Real connector benchmark

This is the live-connector form of the Remedy benchmark. It contains all 803
recipe runners and seeders, connector capability registry, model-evaluation
harness, and tests. Common recipes, the raw executor, other runtime code, agent
strategies, and metrics are loaded from `../shared`; this directory keeps the
live-only connector code and entry points.

## Setup

1. Copy `.env.example` to `.env` and populate only the connectors you plan to
   exercise.
2. Ensure connector-specific clients are available: `sf` for Salesforce,
   `gcloud` for Google APIs, and `snowflake-connector-python` for Snowflake.
3. Run commands with `PYTHONPATH=src`.

```bash
PYTHONPATH=src python3 -m benchmark.seed_recipe 100039154 --variant 0
PYTHONPATH=src python3 -m benchmark.run_recipe 100039154 --variant 0
PYTHONPATH=src python3 -m pytest src/tests
```

Live writes are constrained by the benchmark seed, verification, and cleanup
rules. See `CONNECTOR_CAPABILITIES.md` before running credentialed recipes.

The Agent SDK tests require `claude-agent-sdk`. Without that optional
dependency, the connector-independent suite is:

```bash
PYTHONPATH=src python3 -m pytest \
  src/tests/test_in_time_zone_semantics.py \
  src/tests/test_live_state_outcome.py \
  src/tests/test_replan_mode.py \
  src/tests/test_salesforce_order_by.py
```
