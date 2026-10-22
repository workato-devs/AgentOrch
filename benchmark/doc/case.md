# Case study: runtime observation resolves a nested reference

This example compares Global and ReAct for SOP `102467097`, variant `00`,
from the archived Claude Opus 5 evaluation on the simulated backend.

## Task and results


The task asks an automation agent to verify that a caller is authorized and,
if so, return up to 200 deprecated package versions in chronological order.
Variant `00` contains an enabled authorization record and one qualifying
package-version record. The package reference is represented at runtime as a
nested object:

```json
{
  "display_name": "Bench display_name",
  "record_id": "Bench record_id"
}
```

This representation creates the decisive difference. Global View must emit a
single symbolic workflow before seeing connector results. Its plan maps the
entire nested object to `package_id` and attempts to read `display_name` from
the record's top level. ReAct observes the nested object first and then reads
its `record_id` and `display_name` members correctly.

| Setting | Trace | Side effect | Orchestration | Terminal | Final |
| --- | ---: | ---: | ---: | ---: | ---: |
| Global View | 0.8 | 1.0 | 0.9 | 0.0 | 0.0 |
| ReAct | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

For Global View, the five trace components are
$(1,1,1,0,1)$ for tool selection, tool order, successful execution, required
arguments, and control path. Therefore,
$\mathrm{TraceAcc}=0.2(1+1+1+0+1)=0.8$ and
$\mathrm{OrchAcc}=0.5(0.8)+0.5(1)=0.9$. The task is read-only, so the expected
state is preserved and Side-Effect Accuracy is one. The malformed terminal
response makes Terminal Accuracy and Final Accuracy zero. ReAct receives one
on all five trace components and produces the correct terminal response.

## Run the same SOP with your model

Download the benchmark data and configure a Chat Completions endpoint as
shown in the [evaluation guide](../README.md#run-an-evaluation):

```bash
python scripts/download_data.py --only benchmark
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name nested-reference --model compat:my-served-model \
  --ids 102467097 --variants 0 --modes plan_execute,react
```

Read the generated plans, tool observations, and verdicts in
`benchmark/outputs/full_eval/nested-reference/`. The table above describes
the archived model run; a different model or configuration can produce
different scores.

## Source artifacts

The model-visible specification is in
`benchmark/input/recipes/102467097/PUBLIC_PACKAGE.json`. Reference traces and
terminal contracts are in
`benchmark/groundtruth/recipes/102467097/variant_00.json`. The evaluator uses
the reference data for scoring; it is not part of the model prompt.
