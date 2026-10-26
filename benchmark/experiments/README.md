# AgentOrch experiment drivers

- `replan_iter.py`: three rounds of complete-workflow revision using execution feedback (Figure 4 and Table 7).
- `replan_iter_heldout.py`: revision with two feedback variants and separate held-out scoring (Table 7 and Appendix B.2).
- `global_input_selfcheck.py`: CPU check of the Input-Conditioned Global implementation (Table 4).
- `merge_local_view_shards.py`: combines independently evaluated Local shards using the canonical aggregator (Table 5).

Run instructions are in the [evaluation guide](../README.md).
