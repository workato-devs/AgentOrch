# Experimental protocol

AgentOrch evaluates 650 SOPs and 3,220 runtime variants with a shared
64-tool interface, simulated connector backend, and execution-based scorer.
The primary comparison is Global versus Step-by-Step.

Global generates one complete workflow per SOP before seeing concrete runtime
inputs and reuses it across variants. Step-by-Step acts sequentially using
runtime input and intermediate observations. Their information and decision
schedules differ; the comparison measures the gap between these deployed
settings.

Section 4 examines model scale, model generation, and reasoning, then three
routes to improving Global: incremental construction (Local), complete-workflow
revision using execution feedback (Replan), and SFT followed by GRPO.
Input-Conditioned Global tests access to concrete runtime inputs alone.

All methods are scored from executed trajectories, resulting state, and
terminal output. Non-scoreable failures receive zero accuracy and remain in
the denominator. The primary Orchestration Accuracy averages Execution Trace
Accuracy and Side-Effect Accuracy. Final Accuracy requires correct side
effects and terminal output.

The [evaluation guide](../README.md) provides commands and generation
settings. [Model configurations](../evaluation/global_react_models.json)
record revisions and reasoning settings. Training configurations and the five
reported base/SFT/RL comparisons are in
[training.csv](../../training/results/training.csv).
