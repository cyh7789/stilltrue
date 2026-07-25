"""Evidence records — every claim this system makes must point back to one of these.

Design constraints (SPEC 1.2, items 2 and 5):
- each record captures which read-only function produced it, when, and for which URN
- payloads are hashed over canonical JSON so anyone can re-check the captured
  content was not edited afterwards
- evidence_id is content-derived rather than random, so a re-run produces the
  same ids and existing citations stay valid
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

# The only functions the read-only adapter is allowed to expose (SPEC 1.2 item 2).
# Mutation tools are deliberately absent from this list.
SourceFunction = Literal[
    "search",
    "get_entities",
    "search_documents",
    "grep_documents",
    "list_schema_fields",
    "get_lineage",
    "get_dataset_queries",
]


def canonical_hash(payload: Any) -> str:
    """sha256 over canonical JSON.

    sort_keys makes dict ordering irrelevant and the compact separators strip
    incidental whitespace, so the same observation hashes identically anywhere.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Evidence:
    entity_urn: str
    source_function: SourceFunction
    payload: Any
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def payload_hash(self) -> str:
        return canonical_hash(self.payload)

    @property
    def evidence_id(self) -> str:
        """Content-addressed: same URN + function + payload always yields the same id.

        captured_at is deliberately excluded. Re-reading the same fact should not
        mint a new piece of evidence, otherwise every citation in every proposal
        would break on the next run.
        """
        return "ev_" + canonical_hash(
            {"urn": self.entity_urn, "fn": self.source_function, "payload": self.payload}
        )[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "entity_urn": self.entity_urn,
            "source_function": self.source_function,
            "captured_at": self.captured_at,
            "payload_hash": self.payload_hash,
            "payload": self.payload,
        }


class EvidenceStore:
    """Everything observed during one scan. Append-only; entries are never overwritten."""

    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    def add(self, ev: Evidence) -> str:
        existing = self._items.get(ev.evidence_id)
        if existing is not None and existing.payload_hash != ev.payload_hash:
            raise ValueError(f"evidence_id collision with differing content: {ev.evidence_id}")
        self._items.setdefault(ev.evidence_id, ev)
        return ev.evidence_id

    def get(self, evidence_id: str) -> Evidence | None:
        return self._items.get(evidence_id)

    def hydrate(self, rows: list[dict[str, Any]]) -> int:
        """Reload evidence persisted by an earlier command.

        A proposal produced by `scan` cites ids from that run's store. Without
        this, `apply` starts with an empty store and the Policy Gate correctly
        refuses every proposal for citing evidence it cannot see. Ids are
        content-derived, so a rebuilt record lands on the same id.
        """
        loaded = 0
        for row in rows:
            self.add(Evidence(
                entity_urn=row["entity_urn"],
                source_function=row["source_function"],
                payload=row["payload"],
                captured_at=row.get("captured_at", ""),
            ))
            loaded += 1
        return loaded

    def resolve_all(self, evidence_ids: list[str]) -> tuple[bool, list[str]]:
        """Check a set of citations. Returns (all_resolved, missing_ids).

        The Policy Gate uses this to reject proposals citing evidence that does
        not exist — the most common way a language model fakes its homework.
        """
        missing = [i for i in evidence_ids if i not in self._items]
        return (not missing, missing)

    def __len__(self) -> int:
        return len(self._items)

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._items.values()]
