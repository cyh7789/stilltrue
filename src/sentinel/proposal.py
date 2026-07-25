"""Fix proposals and the Policy Gate.

Division of labour (SPEC 1.2, items 5-7): a proposal may come from a language
model, but **whether it can be written out is decided by plain code**. The gate
does not judge whether the proposal reads convincingly; it only checks
mechanically verifiable conditions. Any violation stops the proposal here.

What the gate deliberately does not cover — whether the new wording is
semantically correct — belongs to the steward's approval step. Keeping the
layers distinct is what stops this from becoming a pile of gates that look
impressive and block nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .evidence import EvidenceStore, canonical_hash

# Change types allowed to reach DataHub. Anything else is refused: a whitelist,
# not a blacklist, so new capabilities require a deliberate decision instead of
# being acquired through an oversight.
ALLOWED_ASPECTS = ("dataset_description", "field_description", "tag")

Verdict = Literal["DRIFT", "CURRENT", "INSUFFICIENT_EVIDENCE"]


@dataclass
class Proposal:
    entity_urn: str
    aspect: str
    verdict: Verdict
    subject: str                   # which field, or which piece of prose
    before_value: str
    after_value: str
    rationale: str
    evidence_ids: list[str] = field(default_factory=list)

    @property
    def before_hash(self) -> str:
        return canonical_hash({"urn": self.entity_urn, "aspect": self.aspect,
                               "subject": self.subject, "value": self.before_value})

    @property
    def proposal_hash(self) -> str:
        """Approvals bind to this value, so editing a proposal voids its approval."""
        return canonical_hash({
            "urn": self.entity_urn, "aspect": self.aspect, "subject": self.subject,
            "before": self.before_value, "after": self.after_value,
            "verdict": self.verdict, "evidence": sorted(self.evidence_ids),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_hash": self.proposal_hash,
            "entity_urn": self.entity_urn,
            "aspect": self.aspect,
            "subject": self.subject,
            "verdict": self.verdict,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "before_hash": self.before_hash,
            "rationale": self.rationale,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class GateResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


ApprovalStatus = Literal["APPROVED", "NOT_APPROVED", "STALE"]

# The CLI prints proposal_hash[:16]; approving with what was printed has to
# work. Shorter than that stops identifying a specific proposal.
MIN_APPROVAL_PREFIX = 16


@dataclass
class ApprovalDecision:
    authorised: bool
    status: ApprovalStatus
    detail: str


def check_approval(p: Proposal, approval: str | None) -> ApprovalDecision:
    """Second lock, after the Policy Gate: did a human approve *this* proposal?

    The gate checks a proposal is well formed. It cannot check anyone wants the
    change — that judgement is the steward's, and it is made against text they
    read. Binding the approval to `proposal_hash` is what makes "approve the
    benign version, then write something else" impossible: the text, the
    evidence and the verdict all feed the hash, so any edit produces a token
    that no longer matches.
    """
    if not approval:
        return ApprovalDecision(
            False, "NOT_APPROVED",
            f"no steward approval supplied; re-run with --approve {p.proposal_hash[:MIN_APPROVAL_PREFIX]}",
        )

    token = approval.strip().lower()
    if len(token) < MIN_APPROVAL_PREFIX or not p.proposal_hash.startswith(token):
        return ApprovalDecision(
            False, "STALE",
            f"approval `{approval}` does not match this proposal "
            f"({p.proposal_hash[:MIN_APPROVAL_PREFIX]}); it was edited after approval, or names another one",
        )

    return ApprovalDecision(True, "APPROVED", f"approved as {token}")


class PolicyGate:
    """Whether a proposal may enter the review queue is decided by these rules alone."""

    def __init__(self, evidence: EvidenceStore) -> None:
        self.evidence = evidence

    def check(self, p: Proposal) -> GateResult:
        v: list[str] = []

        if p.aspect not in ALLOWED_ASPECTS:
            v.append(f"aspect `{p.aspect}` is not in the whitelist {ALLOWED_ASPECTS}")

        if p.verdict != "DRIFT":
            # Only a drift verdict warrants changing anything; the other two
            # states must never produce a write.
            v.append(f"verdict is {p.verdict}, which must not produce a change proposal")

        if not p.evidence_ids:
            v.append("proposal cites no evidence")
        else:
            ok, missing = self.evidence.resolve_all(p.evidence_ids)
            if not ok:
                v.append(f"proposal cites evidence that does not exist: {missing}")

        if p.after_value.strip() == p.before_value.strip():
            v.append("before and after are identical, so this is not a change")

        if not p.after_value.strip():
            v.append("proposal would blank the content; deletion is out of scope for a fix")

        if not p.rationale.strip():
            v.append("proposal states no rationale")

        return GateResult(passed=not v, violations=v)
