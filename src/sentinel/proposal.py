"""修正提案與 Policy Gate。

分工（SPEC §1.2 第 5–7 條）：提案可以由 LLM 產生，但**能不能寫出去由純程式決定**。
Gate 不看提案講得多有道理，只驗證可機械檢查的條件；任何一條不過就停在這裡。

Gate 擋不住的東西（例如提案內容在語意上是否正確）不歸它管，
那是 steward 核准階段的事 —— 分層清楚才不會出現「閘門看起來很多、其實都沒在擋」。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .evidence import EvidenceStore, canonical_hash

# 允許寫回 DataHub 的變更類型。不在此列的一律拒絕 —— 白名單而非黑名單，
# 新增能力必須是明確決定，不能靠遺漏獲得。
ALLOWED_ASPECTS = ("dataset_description", "field_description", "tag")

Verdict = Literal["DRIFT", "CURRENT", "INSUFFICIENT_EVIDENCE"]


@dataclass
class Proposal:
    entity_urn: str
    aspect: str
    verdict: Verdict
    subject: str                   # 針對哪個欄位／哪段描述
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
        """核准是綁在這個值上的。內容一改，舊核准自動失效。"""
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


class PolicyGate:
    """提案能不能進入待審佇列，由這裡的純程式規則決定。"""

    def __init__(self, evidence: EvidenceStore) -> None:
        self.evidence = evidence

    def check(self, p: Proposal) -> GateResult:
        v: list[str] = []

        if p.aspect not in ALLOWED_ASPECTS:
            v.append(f"aspect `{p.aspect}` 不在白名單 {ALLOWED_ASPECTS}")

        if p.verdict != "DRIFT":
            # 只有判定為漂移才需要改東西；其餘兩態不該產生寫入提案
            v.append(f"verdict 為 {p.verdict}，不應產生變更提案")

        if not p.evidence_ids:
            v.append("提案沒有引用任何證據")
        else:
            ok, missing = self.evidence.resolve_all(p.evidence_ids)
            if not ok:
                v.append(f"引用了不存在的證據: {missing}")

        if p.after_value.strip() == p.before_value.strip():
            v.append("修改前後內容相同，不構成變更")

        if not p.after_value.strip():
            v.append("提案要把內容清空 —— 刪除不在允許的修正範圍內")

        if not p.rationale.strip():
            v.append("提案沒有說明理由")

        return GateResult(passed=not v, violations=v)
