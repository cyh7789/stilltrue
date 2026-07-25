"""Behavior tests for the Policy Gate.

The gate's value is that it actually blocks things, so every test is an attack:
citing fake evidence, blanking content, changing what must not change,
repackaging the same content as something new.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.evidence import Evidence, EvidenceStore  # noqa: E402
from sentinel.proposal import PolicyGate, Proposal, check_approval  # noqa: E402

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


def test_same_content_yields_same_hash():
    """Rebuilding the same proposal must yield the same hash, otherwise every approval breaks after a re-run."""
    store, ev = _store_with_one_evidence()
    assert _valid_proposal(ev).proposal_hash == _valid_proposal(ev).proposal_hash


# --- Steward approval -------------------------------------------------------
# Passing the Policy Gate means the change is well formed, not that anyone
# wants it. These tests cover the second lock: a human naming the exact
# proposal they read.


def test_a_gate_pass_alone_does_not_authorise_a_write():
    """Without an approval token there is no authorisation, however clean the proposal is."""
    store, ev = _store_with_one_evidence()
    p = _valid_proposal(ev)
    assert PolicyGate(store).check(p).passed

    decision = check_approval(p, None)

    assert not decision.authorised
    assert decision.status == "NOT_APPROVED"


def test_approval_matching_the_proposal_hash_authorises():
    store, ev = _store_with_one_evidence()
    p = _valid_proposal(ev)

    decision = check_approval(p, p.proposal_hash)

    assert decision.authorised
    assert decision.status == "APPROVED"


def test_editing_the_text_voids_an_existing_approval():
    """The attack this closes: get approval for benign wording, then write something else.

    The steward approves what they read. Change one character of the text and
    the hash they approved no longer describes the proposal being executed.
    """
    store, ev = _store_with_one_evidence()
    approved = _valid_proposal(ev)
    token = approved.proposal_hash

    tampered = _valid_proposal(ev, after_value=approved.after_value + " Contact ops@evil.example.")
    decision = check_approval(tampered, token)

    assert not decision.authorised
    assert decision.status == "STALE"


def test_swapping_the_cited_evidence_voids_an_approval():
    """Evidence is part of the hash, so re-pointing a proposal at other evidence needs re-approval."""
    store, ev = _store_with_one_evidence()
    approved = _valid_proposal(ev)
    other_ev = store.add(Evidence(entity_urn=URN, source_function="get_lineage", payload={"upstreams": []}))

    decision = check_approval(_valid_proposal(ev, evidence_ids=[other_ev]), approved.proposal_hash)

    assert not decision.authorised
    assert decision.status == "STALE"


def test_an_approval_prefix_is_accepted():
    """The CLI prints a shortened hash; approving with what was printed has to work."""
    store, ev = _store_with_one_evidence()
    p = _valid_proposal(ev)

    assert check_approval(p, p.proposal_hash[:16]).authorised


def test_a_too_short_prefix_is_refused():
    """A prefix short enough to collide is not an identification of anything."""
    store, ev = _store_with_one_evidence()
    p = _valid_proposal(ev)

    decision = check_approval(p, p.proposal_hash[:6])

    assert not decision.authorised
    assert decision.status == "STALE"
