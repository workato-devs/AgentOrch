# Local library patches used by the RL runs

Three upstream libraries needed one-line guards to run GRPO on these models.
The published RL checkpoints were trained with these patches applied; the SFT
runs do not need them. Each file is a unified diff against the pinned wheel in
`training/requirements-rl.txt`; apply with `patch -p1` inside the package's
`site-packages` directory, or `git apply --directory=<site-packages>`.

| Patch | Library | Why |
|---|---|---|
| `torch-2.13.0-fsdp2-unsharded-param-guard.patch` | torch 2.13.0, `distributed/fsdp/_fully_shard/_fsdp_param.py` | Qwen3.8 wrapper checkpoints carry a vision tower and MTP head that text-only GRPO never executes. FSDP2 shards them but never all-gathers them, and the post-backward pass crashed on `_unsharded_param` when `reduce_dtype` is set. Backport of the guard already merged in pytorch main. Needed by the verl 27B runs. |
| `accelerate-1.14.0-fsdp2-tied-lm-head-group.patch` | accelerate 1.14.0, `utils/fsdp_utils.py` | gemma-4 ties `embed_tokens` and `lm_head`; accelerate's FSDP2 carving left the two tied parameters in different groups, which torch 2.13 rejects. Puts `lm_head` in the same group when weights are tied. Needed by the TRL gemma runs. |
| `trl-1.10.0-fsdp2-vllm-sync-full-tensor-guard.patch` | trl 1.10.0, `generation/vllm_generation.py` | When syncing FSDP2 weights to the colocated vLLM engine, `state_dict()` also yields buffers and un-sharded tensors without `.full_tensor()`, and pushes frozen vision/audio tower weights that vLLM names differently. Skips both. Needed by the TRL gemma runs. |

```bash
SP=$(python -c "import site; print(site.getsitepackages()[0])")
for p in training/src/rl/patches/*.patch; do (cd "$SP" && patch -p1 --forward < "$OLDPWD/$p"); done
```

Everything else in the RL environment is the unmodified pinned wheel.
