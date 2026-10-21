# Smoke adapter example

This is a dependency-light, two-recipe integration example. It lets a model
author validate the Global View and ReAct request/response protocols before
using the full evaluator.

```bash
PYTHONPATH=benchmark python -m examples.smoke_adapter.eval \
  --mode global \
  --adapter examples.smoke_adapter.example_adapter:build \
  --model-id smoke-test --run-name smoke \
  --recipe-id 64112882 --limit 1
```

Implement the adapter interface in `model_corpus.py`; `example_adapter.py` is
the smallest working template. This harness covers only recipes `64112882`
and `69270259`. Its score is a protocol smoke test and must not be compared
with the 650-recipe benchmark leaderboard. Comparable results must use
`evaluation.full_eval` with all 3,220 variants.

