"""Local LoRA SFT for Qwen3.8-27B on the benchmark-aligned training data.

Design: pure data-parallel (DDP) — a full bf16 copy of the 27B model fits on
one H200 (141 GB) alongside 64k-token activations under gradient
checkpointing, and LoRA means the gradient all-reduce is tiny. Loss is masked
to the assistant turn only. Rows come from prepare_dataset.py's train.jsonl
(messages format, already length-filtered).

Launch (single node, 8 GPUs):
  torchrun --nproc-per-node 8 train_sft_local.py --max-rows 24  # smoke
  torchrun --nproc-per-node 8 train_sft_local.py                # full run

Env: the SFT environment from training/requirements-sft.txt (torch 2.13, peft, trl).
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import time

import torch
import torch.distributed as dist
from peft import LoraConfig, get_peft_model
from torch.utils.data import DataLoader, Dataset, DistributedSampler
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

SRC_DIR = Path(__file__).resolve().parent
TRAIN_ROOT = SRC_DIR.parents[1]
DEFAULT_MODEL = "Qwen/Qwen3.8-27B"


class PlanSftDataset(Dataset):
    """Tokenized rows with prompt tokens masked out of the loss."""

    def __init__(self, path: Path, tokenizer, max_len: int, max_rows: int = 0,
                 max_target_tokens: int = 6144):
        # enable_thinking=False renders the plain system/user/assistant turns
        # with no injected reasoning-effort preamble; inference must use the
        # same setting for template consistency.
        self.rows = []
        skipped = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                messages = json.loads(line)["messages"]
                prompt_text = tokenizer.apply_chat_template(
                    messages[:-1], add_generation_prompt=True, tokenize=False,
                    enable_thinking=False)
                full_text = tokenizer.apply_chat_template(
                    messages, tokenize=False, enable_thinking=False)
                if not full_text.startswith(prompt_text):
                    # Some templates (gemma-4) append tokens to the generation
                    # prompt that the full render omits (an empty closed
                    # thought channel). Build the training sequence as the
                    # exact inference-time context plus the continuation, so
                    # train and eval boundaries match byte-for-byte.
                    common = 0
                    limit = min(len(full_text), len(prompt_text))
                    while common < limit and full_text[common] == prompt_text[common]:
                        common += 1
                    full_text = prompt_text + full_text[common:]
                enc = tokenizer(full_text, add_special_tokens=False,
                                return_offsets_mapping=True)
                full_ids = enc.input_ids
                # Mask every token that starts before the assistant content;
                # a token straddling the boundary stays masked (conservative).
                boundary = len(prompt_text)
                prompt_len = sum(1 for start, _end in enc.offset_mapping
                                 if start < boundary)
                target_len = len(full_ids) - prompt_len
                # Targets beyond the benchmark's 4096 decode cap can never be
                # emitted at eval; they also blow up the fp32 logits buffer
                # (target_tokens x 248k vocab). Drop them.
                if (len(full_ids) > max_len or target_len <= 0
                        or target_len > max_target_tokens):
                    skipped += 1
                    continue
                self.rows.append((full_ids[:prompt_len], full_ids))
                if max_rows and len(self.rows) >= max_rows:
                    break
        self.skipped = skipped

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        prompt_ids, full_ids = self.rows[index]
        input_ids = torch.tensor(full_ids, dtype=torch.long)
        labels = input_ids.clone()
        labels[:len(prompt_ids)] = -100
        return {"input_ids": input_ids, "labels": labels}


def save_adapter(model, out_dir: Path, is_main: bool) -> None:
    """Gather DTensor LoRA weights (collective — all ranks call) and save."""
    from peft import get_peft_model_state_dict
    state = get_peft_model_state_dict(model)
    state = {key: (value.full_tensor() if hasattr(value, "full_tensor")
                   else value).cpu()
             for key, value in state.items()}
    if is_main:
        model.save_pretrained(out_dir, state_dict=state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--attn-impl", default="sdpa",
                        help="attention implementation; use flex_attention for "
                             "sliding-window models (gemma-4) so windows are "
                             "not computed as full quadratic attention")
    parser.add_argument("--data", type=Path,
                        default=TRAIN_ROOT / "data" / "sft_v1_80k" / "train.jsonl")
    parser.add_argument("--output", type=Path,
                        default=TRAIN_ROOT / "output" / "checkpoints" / "sft-lora")
    parser.add_argument("--max-len", type=int, default=65_536)
    parser.add_argument("--max-target-tokens", type=int, default=6144)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--grad-accum", type=int, default=2)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--log-every", type=int, default=1)
    parser.add_argument("--save-every-steps", type=int, default=100)
    parser.add_argument("--wandb-project", default="agentorch-qwen38-sft",
                        help="wandb project; pass '' to disable logging")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--seed", type=int, default=0,
                        help="seeds torch / CUDA RNGs and the data sampler; LoRA init "
                             "and the shuffle order are reproducible, bf16 multi-GPU "
                             "kernels are not bit-exact")
    parser.add_argument("--model-revision", default=os.environ.get("HF_MODEL_REVISION"),
                        help="pinned Hugging Face revision of --model; defaults to "
                             "$HF_MODEL_REVISION, else the entry for --model in "
                             "base_models.json (recorded in train_config.json)")
    parser.add_argument("--deterministic", action="store_true",
                        help="request deterministic kernels (cudnn.deterministic, "
                             "use_deterministic_algorithms warn_only, CUBLAS_WORKSPACE_CONFIG); "
                             "slower, and still not bit-exact across GPU counts or drivers")
    args = parser.parse_args()
    if args.model_revision is None:
        pins = json.loads((SRC_DIR / "base_models.json").read_text(encoding="utf-8"))
        args.model_revision = pins.get(args.model, {}).get("revision")
    if args.deterministic:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.use_deterministic_algorithms(True, warn_only=True)

    dist.init_process_group("nccl")
    rank = dist.get_rank()
    world = dist.get_world_size()
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    is_main = rank == 0
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    def log(msg: str) -> None:
        if is_main:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    wandb_run = None
    if is_main and args.wandb_project:
        import wandb
        wandb_dir = SRC_DIR / "wandb_logs"
        wandb_dir.mkdir(exist_ok=True)
        wandb_run = wandb.init(
            project=args.wandb_project,
            name=args.run_name or f"sft-{time.strftime('%m%d-%H%M')}",
            dir=str(wandb_dir),
            config={**vars(args), "world_size": world,
                    "data": str(args.data), "output": str(args.output)},
        )
        log(f"wandb run: {wandb_run.url}")

    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.model_revision)
    if is_main:
        # record everything needed to re-run this job next to the checkpoints
        import transformers, peft
        args.output.mkdir(parents=True, exist_ok=True)
        record = {**vars(args), "data": str(args.data), "output": str(args.output),
                  "world_size": world, "torch": torch.__version__,
                  "transformers": transformers.__version__, "peft": peft.__version__,
                  "cuda": torch.version.cuda}
        (args.output / "train_config.json").write_text(
            json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    dataset = PlanSftDataset(args.data, tokenizer, args.max_len, args.max_rows,
                             args.max_target_tokens)
    log(f"dataset: {len(dataset)} rows (skipped {dataset.skipped} over {args.max_len})")

    sampler = DistributedSampler(dataset, num_replicas=world, rank=rank,
                                 shuffle=True, seed=args.seed)
    loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=2,
                        collate_fn=lambda items: items[0])

    log(f"loading {args.model} in bf16 on cuda:{local_rank}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, attn_implementation=args.attn_impl,
        revision=args.model_revision)
    model.config.use_cache = False
    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.0,
        target_modules="all-linear", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora)
    if is_main:
        model.print_trainable_parameters()
    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model.to(f"cuda:{local_rank}")
    model.train()
    # FSDP2: shard the 54GB base across ranks (~7GB/rank) so 64k-token
    # activations fit; LoRA grads stay tiny so comms are cheap.
    from torch.distributed.fsdp import fully_shard
    decoder_layers = [m for n, m in model.named_modules()
                      if type(m).__name__.endswith("DecoderLayer")]
    if not decoder_layers:
        raise RuntimeError("no decoder layers found to shard")
    for layer in decoder_layers:
        fully_shard(layer)
    fully_shard(model)
    log(f"FSDP2 sharded {len(decoder_layers)} decoder layers across {world} ranks")
    ddp = model

    trainable = [p for p in ddp.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.0)
    steps_per_epoch = math.ceil(len(loader) / args.grad_accum)
    total_steps = max(int(steps_per_epoch * args.epochs), 1)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, int(total_steps * args.warmup_ratio), total_steps)
    log(f"world={world} rows/rank={len(loader)} grad_accum={args.grad_accum} "
        f"optimizer_steps={total_steps}")

    args.output.mkdir(parents=True, exist_ok=True)
    step = 0
    accumulated = 0.0
    t_step = time.time()
    epochs_int = math.ceil(args.epochs)
    for epoch in range(epochs_int):
        sampler.set_epoch(epoch)
        for micro, batch in enumerate(loader):
            input_ids = batch["input_ids"].unsqueeze(0).to(f"cuda:{local_rank}")
            labels = batch["labels"].unsqueeze(0).to(f"cuda:{local_rank}")
            # The 248k vocab makes full-sequence logits enormous (~26GB bf16
            # at 52k positions); the loss only needs the assistant tail, so
            # compute logits for the last K positions only.
            keep = int((labels != -100).sum().item()) + 8
            out = ddp(input_ids=input_ids, logits_to_keep=keep)
            # logits[:, j] predicts input_ids[:, seq_len - keep + j + 1]
            logits = out.logits[:, :-1].float()
            tail_labels = labels[:, -keep + 1:]
            raw_loss = torch.nn.functional.cross_entropy(
                logits.flatten(0, 1), tail_labels.flatten(), ignore_index=-100)
            loss = raw_loss / args.grad_accum
            loss.backward()
            accumulated += raw_loss.item()
            if (micro + 1) % args.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                if step % args.log_every == 0:
                    mem = torch.cuda.max_memory_allocated() / 1e9
                    step_loss = accumulated / args.grad_accum
                    step_time = time.time() - t_step
                    log(f"epoch {epoch} step {step}/{total_steps} "
                        f"loss {step_loss:.4f} "
                        f"tokens {input_ids.shape[1]} "
                        f"{step_time:.1f}s/step mem {mem:.0f}GB")
                    if wandb_run is not None:
                        wandb_run.log({
                            "train/loss": step_loss,
                            "train/lr": scheduler.get_last_lr()[0],
                            "train/tokens_in_last_row": input_ids.shape[1],
                            "train/sec_per_step": step_time,
                            "train/peak_mem_gb": mem,
                            "train/epoch": epoch,
                        }, step=step)
                accumulated = 0.0
                t_step = time.time()
                if step % args.save_every_steps == 0:
                    save_adapter(ddp, args.output / f"step-{step}", is_main)
                if step >= total_steps:
                    break
        if step >= total_steps:
            break

    dist.barrier()
    save_adapter(ddp, args.output / "final", is_main)
    if is_main:
        tokenizer.save_pretrained(args.output / "final")
        log(f"saved LoRA adapter to {args.output / 'final'}")
    if wandb_run is not None:
        wandb_run.finish()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
