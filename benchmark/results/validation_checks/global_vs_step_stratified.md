# GLOBAL (plan_execute) vs STEP-BY-STEP (react), stratified by SOP structure

Models pooled: 45 (every model has all 3,220 variants in both modes; failed rows scored 0 and counted in the error rate, as in the main benchmark).  
Gap = STEP-BY-STEP - GLOBAL orchestration accuracy; CI95 = clustered bootstrap over SOPs (1000 resamples, seed 0).  '#models gap>0' = models whose own gap is positive.


## Breakdown by all

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 650 | 3220 | 0.138 | 0.464 | +0.326 | [+0.312, +0.342] | 45/45 | 0.707 | 0.005 | 0.060 | 0.261 | 0.155 | 0.566 | 0.121 | 0.362 |

## Breakdown by size_num_tool_calls

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| long (6+ calls) | 165 | 1036 | 0.083 | 0.466 | +0.383 | [+0.351, +0.413] | 45/45 | 0.820 | 0.007 | 0.031 | 0.233 | 0.102 | 0.601 | 0.063 | 0.331 |
| medium (3-5 calls) | 251 | 1149 | 0.142 | 0.473 | +0.331 | [+0.309, +0.351] | 45/45 | 0.693 | 0.005 | 0.065 | 0.265 | 0.168 | 0.593 | 0.116 | 0.353 |
| short (1-2 calls) | 234 | 1035 | 0.188 | 0.452 | +0.263 | [+0.245, +0.284] | 45/45 | 0.609 | 0.005 | 0.084 | 0.285 | 0.192 | 0.501 | 0.185 | 0.402 |

## Breakdown by num_apps

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <=1 | 235 | 1192 | 0.190 | 0.515 | +0.325 | [+0.302, +0.347] | 45/45 | 0.652 | 0.004 | 0.091 | 0.304 | 0.213 | 0.621 | 0.168 | 0.409 |
| 2 | 360 | 1676 | 0.117 | 0.442 | +0.325 | [+0.304, +0.346] | 45/45 | 0.721 | 0.006 | 0.046 | 0.238 | 0.132 | 0.543 | 0.103 | 0.342 |
| 3+ | 55 | 352 | 0.059 | 0.394 | +0.334 | [+0.285, +0.385] | 45/45 | 0.824 | 0.007 | 0.025 | 0.225 | 0.066 | 0.491 | 0.053 | 0.297 |

## Breakdown by num_services

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <=1 | 275 | 1462 | 0.190 | 0.570 | +0.380 | [+0.358, +0.400] | 45/45 | 0.669 | 0.004 | 0.085 | 0.309 | 0.230 | 0.734 | 0.150 | 0.406 |
| 2 | 328 | 1508 | 0.101 | 0.393 | +0.292 | [+0.271, +0.312] | 45/45 | 0.727 | 0.007 | 0.041 | 0.223 | 0.100 | 0.457 | 0.102 | 0.329 |
| 3+ | 47 | 250 | 0.056 | 0.271 | +0.215 | [+0.182, +0.245] | 45/45 | 0.810 | 0.006 | 0.029 | 0.208 | 0.045 | 0.240 | 0.067 | 0.302 |

## Breakdown by conditional

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| has_conditional | 347 | 1981 | 0.136 | 0.500 | +0.364 | [+0.344, +0.384] | 45/45 | 0.733 | 0.005 | 0.067 | 0.290 | 0.165 | 0.638 | 0.106 | 0.361 |
| no_conditional | 303 | 1239 | 0.142 | 0.407 | +0.265 | [+0.246, +0.284] | 45/45 | 0.665 | 0.006 | 0.049 | 0.214 | 0.138 | 0.451 | 0.145 | 0.362 |

## Breakdown by loop

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| has_loop | 139 | 807 | 0.085 | 0.443 | +0.357 | [+0.326, +0.391] | 45/45 | 0.789 | 0.008 | 0.044 | 0.282 | 0.105 | 0.592 | 0.065 | 0.293 |
| no_loop | 511 | 2413 | 0.156 | 0.471 | +0.315 | [+0.299, +0.332] | 45/45 | 0.679 | 0.004 | 0.065 | 0.254 | 0.171 | 0.557 | 0.140 | 0.385 |

## Breakdown by try_catch

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| has_try_catch | 237 | 1291 | 0.140 | 0.512 | +0.372 | [+0.347, +0.396] | 45/45 | 0.748 | 0.005 | 0.055 | 0.240 | 0.175 | 0.675 | 0.104 | 0.349 |
| no_try_catch | 413 | 1929 | 0.137 | 0.432 | +0.295 | [+0.276, +0.312] | 45/45 | 0.679 | 0.006 | 0.064 | 0.275 | 0.141 | 0.493 | 0.133 | 0.370 |

## Breakdown by structure_category

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| branch_only | 132 | 688 | 0.149 | 0.486 | +0.336 | [+0.302, +0.368] | 45/45 | 0.694 | 0.005 | 0.089 | 0.323 | 0.164 | 0.573 | 0.134 | 0.398 |
| error_handling_only | 78 | 295 | 0.166 | 0.488 | +0.322 | [+0.284, +0.361] | 45/45 | 0.696 | 0.005 | 0.063 | 0.179 | 0.186 | 0.616 | 0.147 | 0.360 |
| linear | 186 | 781 | 0.144 | 0.397 | +0.253 | [+0.229, +0.279] | 45/45 | 0.642 | 0.005 | 0.043 | 0.209 | 0.130 | 0.409 | 0.158 | 0.385 |
| loop_only | 36 | 148 | 0.089 | 0.309 | +0.220 | [+0.185, +0.260] | 45/45 | 0.704 | 0.007 | 0.054 | 0.296 | 0.090 | 0.357 | 0.088 | 0.262 |
| multiple_control_flow_types | 218 | 1308 | 0.128 | 0.504 | +0.377 | [+0.352, +0.403] | 45/45 | 0.755 | 0.006 | 0.055 | 0.273 | 0.164 | 0.668 | 0.091 | 0.340 |

## Breakdown by nesting_depth

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 235 | 1030 | 0.150 | 0.478 | +0.328 | [+0.305, +0.352] | 45/45 | 0.693 | 0.004 | 0.074 | 0.269 | 0.172 | 0.585 | 0.129 | 0.372 |
| 3+ | 229 | 1409 | 0.126 | 0.490 | +0.365 | [+0.342, +0.387] | 45/45 | 0.753 | 0.006 | 0.059 | 0.283 | 0.156 | 0.639 | 0.096 | 0.341 |
| 1 (flat) | 186 | 781 | 0.144 | 0.397 | +0.253 | [+0.228, +0.279] | 45/45 | 0.642 | 0.005 | 0.043 | 0.209 | 0.130 | 0.409 | 0.158 | 0.385 |

## Breakdown by fault_injection

| bucket | #SOP | #variants | GLOBAL orch | STEP orch | gap | gap CI95 | #models gap>0 | GLOBAL err | STEP err | GLOBAL final | STEP final | GLOBAL side-effect | STEP side-effect | GLOBAL exec-trace | STEP exec-trace |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fault_variant | 224 | 264 | 0.164 | 0.528 | +0.365 | [+0.338, +0.394] | 45/45 | 0.742 | 0.006 | 0.089 | 0.264 | 0.199 | 0.688 | 0.128 | 0.369 |
| normal_variant | 650 | 2956 | 0.136 | 0.458 | +0.322 | [+0.308, +0.337] | 45/45 | 0.704 | 0.005 | 0.058 | 0.261 | 0.151 | 0.555 | 0.121 | 0.361 |
