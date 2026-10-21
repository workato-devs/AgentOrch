# Public release checklist

The repository is technically staged but must not be published until every
blocking item below is complete.

## Publisher decisions

- [x] Canonical repository: `github.com/jesseliu0913/AgentOrch`.
- [x] Set the GitHub description to: “Benchmark and training suite for
  evaluating language-model orchestration of business workflows.”
- [x] Add topics such as `llm-agents`, `tool-use`, `workflow-automation`,
  `benchmark`, and `agent-orchestration`.
- [ ] Select a project/dataset license after confirming distribution rights
  for the underlying recipe material; add the approved text as `LICENSE`.
- [ ] Add a valid `CITATION.cff` with the final paper title, complete author
  list, version, release date, and canonical repository/paper URLs.
- [ ] Record approval of the privacy, source-rights, and third-party review.
- [ ] Enable GitHub private vulnerability reporting and Discussions (if the
  maintainers intend to provide community support).

## Release artifacts

- [x] Upload the fine-tuned checkpoints (10 `agentorch-*` model repos on the Hugging Face Hub,
  linked from the README).
- [ ] Fill the `hf_repo` column in `training/results/training.csv` for those rows.
- [ ] Decide whether and where the 80 GB per-variant result archive will be
  distributed; document a version and checksum if published.
- [x] From a clean clone, run `python scripts/download_data.py --prepared` and
  confirm every archive passes its checksum (done 2026-10-21).
- [ ] Create a versioned GitHub release and attach immutable release notes.

## Final validation

```bash
python scripts/download_data.py --prepared
python scripts/release_check.py --smoke --write-checksums
sha256sum -c SHA256SUMS
```

The release checker intentionally fails while `LICENSE` or `CITATION.cff` is
missing. After it passes, test the README quick start in a clean clone with no
pre-existing environment variables or caches.
