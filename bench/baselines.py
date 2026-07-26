"""Baselines: what you get without the full context loop.

Each baseline is something a team could plausibly do today, in increasing order
of how much DataHub context it uses. Running all of them against the same
benchmark is how "we needed the context graph for this" stops being a claim and
becomes a number.

B0  no context          only the prose. No schema, no lineage.
B1  coverage only       what DataHub's own documentation-coverage view shows:
                        which fields lack a description. No cross-checking of
                        what the prose actually says.
B2  case-insensitive    prose vs schema, but matching field names the way most
                        people would write it in an afternoon: lowercased.
"""

from __future__ import annotations

import re
from typing import Any


def _referenced(text: str) -> set[str]:
    if not text:
        return set()
    backticked = set(re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", text))
    bare = set(re.findall(r"\b([a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)\b", text))
    return backticked | bare


def b0_no_context(description: str, fields: list[dict]) -> list[str]:
    """Only the prose is available.

    Without the schema there is nothing to compare against, so this cannot
    report drift at all. That is the point of including it: it is the position
    every agent is in before DataHub is wired up.
    """
    return []


def b1_coverage_only(description: str, fields: list[dict]) -> list[str]:
    """Which fields have no description. DataHub already shows this natively.

    Catches columns nobody documented. Cannot catch a description that is
    present but wrong, because it never reads the description.
    """
    return [f["fieldPath"] for f in fields
            if f.get("fieldPath") and not (f.get("description") or "").strip()]


def b2_case_insensitive(description: str, fields: list[dict]) -> list[str]:
    """Prose vs schema, compared the obvious way: lowercase both sides.

    This is the version most people would write first, and it is the version
    that silently misses a case-only rename -- normalising the case erases the
    very difference that constitutes the drift.
    """
    actual = {f.get("fieldPath", "").lower() for f in fields}
    return [ref for ref in _referenced(description) if ref.lower() not in actual]


def ours(description: str, fields: list[dict], entity_urn: str,
         vanished: dict | None = None) -> list[str]:
    """The full loop, for comparison on the same inputs.

    `vanished` is DataHub's change log for this dataset, and it is only nominally
    optional: an assertion needs the log to record the field leaving, so calling
    this without one measures a detector that has been denied its evidence. It
    went unpassed for one commit after the rename rule tightened, and the
    comparison table silently fell to a tie with B1. The baselines are supposed
    to lose on the merits.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from stilltrue.detectors import detect_schema_break

    found = detect_schema_break(entity_urn, description, fields, ["ev_bench"],
                                vanished=vanished)
    return [f.subject for f in found if f.verdict == "DRIFT"]


def evaluate(description: str, fields: list[dict], entity_urn: str,
             expected: set[str], vanished: dict | None = None) -> dict[str, Any]:
    """Score every baseline against the same expected set."""
    runs = {
        "B0 no context": b0_no_context(description, fields),
        "B1 coverage only": b1_coverage_only(description, fields),
        "B2 case-insensitive": b2_case_insensitive(description, fields),
        "StillTrue": ours(description, fields, entity_urn, vanished),
    }
    scored = {}
    for name, reported in runs.items():
        hit = expected & set(reported)
        scored[name] = {
            "reported": sorted(reported),
            "caught": sorted(hit),
            "missed": sorted(expected - set(reported)),
            "false_positives": len(set(reported) - expected),
            "recall": f"{len(hit)}/{len(expected)}",
        }
    return scored
