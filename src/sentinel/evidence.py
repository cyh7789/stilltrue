"""證據紀錄 — 系統對外的每一句主張都必須指回這裡的一筆 evidence_id。

設計約束（SPEC §1.2 第 2、5 條）：
- 每筆證據記錄它是「哪個唯讀 function、什麼時候、對哪個 URN」取得的
- payload 以 canonical JSON 算 hash，供事後複驗抓取內容有沒有被改過
- evidence_id 由內容決定（同樣的觀察 → 同樣的 id），不用隨機值，重跑可比對
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

# 唯讀 adapter 允許暴露的 function（SPEC §1.2 第 2 條；寫入能力不在此列）
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
    """對 payload 取 canonical JSON 後的 sha256。

    sort_keys 讓 dict 順序不影響 hash；separators 去掉多餘空白，
    確保同一份觀察在不同機器上算出同一個值。
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
        """內容定址：同一個 URN + function + payload 永遠得到同一個 id。

        captured_at 刻意不進 id —— 同一份事實重抓一次不該變成新證據，
        否則 proposal 的引用會在每次重跑後全部失效。
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
    """一次 scan 期間蒐集到的所有證據。append-only，不允許覆寫。"""

    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    def add(self, ev: Evidence) -> str:
        existing = self._items.get(ev.evidence_id)
        if existing is not None and existing.payload_hash != ev.payload_hash:
            raise ValueError(f"evidence_id 碰撞但內容不同: {ev.evidence_id}")
        self._items.setdefault(ev.evidence_id, ev)
        return ev.evidence_id

    def get(self, evidence_id: str) -> Evidence | None:
        return self._items.get(evidence_id)

    def resolve_all(self, evidence_ids: list[str]) -> tuple[bool, list[str]]:
        """檢查一組引用是否全部存在。回傳 (是否全中, 找不到的 id)。

        Policy Gate 用它擋掉引用了不存在證據的 proposal。
        """
        missing = [i for i in evidence_ids if i not in self._items]
        return (not missing, missing)

    def __len__(self) -> int:
        return len(self._items)

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._items.values()]
