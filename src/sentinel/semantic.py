"""D5 semantic/glossary drift detection -- the only category in the system where an LLM may intervene (SPEC §2).

The failure mode to catch (BRIEF §9.5, the Pinterest case from the DataHub town hall):
the same business metric is defined differently in each department -- finance's daily
active users differ from marketing's, and the figure where safety filtered out bots
first is in turn marketing's view. Each copy is correct in isolation, but when two
agents each cite one, the user gets contradictory answers with no error signal at all.

The control flow has three stages, with the LLM sandwiched between two deterministic gates:

1. Prefilter (pure function): a pair becomes a candidate only when the term is attached
   to >=2 entities AND the filter condition sets differ. Definition differences with
   identical conditions are just wording, not semantic conflict, and not worth an LLM call.
2. Judgment (injected): the judge is an injected Callable -- this module imports no SDK
   and makes no network requests; production injects an LLM judge, tests inject a fake.
3. Citation gate (pure function): a conflict judgment alone is not enough to stand --
   if either side's quote is missing, or a quote does not match the original definition
   text (the classic symptom of LLM-hallucinated citations), downgrade to INSUFFICIENT_EVIDENCE.
   Abstaining is a legitimate output (SPEC three-state design); an accusation without
   evidence is the problem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Protocol

from .detectors import Verdict


@dataclass(frozen=True)
class TermAttachment:
    """An observation of a glossary term attached to a single entity -- the minimal input unit for the prefilter and the judge.

    filters is the list of WHERE condition strings already parsed upstream; this module
    does not touch SQL parsing, otherwise the prefilter would no longer be an
    independently testable pure function.
    """

    entity_urn: str
    definition: str                     # original definition text of this term on that entity
    filters: tuple[str, ...]            # WHERE conditions of the corresponding column queries (already parsed)
    evidence_ids: tuple[str, ...] = ()


def _normalized_filter_set(filters: tuple[str, ...]) -> frozenset[str]:
    """Turn the condition list into a comparable set.

    Only whitespace normalization and dedup -- condition order and formatting are
    query-style noise, not semantics. Deliberately no case normalization: the case of
    string literals can be semantic ('Bot' and 'bot' may be different tag values);
    the prefilter would rather send extra pairs to the judge than filter out a real conflict.
    """
    return frozenset(re.sub(r"\s+", " ", f).strip() for f in filters if f.strip())


def prescreen(attachments: list[TermAttachment]) -> list[tuple[TermAttachment, TermAttachment]]:
    """Deterministic prefilter: return the entity pairs worth sending to the judge.

    With the term attached to only one entity there are no "two definitions" to speak of;
    with identical filter sets, no matter how different the definition text is, it's just
    a wording difference -- both cases are out immediately and consume no LLM quota.
    A side with an empty definition is bound to fail the citation gate (no original text
    to quote), so block it up front and save a call.
    """
    if len(attachments) < 2:
        return []
    citable = [a for a in attachments if a.definition.strip()]
    return [
        (a, b)
        for a, b in combinations(citable, 2)
        if _normalized_filter_set(a.filters) != _normalized_filter_set(b.filters)
    ]


@dataclass(frozen=True)
class Judgment:
    """The judge's reply. The quote fields are mandatory -- the judge must extract them verbatim from each side's original definition text."""

    conflict: bool                      # whether the two definitions constitute a semantic conflict
    quote_a: str                        # quote extracted from side a's definition (verbatim)
    quote_b: str                        # quote extracted from side b's definition (verbatim)
    rationale: str = ""


class SemanticJudge(Protocol):
    """The judge interface. Production injects an LLM implementation, tests inject a fake.

    Protocol instead of a base class: callers depend only on this signature, and any
    Callable matching it (including plain functions in tests) can be injected without
    inheriting anything.
    """

    def __call__(self, term: str, a: TermAttachment, b: TermAttachment) -> Judgment: ...


@dataclass
class SemanticFinding:
    """D5's output. Does not reuse detectors.Finding -- its category is a closed Literal,

    and claim/reality is a one-way "human-written side vs reality side" structure, while
    a D5 conflict is symmetric: both sides are human-written definitions, and forcing it
    in would lose the mapping of which quote belongs to which entity. Both sides'
    original definition text and filters go into the record in full, so the steward can
    re-verify without looking anything up.
    """

    term: str
    verdict: Verdict
    entity_a: str
    definition_a: str                   # side a's original definition text (the citation gate's comparison baseline)
    filters_a: tuple[str, ...]
    entity_b: str
    definition_b: str
    filters_b: tuple[str, ...]
    quote_a: str | None = None
    quote_b: str | None = None
    rationale: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    category: str = "D5_SEMANTIC_DRIFT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "category": self.category,
            "verdict": self.verdict,
            "entity_a": self.entity_a,
            "definition_a": self.definition_a,
            "filters_a": list(self.filters_a),
            "entity_b": self.entity_b,
            "definition_b": self.definition_b,
            "filters_b": list(self.filters_b),
            "quote_a": self.quote_a,
            "quote_b": self.quote_b,
            "rationale": self.rationale,
            "evidence_ids": self.evidence_ids,
        }


def _quote_is_grounded(quote: str, definition: str) -> bool:
    """A quote counts as evidence only if it appears verbatim in the original definition text.

    LLMs producing quotes that are "roughly the right meaning but not in the original"
    is a known failure mode; a quote that does not match the source cannot enter the
    report no matter how persuasive it is (SPEC §5 citation validity).
    """
    return bool(quote.strip()) and quote.strip() in definition


def detect_semantic_drift(
    term: str,
    attachments: list[TermAttachment],
    judge: SemanticJudge,
) -> list[SemanticFinding]:
    """D5 main flow: prefilter → injected judge → citation gate.

    Judge says "conflict" but the citation gate fails → downgrade to INSUFFICIENT_EVIDENCE,
    not discard: keep the record so the steward knows this pair was once judged suspicious,
    only the system could not produce qualifying evidence.
    Judge says "no conflict" → record a CURRENT entry -- the LLM call has already been
    spent, so the conclusion goes on the books, and a re-run can compare whether the
    judgment for the same pair has drifted.
    """
    findings: list[SemanticFinding] = []
    for a, b in prescreen(attachments):
        judgment = judge(term, a, b)
        evidence = list(a.evidence_ids) + list(b.evidence_ids)

        if not judgment.conflict:
            verdict: Verdict = "CURRENT"
        elif _quote_is_grounded(judgment.quote_a, a.definition) and _quote_is_grounded(
            judgment.quote_b, b.definition
        ):
            verdict = "DRIFT"
        else:
            verdict = "INSUFFICIENT_EVIDENCE"

        findings.append(
            SemanticFinding(
                term=term,
                verdict=verdict,
                entity_a=a.entity_urn,
                definition_a=a.definition,
                filters_a=a.filters,
                entity_b=b.entity_urn,
                definition_b=b.definition,
                filters_b=b.filters,
                quote_a=judgment.quote_a or None,
                quote_b=judgment.quote_b or None,
                rationale=judgment.rationale,
                evidence_ids=evidence,
            )
        )
    return findings
