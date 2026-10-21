# Contributing to AgentOrch

Thanks for helping improve AgentOrch. Small, reviewable pull requests are the
easiest to validate, especially when benchmark fixtures or published results
are involved.

## Before opening an issue

- Use the latest revision of the default branch.
- Search existing issues for the recipe ID, model ID, or error message.
- Remove API keys, private URLs, organization data, and model outputs that you
  are not allowed to share.
- Use a GitHub security advisory instead of a public issue for vulnerabilities
  or suspected credential exposure; see [`SECURITY.md`](SECURITY.md).

## Development setup

The CPU-only validation path needs Python 3.12:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest scripts/tests -q
python scripts/release_check.py --smoke --allow-incomplete-metadata
```

Install [`benchmark/requirements.txt`](benchmark/requirements.txt) only when
working on model evaluation or analysis. Training dependencies belong in
separate SFT and RL environments as described in
[`training/README.md`](training/README.md#set-up).

## Pull-request workflow

1. Create a focused branch and explain the user-visible problem.
2. Keep evaluator behavior, fixtures, and published result tables unchanged
   unless the pull request explicitly justifies a benchmark revision.
3. Add or update tests for executable changes. For fixture changes, update all
   mirrored copies and their manifests.
4. Run `python scripts/release_check.py --smoke --allow-incomplete-metadata`
   from the repository root. Omit the final option when validating a release.
5. If files changed, regenerate `SHA256SUMS` with
   `python scripts/release_check.py --write-checksums --allow-incomplete-metadata`
   and include it in the same pull request. New non-ignored files are included;
   review `git status --short` first. Omit the metadata exception for a release.
6. Complete the pull-request template, including reproducibility and data-risk
   notes.

Do not hand-edit leaderboard aggregates. Change their source CSV/JSON and run
the documented builder. Do not commit `.env`, credentials, checkpoints, run
outputs, or unrestricted third-party data.

## Scope and review expectations

Documentation fixes and new adapters are welcome. Changes to scoring,
ground-truth plans, simulator state, dataset membership, or headline numbers
need a clear migration note because they can invalidate comparisons with the
frozen release. Maintainers may ask for a new versioned benchmark snapshot
instead of changing the existing contract in place.

## Automated checks

GitHub Actions runs the CPU regression tests, sample-recipe smoke checks,
relative-link and result-table checks, and `SHA256SUMS` verification on pushes
and pull requests. It uses the sample committed in Git and needs no downloaded
data or provider credentials. Development CI allows unfinished publication
metadata; the strict release command in `RELEASE_CHECKLIST.md` still requires it.

`python scripts/build_combined_leaderboard.py --check` checks the generated
tables without writing them. Run the builder without `--check` after an
intentional source-table update. Release smoke checks use a temporary run
directory and preserve existing connector outputs and Python caches.
