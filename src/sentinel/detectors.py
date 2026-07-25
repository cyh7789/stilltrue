"""確定性漂移偵測器。

SPEC §2 的 D1–D4 全部是純程式判斷，不碰 LLM；只有 D5（語意漂移）需要判讀。
本模組是純函式：輸入兩側訊號，輸出 Finding。沒有 IO，可單獨測試。

「人寫側」= description / glossary / 文件裡的主張
「現實側」= schema、lineage、查詢紀錄的實際狀態
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

DriftCategory = Literal[
    "D1_SCHEMA_BREAK",      # 描述引用的欄位已不存在
    "D1_UNDOCUMENTED",      # 欄位存在但沒有描述
    "D3_LINEAGE_DRIFT",     # 描述宣稱的來源不在實際上游
]

Verdict = Literal["DRIFT", "CURRENT", "INSUFFICIENT_EVIDENCE"]


@dataclass
class Finding:
    entity_urn: str
    category: DriftCategory
    verdict: Verdict
    subject: str              # 出問題的欄位名或主張
    claim: str                # 人寫側說了什麼
    reality: str              # 現實側是什麼
    evidence_ids: list[str] = field(default_factory=list)
    suspected_rename: str | None = None   # D1 專用：疑似被改成哪個名字
    confidence: Literal["high", "medium"] = "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_urn": self.entity_urn,
            "category": self.category,
            "verdict": self.verdict,
            "subject": self.subject,
            "claim": self.claim,
            "reality": self.reality,
            "evidence_ids": self.evidence_ids,
            "suspected_rename": self.suspected_rename,
            "confidence": self.confidence,
        }


def referenced_identifiers(text: str) -> set[str]:
    """抽出描述文字裡指涉的欄位名。

    兩種寫法都算：反引號包起來的 `col_name`，以及 snake_case 的裸識別碼。
    裸識別碼要求含底線，避免把普通英文單字誤判成欄位名。
    """
    if not text:
        return set()
    backticked = set(re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", text))
    # 裸識別碼允許大小寫混寫（Airport_fee 這種），但仍要求含底線
    bare_snake = set(re.findall(r"\b([a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)\b", text))
    # 原樣回傳 —— 大小寫本身就是漂移訊號（TLC: airport_fee → Airport_fee），
    # 在這裡 lower() 會把要抓的東西抹掉
    return backticked | bare_snake


# 識別碼後面緊跟這些詞時，作者已經講明它不是欄位
NON_FIELD_QUALIFIERS = ("schema", "table", "database", "dataset", "model", "view", "catalog", "warehouse")


def qualified_as_non_field(text: str, identifier: str) -> bool:
    """描述是否自己講明了這個識別碼不是欄位，例如「`order_entry` schema」。"""
    pattern = rf"`?{re.escape(identifier)}`?\s+({'|'.join(NON_FIELD_QUALIFIERS)})\b"
    return re.search(pattern, text, flags=re.I) is not None


def self_reference_tokens(entity_urn: str) -> set[str]:
    """抽出 URN 裡屬於「這張表自己」的名稱片段（平台、資料庫、schema、表名）。

    描述裡提到自己的表名或所屬資料庫是正常寫法，不是欄位引用。
    不排除的話，`order_entry_db.order_entry.order_details` 會被誤判成三個不存在的欄位。
    """
    inner = re.search(r",([^,]+),[A-Z]+\)$", entity_urn)
    if not inner:
        return set()
    parts = inner.group(1).split(".")
    return {p.lower() for p in parts} | {p for p in parts}


def _rename_candidate(missing: str, actual: set[str]) -> str | None:
    """找出 missing 疑似被改成哪一個實際欄位。

    只認兩種機械可判定的改名：大小寫變動、以及底線位置不同的同字母序列。
    這一條直接對應 NYC TLC 的 airport_fee → Airport_fee 事件。
    """
    lowered = {a.lower(): a for a in actual}
    if missing.lower() in lowered:
        return lowered[missing.lower()]
    squashed = {a.lower().replace("_", ""): a for a in actual}
    key = missing.lower().replace("_", "")
    return squashed.get(key)


def detect_schema_break(
    entity_urn: str,
    entity_description: str,
    fields: list[dict],
    evidence_ids: list[str],
) -> list[Finding]:
    """D1：描述引用的欄位是否還存在；欄位是否沒有描述。

    fields 為 list_schema_fields 回傳的欄位清單，每筆含 fieldPath 與 description。
    """
    actual = {f.get("fieldPath", "") for f in fields if f.get("fieldPath")}
    self_tokens = self_reference_tokens(entity_urn)
    findings: list[Finding] = []

    # 人寫側的每一處欄位引用，都要在現實側找得到
    sources = [("dataset description", entity_description)]
    sources += [
        (f'field "{f.get("fieldPath")}" description', f.get("description") or "")
        for f in fields
    ]

    for where, text in sources:
        for ref in referenced_identifiers(text):
            if ref in actual:   # 精確比對：大小寫不同就是不同的欄位名
                continue
            if ref in self_tokens or ref.lower() in self_tokens:
                continue        # 指的是這張表自己或它的資料庫/schema，不是欄位
            if qualified_as_non_field(text, ref):
                continue        # 描述自己寫了「`x` schema」這種限定詞
            candidate = _rename_candidate(ref, actual)
            explicit = f"`{ref}`" in text   # 反引號包起來 = 作者明確指涉一個識別碼

            if candidate:
                # 存在大小寫／底線變體 —— 強訊號（TLC: airport_fee → Airport_fee）
                verdict, confidence = "DRIFT", "high"
                reality = f"目前 schema 沒有 `{ref}`，但存在 `{candidate}`"
            elif explicit:
                verdict, confidence = "DRIFT", "medium"
                reality = f"目前 schema 沒有 `{ref}`（共 {len(actual)} 個欄位）"
            else:
                # 裸寫的 snake_case 可能是別張表、schema 名或業務術語 —— 不當漂移報，
                # 但保留紀錄供人工查看。棄權是合法輸出，亂報不是。
                verdict, confidence = "INSUFFICIENT_EVIDENCE", "medium"
                reality = f"描述提到 `{ref}`，但它不是本表欄位，也找不到相近的欄位名"

            findings.append(
                Finding(
                    entity_urn=entity_urn,
                    category="D1_SCHEMA_BREAK",
                    verdict=verdict,
                    subject=ref,
                    claim=f"{where} 引用了 `{ref}`",
                    reality=reality,
                    evidence_ids=list(evidence_ids),
                    suspected_rename=candidate,
                    confidence=confidence,
                )
            )

    # 現實側存在、人寫側完全沒交代的欄位
    for f in fields:
        path = f.get("fieldPath")
        if path and not (f.get("description") or "").strip():
            findings.append(
                Finding(
                    entity_urn=entity_urn,
                    category="D1_UNDOCUMENTED",
                    verdict="DRIFT",
                    subject=path,
                    claim="無描述",
                    reality=f"欄位 `{path}`（{f.get('nativeDataType', '型別未知')}）存在於 schema 但沒有任何說明",
                    evidence_ids=list(evidence_ids),
                )
            )

    return findings


def detect_lineage_drift(
    entity_urn: str,
    entity_description: str,
    upstream_urns: list[str],
    evidence_ids: list[str],
) -> list[Finding]:
    """D3：描述宣稱的來源表，是否還在實際上游集合裡。"""
    claims = re.findall(
        r"(?:derived from|source[sd]?(?:\s+from)?|built from|based on)\s+`?([a-zA-Z_][\w.]*)`?",
        entity_description or "",
        flags=re.I,
    )
    if not claims:
        return []

    upstream_names = {u.lower() for u in upstream_urns}
    findings = []
    for claimed in {c.lower() for c in claims}:
        if any(claimed in u for u in upstream_names):
            continue
        findings.append(
            Finding(
                entity_urn=entity_urn,
                category="D3_LINEAGE_DRIFT",
                verdict="DRIFT",
                subject=claimed,
                claim=f"描述宣稱資料來自 `{claimed}`",
                reality=f"實際上游有 {len(upstream_urns)} 個，都不是 `{claimed}`",
                evidence_ids=list(evidence_ids),
                confidence="medium",
            )
        )
    return findings
