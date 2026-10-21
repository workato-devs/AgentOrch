"""Credential-signature checks for artifacts intended for public release."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class CredentialPattern:
    name: str
    pattern: re.Pattern[str]


# These deliberately target provider-specific, high-signal shapes. Generic
# words such as ``token`` and ``password`` are not sufficient evidence on
# their own and would create many false positives in workflow specifications.
CREDENTIAL_PATTERNS = (
    CredentialPattern(
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
            r".*?"
            r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    CredentialPattern(
        "private_key_marker",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    CredentialPattern(
        "url_basic_auth",
        re.compile(
            r"(?P<scheme>https?://)"
            r"[A-Za-z0-9._~%+-]+:"
            r"[A-Za-z0-9._~%!$&()*+,;=:-]+@",
            re.IGNORECASE,
        ),
    ),
    CredentialPattern(
        "aws_access_key",
        re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])"),
    ),
    CredentialPattern(
        "github_token",
        re.compile(
            r"(?<![A-Za-z0-9_])"
            r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"
            r"(?![A-Za-z0-9_])"
        ),
    ),
    CredentialPattern(
        "openai_api_key",
        re.compile(
            r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"
            r"(?![A-Za-z0-9_-])",
            re.IGNORECASE,
        ),
    ),
    CredentialPattern(
        "slack_token",
        re.compile(
            r"(?<![A-Za-z0-9-])xox[baprs]-[A-Za-z0-9-]{10,}"
            r"(?![A-Za-z0-9-])",
            re.IGNORECASE,
        ),
    ),
    CredentialPattern(
        "google_api_key",
        re.compile(
            r"(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{30,}"
            r"(?![A-Za-z0-9_-])"
        ),
    ),
)


def _walk_strings(value: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def credential_signature_counts(value: Any) -> Counter[str]:
    """Return high-signal credential-shape counts without retaining values."""

    counts: Counter[str] = Counter()
    for _path, text in _walk_strings(value):
        remaining = text
        # Patterns run in sanitization order. Removing an entire private-key
        # block prevents its BEGIN marker from being counted a second time.
        for item in CREDENTIAL_PATTERNS:
            matches = list(item.pattern.finditer(remaining))
            if matches:
                counts[item.name] += len(matches)
                remaining = item.pattern.sub("", remaining)
    return counts


def credential_signature_paths(value: Any) -> list[tuple[str, str]]:
    """Return ``(signature, JSON path)`` findings, never matched values."""

    findings: list[tuple[str, str]] = []
    for path, text in _walk_strings(value):
        remaining = text
        for item in CREDENTIAL_PATTERNS:
            matches = list(item.pattern.finditer(remaining))
            findings.extend((item.name, path) for _match in matches)
            if matches:
                remaining = item.pattern.sub("", remaining)
    return findings


def sanitize_credential_signatures(value: Any) -> tuple[Any, Counter[str]]:
    """Copy a JSON value and replace credential-shaped substrings.

    Equal values within a record receive the same deterministic placeholder,
    preserving equality relationships needed by replay examples without
    publishing the source value or a digest of it.
    """

    replacements: dict[tuple[str, str], str] = {}
    ordinals: Counter[str] = Counter()
    counts: Counter[str] = Counter()

    def sanitize_text(text: str) -> str:
        result = text
        for item in CREDENTIAL_PATTERNS:
            def replace(match: re.Match[str]) -> str:
                counts[item.name] += 1
                if item.name == "url_basic_auth":
                    return match.group("scheme")
                matched = match.group(0)
                key = (item.name, matched)
                if key not in replacements:
                    ordinals[item.name] += 1
                    label = item.name.replace("_marker", "")
                    replacements[key] = (
                        f"synthetic-placeholder-{label.replace('_', '-')}-"
                        f"{ordinals[item.name]:03d}"
                    )
                return replacements[key]

            result = item.pattern.sub(replace, result)
        return result

    def copy_and_sanitize(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                key: copy_and_sanitize(child)
                for key, child in item.items()
            }
        if isinstance(item, list):
            return [copy_and_sanitize(child) for child in item]
        if isinstance(item, str):
            return sanitize_text(item)
        return item

    sanitized = copy_and_sanitize(value)
    return sanitized, counts
