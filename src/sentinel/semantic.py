"""D5 語意/glossary 漂移偵測 —— 全系統唯一允許 LLM 介入的類別（SPEC §2）。

要抓的失效模式（BRIEF §9.5，Pinterest 在 DataHub town hall 的案例）：
同一個商業指標在不同部門各有定義 —— finance 的日活與 marketing 的不一樣，
safety 先濾掉 bot 的那份數字又成了 marketing 的視角。單獨看每一份都對，
但兩個 agent 各引一份時，使用者拿到互相矛盾的答案，而且沒有任何錯誤訊號。

控制流分三段，LLM 被夾在兩道確定性閘之間：

1. 預篩（純函式）：term 掛 ≥2 個 entity、且過濾條件集合不同，才成為候選。
   條件相同的定義差異只是措辭問題，不是語意衝突，不值得花一次 LLM 呼叫。
2. 判讀（注入）：判讀器是注入的 Callable —— 本模組不 import 任何 SDK、
   不發任何網路請求，正式跑注入 LLM 判讀器，測試注入假的。
3. 引文閘（純函式）：判讀說衝突不足以成案 —— 兩側引文缺一、或引文
   對不上定義原文（LLM 幻覺引文的典型症狀），一律降級 INSUFFICIENT_EVIDENCE。
   棄權是合法輸出（SPEC 三態設計）；沒有證據的指控才是問題。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Protocol

from .detectors import Verdict


@dataclass(frozen=True)
class TermAttachment:
    """glossary term 掛在單一 entity 上的觀察 —— 預篩與判讀的最小輸入單位。

    filters 是上游已經解析好的 WHERE 條件字串清單；本模組不碰 SQL 解析，
    否則預篩就不再是可獨立測試的純函式。
    """

    entity_urn: str
    definition: str                     # 該 entity 上這個 term 的定義原文
    filters: tuple[str, ...]            # 對應欄位查詢的 WHERE 條件（已解析）
    evidence_ids: tuple[str, ...] = ()


def _normalized_filter_set(filters: tuple[str, ...]) -> frozenset[str]:
    """把條件清單化成可比較的集合。

    只做空白正規化與去重 —— 條件的順序和排版是查詢寫法的雜訊，不是語意。
    刻意不做大小寫正規化：字串字面值的大小寫可能有語意（'Bot' 與 'bot'
    可能是不同的標籤值），預篩寧可多放進判讀，也不能把真衝突濾掉。
    """
    return frozenset(re.sub(r"\s+", " ", f).strip() for f in filters if f.strip())


def prescreen(attachments: list[TermAttachment]) -> list[tuple[TermAttachment, TermAttachment]]:
    """確定性預篩：回傳值得送判讀的 entity 配對。

    term 只掛一個 entity 時沒有「兩套定義」可言；過濾條件集合相同時，
    定義文字再怎麼不同也只是措辭差異 —— 兩者都直接出局，不佔 LLM 額度。
    定義為空的一側註定過不了引文閘（沒有原文可引），先擋下來省一次呼叫。
    """
    if len(attachments) < 2:
        return []
    citable = [a for a in attachments if a.definition.strip()]
    return [
        (a, b)
        for a, b in combinations(citable, 2)
        if _normalized_filter_set(a.filters) != _normalized_filter_set(b.filters)
    ]


@dataclass(frozen=True)
class Judgment:
    """判讀器的回覆。引文欄位是強制的 —— 判讀器必須從各側定義原文逐字擷取。"""

    conflict: bool                      # 兩份定義是否構成語意衝突
    quote_a: str                        # 從 a 側定義擷取的引文（逐字）
    quote_b: str                        # 從 b 側定義擷取的引文（逐字）
    rationale: str = ""


class SemanticJudge(Protocol):
    """判讀器介面。正式跑注入 LLM 實作，測試注入假的。

    用 Protocol 而不是基底類別：呼叫端只依賴這個簽名，任何符合簽名的
    Callable（含測試裡的普通函式）都能注入，不必繼承任何東西。
    """

    def __call__(self, term: str, a: TermAttachment, b: TermAttachment) -> Judgment: ...


@dataclass
class SemanticFinding:
    """D5 的產出。不重用 detectors.Finding —— 它的 category 是封閉 Literal、

    claim/reality 是「人寫側 vs 現實側」的單向結構，而 D5 的衝突是對稱的：
    兩側都是人寫的定義，硬塞進去會丟失「哪份引文屬於哪個 entity」的對應。
    兩側的定義原文與過濾條件都完整入檔，steward 不用回頭查就能複驗。
    """

    term: str
    verdict: Verdict
    entity_a: str
    definition_a: str                   # a 側定義原文（引文閘的比對基準）
    filters_a: tuple[str, ...]
    entity_b: str
    definition_b: str
    filters_b: tuple[str, ...]
    quote_a: str | None = None
    quote_b: str | None = None
    rationale: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    category: str = "D5_SEMANTIC_DRIFT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "category": self.category,
            "verdict": self.verdict,
            "entity_a": self.entity_a,
            "definition_a": self.definition_a,
            "filters_a": list(self.filters_a),
            "entity_b": self.entity_b,
            "definition_b": self.definition_b,
            "filters_b": list(self.filters_b),
            "quote_a": self.quote_a,
            "quote_b": self.quote_b,
            "rationale": self.rationale,
            "evidence_ids": self.evidence_ids,
        }


def _quote_is_grounded(quote: str, definition: str) -> bool:
    """引文必須逐字出現在定義原文裡才算證據。

    LLM 產生「意思差不多但原文沒有」的引文是已知失效模式；
    對不上原文的引文再有說服力也不能進報告（SPEC §5 citation validity）。
    """
    return bool(quote.strip()) and quote.strip() in definition


def detect_semantic_drift(
    term: str,
    attachments: list[TermAttachment],
    judge: SemanticJudge,
) -> list[SemanticFinding]:
    """D5 主流程：預篩 → 注入的判讀器 → 引文閘。

    判讀說「衝突」但引文閘沒過 → 降級 INSUFFICIENT_EVIDENCE，不是丟棄：
    留下紀錄讓 steward 知道這一對曾被判為可疑，只是系統拿不出合格證據。
    判讀說「不衝突」→ 記一筆 CURRENT —— LLM 呼叫已經花了，結論要入帳，
    複跑時才能對照同一配對的判讀有沒有漂移。
    """
    findings: list[SemanticFinding] = []
    for a, b in prescreen(attachments):
        judgment = judge(term, a, b)
        evidence = list(a.evidence_ids) + list(b.evidence_ids)

        if not judgment.conflict:
            verdict: Verdict = "CURRENT"
        elif _quote_is_grounded(judgment.quote_a, a.definition) and _quote_is_grounded(
            judgment.quote_b, b.definition
        ):
            verdict = "DRIFT"
        else:
            verdict = "INSUFFICIENT_EVIDENCE"

        findings.append(
            SemanticFinding(
                term=term,
                verdict=verdict,
                entity_a=a.entity_urn,
                definition_a=a.definition,
                filters_a=a.filters,
                entity_b=b.entity_urn,
                definition_b=b.definition,
                filters_b=b.filters,
                quote_a=judgment.quote_a or None,
                quote_b=judgment.quote_b or None,
                rationale=judgment.rationale,
                evidence_ids=evidence,
            )
        )
    return findings
