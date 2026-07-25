"""Behavior tests for the hash-chained audit ledger.

Each test simulates a real tampering technique: rewrite the JSONL file directly,
then run verify(). What's tested is the behavior "tampering gets caught and the
position is reported correctly" -- break any of verify's checks and the matching
test goes red; renaming things won't.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.evidence import canonical_hash  # noqa: E402
from sentinel.ledger import AuditLedger  # noqa: E402

URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"


def _build_ledger(path: Path, n: int = 5) -> AuditLedger:
    led = AuditLedger(path)
    for i in range(n):
        led.append(stage="detect", run_id="run-1", entity_urn=URN, payload={"seq": i})
    return led


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_intact_chain_verifies(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    ok, msg = led.verify()

    assert ok
    assert "5" in msg


def test_empty_ledger_is_valid(tmp_path: Path) -> None:
    """A ledger whose file doesn't exist yet counts as valid -- running verify before the first scan must not fail."""
    led = AuditLedger(tmp_path / "audit.jsonl")

    ok, _ = led.verify()

    assert ok


def test_content_tamper_is_caught_at_position(tmp_path: Path) -> None:
    """Edit one payload without recomputing the hash -- the most direct tampering technique."""
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    entry = json.loads(lines[2])
    entry["payload"] = {"seq": 999}
    lines[2] = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    assert "record 3" in msg


def test_recomputed_hash_tamper_is_still_caught(tmp_path: Path) -> None:
    """The tamperer recomputes entry_hash as well -- the next entry's prev_hash still catches it.

    This blocks the lazy implementation where verify only recomputes per-entry hashes without following the chain.
    """
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    entry = json.loads(lines[2])
    entry["payload"] = {"seq": 999}
    del entry["entry_hash"]
    entry["entry_hash"] = canonical_hash(entry)
    lines[2] = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    assert "record 4" in msg


def test_deleted_middle_entry_is_caught(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    del lines[2]
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    # the original 4th entry shifts up to line 3; its prev_hash points at the deleted entry → the chain breaks here
    assert "record 3" in msg


def test_swapped_entries_are_caught(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    lines[1], lines[2] = lines[2], lines[1]
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    assert "record 2" in msg


def test_reopened_ledger_continues_chain(tmp_path: Path) -> None:
    """A new run must append to the existing chain tail -- if reopening started a fresh chain, every later record would break the chain."""
    path = tmp_path / "audit.jsonl"
    _build_ledger(path, n=2)

    led2 = AuditLedger(path)
    led2.append(stage="write", run_id="run-2", entity_urn=URN, payload={"seq": 99})

    ok, msg = led2.verify()
    assert ok
    assert "3" in msg
