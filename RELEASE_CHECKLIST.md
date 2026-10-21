# Public release checklist

The repository is technically staged but must not be published until every
blocking item below is complete.

## Publisher decisions

- [ ] Confirm the canonical GitHub owner/repository name. The surrounding
  worktree's remote uses the apparent `agnetorch` spelling, while this README
  uses `agentorch`.
- [ ] Set the GitHub description to: “Benchmark and training suite for
  evaluating language-model orchestration of business workflows.”
- [ ] Add topics such as `llm-agents`, `tool-use`, `workflow-automation`,
  `benchmark`, and `agent-orchestration`.
- [ ] Select a project/dataset license after confirming distribution rights
  for the underlying recipe material; add the approved text as `LICENSE`.
- [ ] Add a valid `CITATION.cff` with the final paper title, complete author
  list, version, release date, and canonical repository/paper URLs.
- [ ] Record approval of the privacy, source-rights, and third-party review.
- [ ] Enable GitHub private vulnerability reporting and Discussions (if the
  maintainers intend to provide community support).

## Release artifacts

- [ ] Upload every promised fine-tuned checkpoint and fill the `hf_repo`
  column in `training/results/training.csv`, or remove the download claim.
- [ ] Decide whether and where the 80 GB per-variant result archive will be
  distributed; document a version and checksum if published.
- [ ] From a clean clone, run `python scripts/download_data.py --prepared` and
  confirm every archive passes its checksum.
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
