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


def referenced_identifiers(text: str) -> set[str]:
    """Pull the field names a description refers to.

    Two spellings count: backticked `col_name`, and bare snake_case. Bare
    identifiers must contain an underscore, otherwise ordinary English words
    get mistaken for column names.
    """
    if not text:
        return set()
    backticked = set(re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", text))
    # Bare identifiers may be mixed case (Airport_fee), but still need an underscore
    bare_snake = set(re.findall(r"\b([a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)\b", text))
    # Returned verbatim: case itself is a drift signal (TLC: airport_fee ->
    # Airport_fee). Lowercasing here would erase the very thing we are hunting.
    return backticked | bare_snake


# When an identifier is followed by one of these, the author has named the kind
# of thing it is, and it is not a column of this table.
NON_FIELD_QUALIFIERS = (
    "schema", "table", "database", "dataset", "model", "view", "catalog", "warehouse",
    "method", "strategy", "mode", "package", "macro", "grain",
)

# Phrases that introduce a list of the values a column can hold. What follows is
# data, not schema -- and an enumerated value is spelled exactly like a column.
ENUMERATION_MARKERS = (
    "possible values", "valid values", "values include", "such as",
    "one of", "either", "can be", "e.g.", "for example",
)

# Phrases that introduce a relationship. What follows names the *other* entity,
# which is correct documentation, not a broken field reference.
RELATION_MARKERS = ("foreign key", "referencing", "references the", "belongs to", "points to")


def qualified_as_non_field(text: str, identifier: str) -> bool:
    """Did the text itself say this is not a field, as in "`order_entry` schema"?

    Up to two words may sit between: "`insert_overwrite` incremental method"
    names a method just as plainly as "`x` table" names a table.
    """
    pattern = rf"`?{re.escape(identifier)}`?\s+(?:\w+\s+){{0,2}}({'|'.join(NON_FIELD_QUALIFIERS)})\b"
    return re.search(pattern, text, flags=re.I) is not None


def names_something_else(text: str, identifier: str) -> bool:
    """Does the surrounding prose say this token is not a column of this table?

    Four shapes, all measured on real descriptions rather than imagined:

      "Possible values include `broken`, `deleted`"      -> values
      "the discount applies to all items (`all`)"        -> a value in apposition
      "Foreign key referencing the ID of the `account`"  -> another entity
      "may differ from `incremental_mar.schema_name`"    -> another entity's column

    An enumeration's scope runs to the end of the description rather than to the
    end of its sentence. Written docs list values as bullets and sub-sentences --
    "Valid values include: - `label_printed`: A label was purchased. -
    `in_transit`: ..." -- so a per-sentence window loses the marker on every
    item after the first, which is most of them.

    Callers apply this only where the verdict would otherwise be an assertion
    made without a rename candidate. A near-match in the schema is stronger
    evidence than any prose and keeps its DRIFT verdict.
    """
    ref = re.escape(identifier)

    if re.search(rf"\w\.{ref}\b|\b{ref}\.\w", text):
        return True        # part of a dotted path: a qualified reference elsewhere

    if re.search(rf"\(\s*`?{ref}`?\s*\)", text):
        return True        # parenthesised: an example or a value in apposition

    m = re.search(rf"`?{ref}`?", text)
    head = text[: m.start()].lower() if m else ""
    return any(marker in head for marker in ENUMERATION_MARKERS + RELATION_MARKERS)


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
) -> list[Finding]:
    """D1: do referenced fields still exist, and are any fields undocumented?

    `fields` is what list_schema_fields returns: each entry carries fieldPath
    and description.
    """
    actual = {f.get("fieldPath", "") for f in fields if f.get("fieldPath")}
    self_tokens = self_reference_tokens(entity_urn)
    findings: list[Finding] = []

    # Every field reference on the authored side must resolve on the reality side
    sources = [("dataset description", entity_description)]
    sources += [
        (f'field "{f.get("fieldPath")}" description', f.get("description") or "")
        for f in fields
    ]

    for where, text in sources:
        # sorted, not raw set order: findings are numbered by position, so an
        # order that shifts with PYTHONHASHSEED makes every finding id printed
        # in the docs wrong on the reader's machine.
        for ref in sorted(referenced_identifiers(text)):
            if ref in actual:   # exact match: different case means a different field
                # Recorded rather than skipped. A report that only lists problems
                # cannot show how much was checked, and an abstention is only
                # believable next to the references that did resolve.
                findings.append(
                    Finding(
                        entity_urn=entity_urn,
                        category="D1_SCHEMA_BREAK",
                        verdict="CURRENT",
                        subject=ref,
                        claim=f"{where} references `{ref}`",
                        reality=f"`{ref}` is still a field on this dataset",
                        evidence_ids=list(evidence_ids),
                    )
                )
                continue
            if ref in self_tokens or ref.lower() in self_tokens:
                continue        # refers to the table itself or its database/schema
            if qualified_as_non_field(text, ref):
                continue        # the text qualified it, e.g. "`x` schema"
            candidate = _rename_candidate(ref, actual)

            if candidate:
                # A case/underscore variant exists: strong signal (TLC case)
                verdict, confidence = "DRIFT", "high"
                reality = f"the schema has no `{ref}`, but it does have `{candidate}`"
            elif where != "dataset description" and not names_something_else(text, ref):
                # The reference came from a *field* description. That context is
                # narrow: when a column's own documentation names another
                # snake_case identifier, it is almost always a sibling column
                # (surrogate keys list their components, derived fields name
                # their inputs). A table description is prose and cites other
                # tables, entity types and placeholders; a field description
                # rarely does. Measured on fivetran/dbt_shopify: 9 of 10
                # identifier-change positives live here.
                #
                # Unless the sentence says otherwise. Field descriptions also
                # enumerate values and document relationships, and both spell
                # things exactly like column names -- the single largest source
                # of false positives on both benchmarks.
                verdict, confidence = "DRIFT", "medium"
                reality = f"the schema has no `{ref}` (it has {len(actual)} fields)"
            else:
                # A table description with no near-match to point at. Real ones
                # are prose: they cite other tables, DataHub entity types, and
                # placeholders like `table_name`. Calling every unresolved token
                # drift produced far more noise than signal on real data.
                # The cost: a genuinely deleted column named only in the table
                # description reads as abstention. That trade is deliberate --
                # a report nobody trusts is worth less than one that stays quiet.
                verdict, confidence = "INSUFFICIENT_EVIDENCE", "medium"
                reality = f"the text mentions `{ref}`, which is not a field here and has no close match"

            findings.append(
                Finding(
                    entity_urn=entity_urn,
                    category="D1_SCHEMA_BREAK",
                    verdict=verdict,
                    subject=ref,
                    claim=f"{where} references `{ref}`",
                    reality=reality,
                    evidence_ids=list(evidence_ids),
                    suspected_rename=candidate,
                    confidence=confidence,
                )
            )

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
