"""Behavior tests for the Write Executor.

One test per protection, using an injected reader to simulate what actually
happens: someone else changed it first, the script got re-run, the API said
success but the value never landed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stilltrue.executor import WriteExecutor  # noqa: E402
from stilltrue.proposal import Proposal  # noqa: E402

URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"
BEFORE = "Fare breakdown includes airport_fee for LGA/JFK pickups."
AFTER = "Fare breakdown includes Airport_fee for LGA/JFK pickups."


def _proposal() -> Proposal:
    return Proposal(
        entity_urn=URN, aspect="dataset_description", verdict="DRIFT", subject="description",
        before_value=BEFORE, after_value=AFTER,
        rationale="the schema field is named Airport_fee.", evidence_ids=["ev_1"],
    )


def test_dry_run_verifies_without_writing():
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=True)
    assert ex.execute(p, p.proposal_hash).status == "VERIFIED"


def test_conflict_when_someone_changed_it_first():
    """Between proposal generation and approval someone else already changed the same description -- must not overwrite it."""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: "someone else rewrote this", dry_run=True)
    r = ex.execute(p, p.proposal_hash)

    assert r.status == "CONFLICT"
    assert "nothing written" in r.detail


def test_second_run_is_idempotent():
    """Re-running the script must not apply the same change twice."""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=True)

    assert ex.execute(p, p.proposal_hash).status == "VERIFIED"
    assert ex.execute(p, p.proposal_hash).status == "DUPLICATE"


def test_approval_hash_must_match_proposal_content():
    """Content edited after approval -- the old approval must not execute the new content."""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=True)
    r = ex.execute(p, "approved_hash_of_a_different_version")

    assert r.status == "FAILED"
    assert "approval" in r.detail


def test_readback_mismatch_does_not_auto_retry():
    """API reports success but the value never landed: mark VERIFY_FAILED, hand it to a human, no self-retry."""
    p = _proposal()
    calls = {"n": 0}

    def reader(_):
        calls["n"] += 1
        return BEFORE   # readback after the write still shows the old value -- the write never landed

    ex = WriteExecutor(reader=reader, dry_run=False)
    ex._write = lambda _p: None   # pretend the API call succeeded
    r = ex.execute(p, p.proposal_hash)

    assert r.status == "VERIFY_FAILED"
    assert calls["n"] == 2        # once before the write, once after, no third retry


def test_write_failure_is_recorded_not_raised():
    """When the call blows up, leave a receipt instead of raising and aborting the whole batch."""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=False)

    def boom(_p):
        raise ConnectionError("gms unreachable")

    ex._write = boom
    r = ex.execute(p, p.proposal_hash)

    assert r.status == "FAILED"
    assert "ConnectionError" in r.detail


def _removal() -> Proposal:
    return Proposal(
        entity_urn=URN, aspect="field_description_removal", verdict="DRIFT",
        subject="airport_fee",
        before_value="Only charged on LGA and JFK pickups.", after_value="",
        rationale="the schema has no airport_fee; this note is attached to nothing.",
        evidence_ids=["ev_1"],
    )


def test_a_removal_is_refused_while_the_field_is_still_in_the_schema():
    """The guard that makes the gate's exemption safe.

    Between the scan and the confirmation someone may have re-added the column --
    a rollback, a re-run of the pipeline that dropped it. Then the description is
    not orphaned any more and removing it would delete a live field's
    documentation, which is the thing the gate refuses everywhere else.
    """
    p = _removal()
    ex = WriteExecutor(reader=lambda _: p.before_value, server="http://x",
                       schema_reader=lambda _: {"airport_fee", "fare_amount"})
    receipt = ex.execute(p, p.proposal_hash)

    assert receipt.status == "CONFLICT"
    assert "airport_fee" in receipt.detail


def test_a_removal_proceeds_once_the_field_is_really_gone():
    p = _removal()
    ex = WriteExecutor(reader=lambda _: p.before_value, server="http://x",
                       schema_reader=lambda _: {"Airport_fee", "fare_amount"},
                       dry_run=True)

    assert ex.execute(p, p.proposal_hash).status == "VERIFIED"


def test_a_removal_refuses_when_the_schema_could_not_be_read_in_full():
    """A short read is not an empty schema.

    list_schema_fields pages, and stops early on a token budget as well as a
    limit. A field left out of a partial page is indistinguishable from one the
    schema does not have -- which is exactly the question this guard asks.
    Measured on a 120-column dataset: 100 returned, 20 remaining, and a live
    documented column read as an orphan.
    """
    p = _removal()
    ex = WriteExecutor(reader=lambda _: p.before_value, server="http://x",
                       schema_reader=lambda _: None)
    receipt = ex.execute(p, p.proposal_hash)

    assert receipt.status == "CONFLICT"
    assert "in full" in receipt.detail


def test_a_removal_without_a_schema_reader_fails_rather_than_writing():
    """The gate's exemption is justified by this check, so it must happen."""
    p = _removal()
    ex = WriteExecutor(reader=lambda _: p.before_value, server="http://x")

    assert ex.execute(p, p.proposal_hash).status == "FAILED"
