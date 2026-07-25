"""Behavior tests for the Policy Gate.

The gate's value is that it actually blocks things, so every test is an attack:
citing fake evidence, blanking content, changing what must not change,
repackaging the same content as something new.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.evidence import Evidence, EvidenceStore  # noqa: E402
from sentinel.proposal import PolicyGate, Proposal  # noqa: E402

URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"


def _store_with_one_evidence() -> tuple[EvidenceStore, str]:
    store = EvidenceStore()
    ev_id = store.add(Evidence(entity_urn=URN, source_function="list_schema_fields",
                               payload={"fields": [{"fieldPath": "Airport_fee"}]}))
    return store, ev_id


def _valid_proposal(ev_id: str, **overrides) -> Proposal:
    base = dict(
        entity_urn=URN, aspect="dataset_description", verdict="DRIFT", subject="description",
        before_value="Fare breakdown includes airport_fee for LGA/JFK pickups.",
        after_value="Fare breakdown includes Airport_fee for LGA/JFK pickups.",
        rationale="the schema names the field Airport_fee; the description still says airport_fee.",
        evidence_ids=[ev_id],
    )
    base.update(overrides)
    return Proposal(**base)


def test_valid_proposal_passes():
    store, ev = _store_with_one_evidence()
    assert PolicyGate(store).check(_valid_proposal(ev)).passed


def test_fabricated_evidence_is_rejected():
    """The mistake LLMs make most often: citing an evidence_id that sounds plausible but doesn't exist."""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, evidence_ids=["ev_deadbeef12345678"]))

    assert not result.passed
    assert any("does not exist" in v for v in result.violations)


def test_proposal_without_evidence_is_rejected():
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, evidence_ids=[]))

    assert not result.passed
    assert any("cites no evidence" in v for v in result.violations)


def test_clearing_content_is_rejected():
    """Blanking the description is also a kind of "fix", but deletion is not within the allowed scope."""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, after_value="   "))

    assert not result.passed
    assert any("blank the content" in v for v in result.violations)


def test_non_drift_verdict_cannot_produce_a_change():
    """On abstain or a no-drift verdict, no write proposal should appear at all."""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, verdict="INSUFFICIENT_EVIDENCE"))

    assert not result.passed
    assert any("must not produce a change proposal" in v for v in result.violations)


def test_aspect_outside_whitelist_is_rejected():
    """Any change type outside the whitelist is rejected -- including ones that look harmless."""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, aspect="ownership"))

    assert not result.passed
    assert any("whitelist" in v for v in result.violations)


def test_editing_a_proposal_invalidates_the_old_approval():
    """Approval is bound to proposal_hash: change the content and the hash changes, so the old approval can't carry over."""
    store, ev = _store_with_one_evidence()
    original = _valid_proposal(ev)
    edited = _valid_proposal(ev, after_value=original.after_value + " (updated)")

    assert original.proposal_hash != edited.proposal_hash


def test_same_content_yields_same_hash():
    """Rebuilding the same proposal must yield the same hash, otherwise every approval breaks after a re-run."""
    store, ev = _store_with_one_evidence()
    assert _valid_proposal(ev).proposal_hash == _valid_proposal(ev).proposal_hash
