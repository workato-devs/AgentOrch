# Simulator fidelity: reference-action replay

Recorded reference tool calls are replayed one action at a time in the
simulated backend and scored with the canonical evaluator (Appendix D).

| Metric | Agreement (%) |
| --- | ---: |
| Tool selection | 97.20 |
| Tool order | 97.20 |
| Tool execution | 97.20 |
| Required arguments | 99.97 |
| Control path | 97.20 |
| Execution Trace Accuracy | 97.76 |
| Side-Effect Accuracy | 99.32 |
| Orchestration Accuracy | 98.54 |
