# Security policy

## Supported version

Security fixes are applied to the latest revision of the default branch. Old
research snapshots and previously generated model outputs are not supported.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository. If the
Security tab does not offer a private report form, contact the repository
owner through the private contact method on their GitHub profile. Do not open
a public issue containing an exploit, credential, private fixture value, or
personal data.

Include the affected path and revision, impact, reproduction steps, and any
suggested mitigation. Remove live credentials from logs and examples. A
maintainer should acknowledge the report, coordinate a fix and disclosure
timeline, and credit the reporter if requested.

## Execution boundary

The simulated backend is the safe default. The optional real-connector backend
can create, update, or delete external resources and must be used only with
least-privilege credentials in an isolated, benchmark-owned environment. See
[`benchmark/verification/README.md`](benchmark/verification/README.md#real-connectors)
before enabling it.
