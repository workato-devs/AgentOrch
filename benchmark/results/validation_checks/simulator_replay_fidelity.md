# Reference workflow replay: real-backend reference vs simulator

run `outputs/full_eval/gold-replay-20260915/scripted-gold/<mode>/` (canonical evaluator, `--scripted-selftest`, simulated backend, all variants)


## mode = plan_execute

```
Metric                           Agreement / Accuracy
-------------------------------------------------------
Replay success rate              100.00%
Tool selection                    61.68%
Tool order                        61.68%
Tool execution                    60.99%
Required arguments                90.34%
Control path                      61.68%
Execution Trace Accuracy          67.27%
Side-Effect Accuracy              81.55%
Terminal Output Accuracy          71.43%
Final Accuracy                    56.83%
Orchestration Accuracy            74.41%
```
- SOPs attempted: 650
- runtime variants attempted: 3220
- runtime variants excluded / not replayable: 0
- replay statuses: {'ok': 3220}
- mismatched variants (any failed primary component/metric): 1652 (51.30%)
- components not applicable (vacuous pass) counts: {'tool_argument_required': 448}
- mismatch cause categories:
    - private runtime step in reference plan (public projection asymmetry): 766 (46.4% of mismatches)
    - return-value envelope wrapping in reference plan: 303 (18.3% of mismatches)
    - simulator fixture guard refused call: workato_smart_list.create_list: 147 (8.9% of mismatches)
    - plan executor resolution error: 91 (5.5% of mismatches)
    - action budget exhausted: 78 (4.7% of mismatches)
    - simulator fixture guard refused call: workato_service.call_service: 47 (2.8% of mismatches)
    - required-arg check fails while canonical exact passes (scorer diagnostic): 44 (2.7% of mismatches)
    - argument value mismatch (read result / dynamic value / normalization): 32 (1.9% of mismatches)
    - private runtime step + other trace difference: 17 (1.0% of mismatches)
    - simulator fixture guard refused call: salesforce.search_records: 17 (1.0% of mismatches)
    - trigger filter / gating not encoded in plan (engine skipped execution): 16 (1.0% of mismatches)
    - simulator fixture guard refused call: workato_smart_list.query_list: 15 (0.9% of mismatches)
    - simulator refused/failed a gold call (react: call absent from success log): 14 (0.8% of mismatches)
    - extra/missing tool identity: 13 (0.8% of mismatches)
    - state mismatch with identical call sequence (seed/gold-snapshot divergence): 10 (0.6% of mismatches)
    - unexpected tool failure in simulator: 9 (0.5% of mismatches)
    - call-count / loop-count mismatch: 8 (0.5% of mismatches)
    - simulator fixture guard refused call: snowflake.search_rows_sql: 8 (0.5% of mismatches)
    - simulator fixture guard refused call: unsupported: 5 (0.3% of mismatches)
    - simulator fixture guard refused call: workato_smart_list.create_list_from_csv: 5 (0.3% of mismatches)
    - simulator fixture guard refused call: google_sheets.update_row_v4_new: 3 (0.2% of mismatches)
    - simulator fixture guard refused call: slack_bot.generate_menu_options: 2 (0.1% of mismatches)
    - simulator fixture guard refused call: refusing: 1 (0.1% of mismatches)
    - terminal-output mismatch (missing-field): 1 (0.1% of mismatches)
- identical-sequence state mismatches: 10 variants; no side-effect pass in any of 3 strong ReAct lanes for 4 of them: ['124154692__v00', '124154692__v01', '124154692__v02', '124154692__v03']
- exact-match rate by whether the reference plan contains runtime-helper (workato_runtime/clock) call nodes: with helpers: 177/1356 = 13.1%; without helpers: 1391/1864 = 74.6%

## mode = react

```
Metric                           Agreement / Accuracy
-------------------------------------------------------
Replay success rate              100.00%
Tool selection                    97.20%
Tool order                        97.20%
Tool execution                    97.20%
Required arguments                99.97%
Control path                      97.20%
Execution Trace Accuracy          97.76%
Side-Effect Accuracy              99.32%
Terminal Output Accuracy          76.80%
Final Accuracy                    76.52%
Orchestration Accuracy            98.54%
```
- SOPs attempted: 650
- runtime variants attempted: 3220
- runtime variants excluded / not replayable: 0
- replay statuses: {'ok': 3220}
- mismatched variants (any failed primary component/metric): 757 (23.51%)
- components not applicable (vacuous pass) counts: {'tool_argument_required': 90}
- mismatch cause categories:
    - terminal-output mismatch (missing-output): 653 (86.3% of mismatches)
    - simulator refused/failed a gold call (react: call absent from success log): 83 (11.0% of mismatches)
    - state mismatch with identical call sequence (seed/gold-snapshot divergence): 13 (1.7% of mismatches)
    - call-count / loop-count mismatch: 4 (0.5% of mismatches)
    - extra/missing tool identity: 3 (0.4% of mismatches)
    - argument value mismatch (read result / dynamic value / normalization): 1 (0.1% of mismatches)
- identical-sequence state mismatches: 13 variants; no side-effect pass in any of 3 strong ReAct lanes for 9 of them: ['103988401__v00', '103988401__v01', '103988401__v02', '103988401__v03', '103988401__v04', '124154692__v00', '124154692__v01', '124154692__v02', '124154692__v03']
- exact-match rate by whether the reference plan contains runtime-helper (workato_runtime/clock) call nodes: with helpers: 954/1356 = 70.4%; without helpers: 1509/1864 = 81.0%
