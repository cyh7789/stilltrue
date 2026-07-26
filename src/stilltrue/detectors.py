"""Deterministic drift detectors.

D1-D4 in SPEC section 2 are plain code with no LLM involved; only D5 (semantic
drift) needs judgement. This module is pure functions: two sides of signal in,
Findings out. No IO, so it can be tested on its own.

"authored side"  = what descriptions, glossary terms and documents claim
"reality side"   = what the schema, lineage and query history actually show
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

DriftCategory = Literal[
    "D1_SCHEMA_BREAK",      # a description references a field that no longer exists
    "D1_UNDOCUMENTED",      # the field exists but nobody documented it
    "D3_LINEAGE_DRIFT",     # a claimed source is not among the actual upstreams
]

Verdict = Literal["DRIFT", "CURRENT", "INSUFFICIENT_EVIDENCE"]


@dataclass
class Finding:
    entity_urn: str
    category: DriftCategory
    verdict: Verdict
    subject: str              # the field name or claim at issue
    claim: str                # what the authored side says
    reality: str              # what the reality side shows
    evidence_ids: list[str] = field(default_factory=list)
    suspected_rename: str | None = None   # D1 only: which field it was likely renamed to
    confidence: Literal["high", "medium"] = "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_urn": self.entity_urn,
            "category": self.category,
            "verdict": self.verdict,
            "subject": self.subject,
            "claim": self.claim,
            "reality": self.reality,
            "evidence_ids": self.evidence_ids,
            "suspected_rename": self.suspected_rename,
            "confidence": self.confidence,
        }


# Jinja that dbt has not expanded. `{{ doc("history_source") }}` is a lookup
# key, not a column, and a catalog can hold the template rather than the text.
TEMPLATE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)

# Dotted first, so `parent.child` is matched whole before anything splits it.
DOTTED = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)`")
BACKTICKED = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_]*)`")
BARE_SNAKE = re.compile(r"\b([a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)\b")


@dataclass(frozen=True)
class Mention:
    value: str
    kind: Literal["identifier", "unresolved_template"]


@dataclass(frozen=True)
class VanishedField:
    """A field DataHub has seen leave this dataset and not come back."""
    name: str
    operation: str            # REMOVE, or MODIFY where the diff called it a rename
    observed_at: int          # epoch millis of the version that dropped it
    semantic_version: str
    datahub_says: str         # DataHub's own wording, quoted in the finding


RENAME_PHRASE = "renaming of the field"


def vanished_fields(events: list[dict], current: set[str]) -> dict[str, VanishedField]:
    """Read DataHub's schema change log; keep the fields that really are gone.

    Two filters, and the second is load-bearing.

    DataHub's differ matches schema versions **positionally**. When a single
    version changes several things at once -- the NYC TLC replay drops a column,
    renames another and changes three datatypes -- the matcher mis-pairs and
    reports renames that never happened: "renaming of the field 'RatecodeID to
    Airport_fee'". Those claims are self-correcting, because the field they say
    was renamed away is still in the schema. Checking each claim against the
    current field list leaves only the genuine departures. On that replay: three
    claimed, one real, and the real one is the actual 2023-02 TLC event.

    A field removed in one version and re-added in a later one is not vanished;
    the current schema settles it.
    """
    gone: dict[str, VanishedField] = {}
    for ev in sorted(events, key=lambda e: e.get("timestamp", 0)):
        name, op = ev.get("field", ""), ev.get("operation", "")
        if not name:
            continue
        departed = op == "REMOVE" or (op == "MODIFY" and RENAME_PHRASE in ev.get("description", ""))
        if departed:
            gone[name] = VanishedField(
                name=name, operation="REMOVE" if op == "REMOVE" else "RENAMED_FROM",
                observed_at=ev.get("timestamp", 0),
                semantic_version=ev.get("semantic_version", ""),
                datahub_says=ev.get("description", ""),
            )
        elif op == "ADD":
            gone.pop(name, None)          # it came back
    return {n: v for n, v in gone.items() if n not in current}


def identifier_mentions(text: str) -> list[Mention]:
    """Pull identifier *candidates* out of a description.

    Candidates only. Nothing here decides whether a token is a field -- that
    needs schema evidence, and looking like an identifier is not evidence.
    Earlier versions of this module called these "field names", and treating the
    guess as the answer is what made every new corpus produce a new false
    positive.
    """
    if not text:
        return []

    mentions: list[Mention] = []
    if TEMPLATE.search(text):
        mentions.append(Mention("", "unresolved_template"))
    stripped = TEMPLATE.sub(" ", text)

    seen: set[str] = set()
    for rx in (DOTTED, BACKTICKED, BARE_SNAKE):
        for value in rx.findall(stripped):
            if value not in seen:
                seen.add(value)
                mentions.append(Mention(value, "identifier"))
        # Dotted names are consumed whole so their parts are not re-extracted
        # as two separate missing columns.
        if rx is DOTTED:
            for value in list(seen):
                stripped = stripped.replace(f"`{value}`", " ")

    # Sorted so finding ids stay stable across processes; templates lead.
    return ([m for m in mentions if m.kind == "unresolved_template"]
            + sorted((m for m in mentions if m.kind == "identifier"), key=lambda m: m.value))


# When an identifier is followed by one of these, the author named the kind of
# thing it is. Kept as noise reduction only: it can suppress an abstention, and
# it must never overturn a verdict that has schema evidence behind it.
NON_FIELD_QUALIFIERS = (
    "schema", "table", "database", "dataset", "model", "view", "catalog", "warehouse",
    "method", "strategy", "mode", "package", "macro", "grain",
)


def qualified_as_non_field(text: str, identifier: str) -> bool:
    """Did the text itself say this is not a field, as in "`order_entry` schema"?

    Up to two words may sit between: "`insert_overwrite` incremental method"
    names a method just as plainly as "`x` table" names a table.
    """
    pattern = rf"`?{re.escape(identifier)}`?\s+(?:\w+\s+){{0,2}}({'|'.join(NON_FIELD_QUALIFIERS)})\b"
    return re.search(pattern, text, flags=re.I) is not None


def self_reference_tokens(entity_urn: str) -> set[str]:
    """Name fragments belonging to the table itself (database, schema, table).

    A description mentioning its own table or database is normal prose, not a
    field reference. Without this, `order_entry_db.order_entry.order_details`
    gets reported as three non-existent columns.
    """
    inner = re.search(r",([^,]+),[A-Z]+\)$", entity_urn)
    if not inner:
        return set()
    parts = inner.group(1).split(".")
    return {p.lower() for p in parts} | {p for p in parts}


def _rename_candidate(missing: str, actual: set[str]) -> str | None:
    """Which existing field is `missing` likely to have been renamed to?

    Only two mechanically decidable renames count: a case change, and the same
    letters with underscores moved. This is exactly the NYC TLC
    airport_fee -> Airport_fee event.
    """
    lowered = {a.lower(): a for a in actual}
    if missing.lower() in lowered:
        return lowered[missing.lower()]
    squashed = {a.lower().replace("_", ""): a for a in actual}
    key = missing.lower().replace("_", "")
    return squashed.get(key)


def detect_schema_break(
    entity_urn: str,
    entity_description: str,
    fields: list[dict],
    evidence_ids: list[str],
    *,
    vanished: dict[str, VanishedField] | None = None,
) -> list[Finding]:
    """D1: does the prose still name fields this dataset no longer has?

    An assertion needs proof the token was a field here. Two things qualify and
    both come from DataHub:

      a near-match in the current schema   the field was renamed (TLC's
                                           airport_fee -> Airport_fee)
      a departure in the change log        the field was deleted, with no
                                           similarly-named successor to point at

    Everything else abstains. That is the whole rule, and it is why there is no
    list of English phrases in this module any more. Earlier versions asserted on
    any unresolved identifier and then subtracted the shapes that turned out to
    be prose -- enumerated values, neighbouring tables, entity types, unexpanded
    Jinja. Each new corpus supplied a form the last one had not, because
    "which English tokens are not column names" is an open-world problem.
    Requiring evidence closes it: an enumerated value never appears in a schema
    change log, so it can never be asserted, and no rule had to be written to
    say so.

    `vanished` is `None` when no change history was consulted and `{}` when one
    was consulted and showed nothing. Both abstain; the finding says which.
    """
    actual = {f.get("fieldPath", "") for f in fields if f.get("fieldPath")}
    self_tokens = self_reference_tokens(entity_urn)
    gone = vanished or {}
    findings: list[Finding] = []

    sources = [("dataset description", entity_description)]
    sources += [
        (f'field "{f.get("fieldPath")}" description', f.get("description") or "")
        for f in fields
    ]

    def add(**kw: Any) -> None:
        findings.append(Finding(entity_urn=entity_urn, category="D1_SCHEMA_BREAK",
                                evidence_ids=list(evidence_ids), **kw))

    for where, text in sources:
        for mention in identifier_mentions(text):
            if mention.kind == "unresolved_template":
                add(verdict="INSUFFICIENT_EVIDENCE", subject="{{ … }}",
                    claim=f"{where} contains an unexpanded template",
                    reality="the catalog holds Jinja rather than the text a reader sees",
                    confidence="medium")
                continue

            ref = mention.value
            if ref in actual:
                add(verdict="CURRENT", subject=ref,
                    claim=f"{where} references `{ref}`",
                    reality=f"`{ref}` is still a field on this dataset")
                continue
            if ref in self_tokens or ref.lower() in self_tokens:
                continue
            if qualified_as_non_field(text, ref):
                continue

            candidate = _rename_candidate(ref, actual)
            if candidate:
                add(verdict="DRIFT", subject=ref, suspected_rename=candidate,
                    claim=f"{where} references `{ref}`",
                    reality=f"the schema has no `{ref}`, but it does have `{candidate}`")
            elif ref in gone:
                v = gone[ref]
                add(verdict="DRIFT", subject=ref,
                    claim=f"{where} references `{ref}`",
                    reality=f"DataHub's change log records it leaving at v{v.semantic_version}: "
                            f"{v.datahub_says}")
            else:
                seen = ("no change history was available for this dataset"
                        if vanished is None
                        else "DataHub's change log has no record of it leaving")
                add(verdict="INSUFFICIENT_EVIDENCE", subject=ref,
                    claim=f"{where} references `{ref}`",
                    reality=f"`{ref}` is not a field here and {seen}",
                    confidence="medium")

    findings.extend(
        _undocumented_findings(entity_urn, entity_description, fields, evidence_ids)
    )
    return findings


# Above this ratio, report one summary instead of one finding per field:
_BULK_UNDOCUMENTED_RATIO = 0.5


def _undocumented_findings(
    entity_urn: str,
    entity_description: str,
    fields: list[dict],
    evidence_ids: list[str],
) -> list[Finding]:
    """Fields that exist in reality but nobody wrote about.

    Only counts as drift when the table itself has a description yet some
    fields were missed: that is documentation failing to keep up with the
    schema. A table with no description anywhere is a different thing entirely
    (never started, rather than fallen out of sync), and reporting it here
    would bury the real signal under noise.
    """
    if not (entity_description or "").strip():
        return []

    missing = [f for f in fields if f.get("fieldPath") and not (f.get("description") or "").strip()]
    if not missing:
        return []

    if len(missing) / len(fields) > _BULK_UNDOCUMENTED_RATIO:
        return [
            Finding(
                entity_urn=entity_urn,
                category="D1_UNDOCUMENTED",
                verdict="DRIFT",
                subject=f"{len(missing)}/{len(fields)} fields",
                claim="the table itself is documented",
                reality=f"but {len(missing)} of {len(fields)} fields carry no description at all; confirm this table is still maintained before filling them in one by one",
                evidence_ids=list(evidence_ids),
                confidence="medium",
            )
        ]

    return [
        Finding(
            entity_urn=entity_urn,
            category="D1_UNDOCUMENTED",
            verdict="DRIFT",
            subject=f["fieldPath"],
            claim="the table is documented, this field is not",
            reality=f"field `{f['fieldPath']}` ({f.get('nativeDataType', 'unknown type')}) exists in the schema but has no description",
            evidence_ids=list(evidence_ids),
        )
        for f in missing
    ]


def detect_lineage_drift(
    entity_urn: str,
    entity_description: str,
    upstream_urns: list[str],
    evidence_ids: list[str],
) -> list[Finding]:
    """D3: is the source a description claims still among the actual upstreams?"""
    claims = re.findall(
        r"(?:derived from|source[sd]?(?:\s+from)?|built from|based on)\s+`?([a-zA-Z_][\w.]*)`?",
        entity_description or "",
        flags=re.I,
    )
    if not claims:
        return []

    upstream_names = {u.lower() for u in upstream_urns}
    findings = []
    for claimed in sorted({c.lower() for c in claims}):
        if any(claimed in u for u in upstream_names):
            findings.append(
                Finding(
                    entity_urn=entity_urn,
                    category="D3_LINEAGE_DRIFT",
                    verdict="CURRENT",
                    subject=claimed,
                    claim=f"the description claims the data comes from `{claimed}`",
                    reality=f"`{claimed}` is among the {len(upstream_urns)} actual upstreams",
                    evidence_ids=list(evidence_ids),
                )
            )
            continue
        findings.append(
            Finding(
                entity_urn=entity_urn,
                category="D3_LINEAGE_DRIFT",
                verdict="DRIFT",
                subject=claimed,
                claim=f"the description claims the data comes from `{claimed}`",
                reality=f"there are {len(upstream_urns)} actual upstreams, none of them `{claimed}`",
                evidence_ids=list(evidence_ids),
                confidence="medium",
            )
        )
    return findings
