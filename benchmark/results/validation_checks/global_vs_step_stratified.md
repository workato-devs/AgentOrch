# Performance across workflow characteristics

Pooled Global and Step-by-Step results for the subgroup analysis in Appendix E.
Scores and gaps below use fractions; gap is Step-by-Step minus Global.
Confidence intervals are clustered by SOP.

| Feature | Subset | SOPs | Variants | Global | Step-by-Step | Gap | 95% CI | Global error | Step error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| all | all | 650 | 3220 | 0.138 | 0.4638 | 0.3259 | [0.3122, 0.342] | 0.7068 | 0.0053 |
| size_num_tool_calls | long (6+ calls) | 165 | 1036 | 0.0828 | 0.4659 | 0.3831 | [0.3514, 0.4131] | 0.8198 | 0.0065 |
| size_num_tool_calls | medium (3-5 calls) | 251 | 1149 | 0.1423 | 0.473 | 0.3307 | [0.309, 0.3514] | 0.6933 | 0.0045 |
| size_num_tool_calls | short (1-2 calls) | 234 | 1035 | 0.1884 | 0.4515 | 0.2631 | [0.2445, 0.2839] | 0.6086 | 0.0049 |
| num_apps | <=1 | 235 | 1192 | 0.1901 | 0.5148 | 0.3247 | [0.3024, 0.3468] | 0.6521 | 0.0041 |
| num_apps | 2 | 360 | 1676 | 0.1174 | 0.4423 | 0.3249 | [0.304, 0.3458] | 0.721 | 0.0057 |
| num_apps | 3+ | 55 | 352 | 0.0594 | 0.3936 | 0.3343 | [0.2855, 0.385] | 0.8241 | 0.0073 |
| conditional | has_conditional | 347 | 1981 | 0.1357 | 0.4997 | 0.364 | [0.3444, 0.3839] | 0.7329 | 0.0051 |
| conditional | no_conditional | 303 | 1239 | 0.1416 | 0.4065 | 0.2649 | [0.2464, 0.2836] | 0.665 | 0.0056 |
| loop | has_loop | 139 | 807 | 0.0852 | 0.4427 | 0.3575 | [0.3257, 0.391] | 0.7892 | 0.0082 |
| loop | no_loop | 511 | 2413 | 0.1556 | 0.4709 | 0.3153 | [0.2991, 0.3317] | 0.6792 | 0.0043 |
| try_catch | has_try_catch | 237 | 1291 | 0.1398 | 0.5119 | 0.3722 | [0.3473, 0.3965] | 0.7482 | 0.0048 |
| try_catch | no_try_catch | 413 | 1929 | 0.1368 | 0.4316 | 0.2949 | [0.2765, 0.3121] | 0.679 | 0.0056 |
| structure_category | branch_only | 132 | 688 | 0.1491 | 0.4856 | 0.3364 | [0.3022, 0.3675] | 0.694 | 0.0046 |
| structure_category | error_handling_only | 78 | 295 | 0.1665 | 0.4883 | 0.3218 | [0.2841, 0.3606] | 0.6958 | 0.0047 |
| structure_category | linear | 186 | 781 | 0.1439 | 0.3968 | 0.2529 | [0.229, 0.2785] | 0.6418 | 0.0053 |
| structure_category | loop_only | 36 | 148 | 0.0893 | 0.3092 | 0.2199 | [0.1855, 0.26] | 0.7039 | 0.0072 |
| structure_category | multiple_control_flow_types | 218 | 1308 | 0.1276 | 0.5044 | 0.3768 | [0.3517, 0.4035] | 0.755 | 0.0056 |
| nesting_depth | 2 | 235 | 1030 | 0.1502 | 0.4783 | 0.3281 | [0.3049, 0.3525] | 0.6933 | 0.0043 |
| nesting_depth | 3+ | 229 | 1409 | 0.1257 | 0.4904 | 0.3647 | [0.3418, 0.3868] | 0.7526 | 0.006 |
| nesting_depth | 1 (flat) | 186 | 781 | 0.1439 | 0.3968 | 0.2529 | [0.2284, 0.2793] | 0.6418 | 0.0053 |
| fault_injection | fault_variant | 224 | 264 | 0.1636 | 0.5284 | 0.3648 | [0.3383, 0.3939] | 0.7423 | 0.0062 |
| fault_injection | normal_variant | 650 | 2956 | 0.1357 | 0.4581 | 0.3224 | [0.308, 0.3373] | 0.7036 | 0.0052 |
