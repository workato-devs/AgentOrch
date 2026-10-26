# AgentOrch datasets

AgentOrch contains 650 enterprise SOPs and 3,220 runtime variants. A separate
training set contains 3,000 source recipes, disjoint from the benchmark by
recipe ID. Both sets come from the same enterprise automation environment.

## Benchmark construction

Sanitized executable Workato recipes define reference workflows. Task
specifications describe their business requirements, public schemas, workspace
resources, templates, and 64 available tool interfaces. Runtime variants
exercise different control-flow paths, loop cardinalities, and error conditions.
Real-connector reference executions provide traces, intermediate results,
and terminal outputs; model-generated workflows are evaluated in simulation.

Four authors reviewed task descriptions through five review/regeneration
rounds. Runtime variants underwent reference execution and human inspection
of outputs, state changes, control flow, and terminal responses, as described
in Appendix G.

## Training data

Each recipe provides one task-specification/complete-workflow pair. Targets
preserve branches, loops, exception handling, tool calls, data dependencies,
and termination behavior. Each example exposes 64 tool cards. Targets use
1,033 tool operations across 305 namespaces; the tool-card pool contains
1,036 cards across 306 namespaces.

Training targets undergo structural and interface validation. Their inclusion
does not require execution of the serialized target. The recipe-disjoint
split evaluates new workflows within a shared tool ecosystem.

## Information boundaries

Public task specifications exclude reference workflows, reference traces,
hidden connector state, fault settings, and concrete runtime inputs. Step-by-Step
receives runtime input and execution observations. Input-Conditioned Global
receives runtime input before planning. Replan receives feedback from its own
executions, without reference behavior or evaluation scores.

## Download and use

[Benchmark data](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark)
and [training data](https://huggingface.co/datasets/JesseLiu/agentorch-training)
are available on Hugging Face:

```bash
python -m pip install huggingface_hub
python scripts/download_data.py --only benchmark
python scripts/download_data.py --only training --prepared
```

See the [evaluation guide](benchmark/README.md) and
[training guide](training/README.md) for execution commands.
Included third-party attribution is in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
