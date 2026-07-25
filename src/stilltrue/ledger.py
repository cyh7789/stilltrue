"""Hash-chained audit ledger: every stage leaves a verifiable trace (SPEC 4).

Design constraints:
- append-only JSONL, one record per line, never edited in place. Tamper
  detection comes from the chain itself rather than file permissions, since
  anyone with write access can already work around permissions.
- each record's prev_hash points at the previous entry_hash, with genesis
  pointing at a fixed string, so edited content, deleted records and reordered
  records all break the chain somewhere.
- pure file IO, no DataHub. The ledger is the last line of defence and must not
  depend on any component it audits.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import canonical_hash

# Fixed genesis prev_hash, so replacing the very first record is still detectable
GENESIS_HASH = "genesis"


class AuditLedger:
    """Append-only audit ledger. One instance maps to one JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        # Reopening must continue from the existing tail rather than starting a
        # new chain, otherwise ordering and integrity break across runs.
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._path.exists():
            return GENESIS_HASH
        last = GENESIS_HASH
        with self._path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line:
                    last = json.loads(line)["entry_hash"]
        return last

    def append(self, stage: str, run_id: str, entity_urn: str, payload: Any) -> dict[str, Any]:
        """Append one record and return it, entry_hash included."""
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": run_id,
            "stage": stage,
            "entity_urn": entity_urn,
            "payload": payload,
            "prev_hash": self._last_hash,
        }
        # entry_hash covers prev_hash and every field: change any one of them
        # and this record's hash stops matching. Including prev_hash is what
        # makes the ordering itself immutable.
        entry["entry_hash"] = canonical_hash(entry)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        self._last_hash = entry["entry_hash"]
        return entry

    def verify(self) -> tuple[bool, str]:
        """Re-read the whole file and verify the chain. Returns (ok, detail).

        Two checks per record, reporting the first failure by 1-based line:
        1. recompute entry_hash, catching content edited without rehashing
        2. prev_hash must equal the previous entry_hash, catching deletions and
           reordering. Content edited *with* a recomputed hash also breaks here,
           on the following record.
        """
        if not self._path.exists():
            return (True, "empty ledger, chain valid (0 records)")

        expected_prev = GENESIS_HASH
        count = 0
        with self._path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line:
                    continue
                count += 1
                try:
                    entry: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    return (False, f"record {lineno} is not valid JSON")

                stored_hash = entry.get("entry_hash")
                body = {k: v for k, v in entry.items() if k != "entry_hash"}
                if canonical_hash(body) != stored_hash:
                    return (False, f"record {lineno} does not match its entry_hash: content was tampered with")
                if entry.get("prev_hash") != expected_prev:
                    return (False, f"record {lineno} breaks the prev_hash chain: a record was deleted or reordered")
                expected_prev = str(stored_hash)

        return (True, f"chain valid ({count} records)")
