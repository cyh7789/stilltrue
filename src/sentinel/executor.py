"""Write executor: the only place that mutates DataHub.

Split of duties with the adapter (SPEC 1.2, items 2 and 9-12): the adapter only
reads and holds a read-only credential; the executor only writes after an
approval, and re-reads both before and after. Who produced the proposal makes
no difference here. No approval, or an approval that does not match the
content, means no write.

Three guards, each for something that genuinely happens:
- re-read before write: between proposal and approval, someone else may have
  edited the same field (TOCTOU)
- idempotency key: re-running a script or retrying a network failure must not
  apply the same change twice
- read-back after write: a 200 response does not mean the value landed
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from .evidence import canonical_hash
from .proposal import Proposal

warnings.filterwarnings("ignore", category=UserWarning)

ExecutionStatus = Literal[
    "VERIFIED",        # written and confirmed by read-back
    "CONFLICT",        # current value no longer matches the proposal baseline; nothing written
    "DUPLICATE",       # this idempotency key already ran; not applied again
    "VERIFY_FAILED",   # read-back disagrees; never auto-retried, handed to a human
    "FAILED",          # the call itself failed
]


@dataclass
class Receipt:
    idempotency_key: str
    proposal_hash: str
    entity_urn: str
    status: ExecutionStatus
    detail: str
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "idempotency_key": self.idempotency_key,
            "proposal_hash": self.proposal_hash,
            "entity_urn": self.entity_urn,
            "status": self.status,
            "detail": self.detail,
            "executed_at": self.executed_at,
        }


def idempotency_key(p: Proposal) -> str:
    """The same (entity, aspect, subject, proposal content) must apply only once."""
    return canonical_hash({
        "urn": p.entity_urn, "aspect": p.aspect,
        "subject": p.subject, "proposal": p.proposal_hash,
    })


class WriteExecutor:
    """Write an approved proposal back to DataHub.

    `reader` is injected rather than built in: it re-reads the current value, so
    the before/after checks can run against a fake in tests, and the executor
    never needs to know how that value is fetched.
    """

    def __init__(
        self,
        reader: Callable[[Proposal], str],
        server: str = "http://localhost:8080",
        token: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self.reader = reader
        self.server = server
        self.token = token
        self.dry_run = dry_run
        self._receipts: dict[str, Receipt] = {}

    def execute(self, p: Proposal, approved_hash: str) -> Receipt:
        key = idempotency_key(p)

        if approved_hash != p.proposal_hash:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "FAILED",
                                        "approved proposal_hash does not match the content; the proposal may have been edited after approval"))

        prior = self._receipts.get(key)
        if prior is not None and prior.status in ("VERIFIED", "DUPLICATE"):
            return Receipt(key, p.proposal_hash, p.entity_urn, "DUPLICATE",
                           f"already applied at {prior.executed_at}; not written again")

        current = self.reader(p)
        if canonical_hash({"urn": p.entity_urn, "aspect": p.aspect,
                           "subject": p.subject, "value": current}) != p.before_hash:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "CONFLICT",
                                        "re-read before write shows the current value no longer matches the proposal baseline; nothing written"))

        if self.dry_run:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "VERIFIED",
                                        "dry run: nothing written"))

        try:
            self._write(p)
        except Exception as exc:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "FAILED",
                                        f"{type(exc).__name__}: {exc}"))

        after = self.reader(p)
        if after.strip() != p.after_value.strip():
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "VERIFY_FAILED",
                                        "read-back after write disagrees with the proposal; not retried automatically, needs a human"))

        return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "VERIFIED",
                                    "written and confirmed by read-back"))

    def _write(self, p: Proposal) -> None:
        """The actual DataHub call. Exactly one whitelisted change per invocation."""
        from datahub.sdk import DataHubClient
        from datahub_agent_context import DataHubContext
        from datahub_agent_context.mcp_tools import descriptions

        client = DataHubClient(server=self.server, token=self.token)
        with DataHubContext(client):
            if p.aspect == "dataset_description":
                descriptions.update_description(
                    entity_urn=p.entity_urn, operation="replace", description=p.after_value
                )
            elif p.aspect == "field_description":
                descriptions.update_description(
                    entity_urn=p.entity_urn, operation="replace",
                    description=p.after_value, column_path=p.subject,
                )
            else:
                raise ValueError(f"executor does not support aspect: {p.aspect}")

    def _record(self, r: Receipt) -> Receipt:
        self._receipts[r.idempotency_key] = r
        return r
