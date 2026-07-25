"""Behavior tests for the D5 semantic drift detector.

The judge is always an injected fake -- these test this module's control flow
and citation gate, not any LLM's judgment quality. Break the pre-filter or the
citation gate and these go red; renaming things won't.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.semantic import (  # noqa: E402
    Judgment,
    TermAttachment,
    detect_semantic_drift,
)

# Minimal reproduction of the Pinterest case: same DAU term, the marketing side filters out bots first
FINANCE = TermAttachment(
    entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,finance.dau_daily,PROD)",
    definition="Daily active users: all accounts with at least one session per day.",
    filters=("event_date = CURRENT_DATE", "session_count >= 1"),
    evidence_ids=("ev_fin",),
)
MARKETING = TermAttachment(
    entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,marketing.dau_daily,PROD)",
    definition="Daily active users, excluding accounts flagged as bots by safety.",
    filters=("event_date = CURRENT_DATE", "session_count >= 1", "is_bot = false"),
    evidence_ids=("ev_mkt",),
)


class RecordingJudge:
    """Records every pair it gets called with; returns a preset judgment."""

    def __init__(self, judgment: Judgment) -> None:
        self.judgment = judgment
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, term: str, a: TermAttachment, b: TermAttachment) -> Judgment:
        self.calls.append((term, a.entity_urn, b.entity_urn))
        return self.judgment


def _conflict_with_valid_quotes() -> Judgment:
    """Quotes taken verbatim from the two definitions above -- a valid judgment the citation gate should let through."""
    return Judgment(
        conflict=True,
        quote_a="all accounts with at least one session",
        quote_b="excluding accounts flagged as bots",
        rationale="one side includes bots, the other excludes them, so the same metric has different denominators",
    )


def test_single_entity_never_triggers():
    """With only one entity attached to the term there is no second definition to conflict with; the judge must never be called."""
    judge = RecordingJudge(_conflict_with_valid_quotes())
    assert detect_semantic_drift("DAU", [FINANCE], judge) == []
    assert judge.calls == []


def test_identical_filters_never_reach_judge():
    """Identical filters mean both sides look at the same population; wording differences are not semantic conflict.

    Different order and formatting still count as identical -- that's query-style noise, and sending it to the judge wastes LLM quota.
    """
    same_population = TermAttachment(
        entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,growth.dau_daily,PROD)",
        definition="Count of users active on a given day.",
        filters=("session_count >= 1", "event_date  =  CURRENT_DATE"),
        evidence_ids=("ev_growth",),
    )
    judge = RecordingJudge(_conflict_with_valid_quotes())
    assert detect_semantic_drift("DAU", [FINANCE, same_population], judge) == []
    assert judge.calls == []


def test_differing_filters_are_sent_to_judge_exactly_once():
    """Only pairs with differing filter sets reach the judge, and each pair is judged exactly once."""
    judge = RecordingJudge(_conflict_with_valid_quotes())
    detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert judge.calls == [("DAU", FINANCE.entity_urn, MARKETING.entity_urn)]


def test_conflict_with_both_quotes_yields_drift_carrying_both_sides():
    """Judge says conflict and both quotes are valid → DRIFT, carrying both sides' original definitions and filters.

    The steward re-verifies from the finding alone -- without either side's original text, the re-verification gate is a sham.
    """
    judge = RecordingJudge(_conflict_with_valid_quotes())
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert len(findings) == 1
    f = findings[0]
    assert f.verdict == "DRIFT"
    assert f.definition_a == FINANCE.definition
    assert f.filters_a == FINANCE.filters
    assert f.definition_b == MARKETING.definition
    assert f.filters_b == MARKETING.filters
    assert sorted(f.evidence_ids) == ["ev_fin", "ev_mkt"]


def test_missing_quote_downgrades_to_insufficient_evidence():
    """Judge says conflict but one quote is missing → downgrade to abstain, not DRIFT and not discarded."""
    judge = RecordingJudge(
        Judgment(conflict=True, quote_a="all accounts with at least one session", quote_b="")
    )
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert [f.verdict for f in findings] == ["INSUFFICIENT_EVIDENCE"]


def test_hallucinated_quote_downgrades_to_insufficient_evidence():
    """Both quotes present, but one doesn't match the original definition text → same downgrade.

    "Roughly the right meaning but not in the original" is a known failure mode
    of LLM citations; a quote that doesn't match the source is not evidence
    (SPEC §5 citation validity).
    """
    judge = RecordingJudge(
        Judgment(
            conflict=True,
            quote_a="all accounts with at least one session",
            quote_b="bots are removed before counting",  # this sentence is not in the original definition
        )
    )
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert [f.verdict for f in findings] == ["INSUFFICIENT_EVIDENCE"]


def test_judge_says_consistent_records_current():
    """Judge says no conflict → record CURRENT, so a re-run can compare whether the judgment for the same pair has drifted."""
    judge = RecordingJudge(Judgment(conflict=False, quote_a="", quote_b=""))
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert [f.verdict for f in findings] == ["CURRENT"]
