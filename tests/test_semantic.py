"""D5 語意漂移偵測器的行為測試。

判讀器一律用注入的假貨 —— 測的是本模組的控制流與引文閘，
不是任何 LLM 的判讀品質。把預篩或引文閘弄壞，這些會紅；只改名字不會。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.semantic import (  # noqa: E402
    Judgment,
    TermAttachment,
    detect_semantic_drift,
)

# Pinterest 案例的最小重現：同一個 DAU term，marketing 側先濾掉 bot
FINANCE = TermAttachment(
    entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,finance.dau_daily,PROD)",
    definition="Daily active users: all accounts with at least one session per day.",
    filters=("event_date = CURRENT_DATE", "session_count >= 1"),
    evidence_ids=("ev_fin",),
)
MARKETING = TermAttachment(
    entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,marketing.dau_daily,PROD)",
    definition="Daily active users, excluding accounts flagged as bots by safety.",
    filters=("event_date = CURRENT_DATE", "session_count >= 1", "is_bot = false"),
    evidence_ids=("ev_mkt",),
)


class RecordingJudge:
    """記錄每次被呼叫的配對，回傳預先設定的判讀結果。"""

    def __init__(self, judgment: Judgment) -> None:
        self.judgment = judgment
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, term: str, a: TermAttachment, b: TermAttachment) -> Judgment:
        self.calls.append((term, a.entity_urn, b.entity_urn))
        return self.judgment


def _conflict_with_valid_quotes() -> Judgment:
    """引文逐字取自上面兩份定義 —— 引文閘應該放行的合格判讀。"""
    return Judgment(
        conflict=True,
        quote_a="all accounts with at least one session",
        quote_b="excluding accounts flagged as bots",
        rationale="一側含 bot 一側排除，同名指標分母不同",
    )


def test_single_entity_never_triggers():
    """term 只掛一個 entity 時沒有第二份定義可衝突，判讀器一次都不能被呼叫。"""
    judge = RecordingJudge(_conflict_with_valid_quotes())
    assert detect_semantic_drift("DAU", [FINANCE], judge) == []
    assert judge.calls == []


def test_identical_filters_never_reach_judge():
    """過濾條件相同代表兩側看的是同一個母體，措辭差異不是語意衝突。

    順序與排版不同仍算相同 —— 那是查詢寫法的雜訊，送判讀就是浪費 LLM 額度。
    """
    same_population = TermAttachment(
        entity_urn="urn:li:dataset:(urn:li:dataPlatform:hive,growth.dau_daily,PROD)",
        definition="Count of users active on a given day.",
        filters=("session_count >= 1", "event_date  =  CURRENT_DATE"),
        evidence_ids=("ev_growth",),
    )
    judge = RecordingJudge(_conflict_with_valid_quotes())
    assert detect_semantic_drift("DAU", [FINANCE, same_population], judge) == []
    assert judge.calls == []


def test_differing_filters_are_sent_to_judge_exactly_once():
    """條件集合不同的配對才進判讀，且同一對只判一次。"""
    judge = RecordingJudge(_conflict_with_valid_quotes())
    detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert judge.calls == [("DAU", FINANCE.entity_urn, MARKETING.entity_urn)]


def test_conflict_with_both_quotes_yields_drift_carrying_both_sides():
    """判讀說衝突且兩側引文合格 → DRIFT，且兩側定義原文與過濾條件都要入檔。

    steward 複驗時只能看 finding 本身 —— 缺任何一側的原文，複驗閘就是虛設。
    """
    judge = RecordingJudge(_conflict_with_valid_quotes())
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert len(findings) == 1
    f = findings[0]
    assert f.verdict == "DRIFT"
    assert f.definition_a == FINANCE.definition
    assert f.filters_a == FINANCE.filters
    assert f.definition_b == MARKETING.definition
    assert f.filters_b == MARKETING.filters
    assert sorted(f.evidence_ids) == ["ev_fin", "ev_mkt"]


def test_missing_quote_downgrades_to_insufficient_evidence():
    """判讀說衝突但缺一側引文 → 降級棄權，不是 DRIFT 也不是丟棄。"""
    judge = RecordingJudge(
        Judgment(conflict=True, quote_a="all accounts with at least one session", quote_b="")
    )
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert [f.verdict for f in findings] == ["INSUFFICIENT_EVIDENCE"]


def test_hallucinated_quote_downgrades_to_insufficient_evidence():
    """引文兩側都有、但其中一側對不上定義原文 → 一樣降級。

    「意思差不多但原文沒有」是 LLM 引文的已知失效模式，
    對不上原文的引文不是證據（SPEC §5 citation validity）。
    """
    judge = RecordingJudge(
        Judgment(
            conflict=True,
            quote_a="all accounts with at least one session",
            quote_b="bots are removed before counting",  # 定義原文裡沒有這句
        )
    )
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert [f.verdict for f in findings] == ["INSUFFICIENT_EVIDENCE"]


def test_judge_says_consistent_records_current():
    """判讀說不衝突 → 記 CURRENT 入帳，複跑時才能比對同一配對的判讀有沒有漂移。"""
    judge = RecordingJudge(Judgment(conflict=False, quote_a="", quote_b=""))
    findings = detect_semantic_drift("DAU", [FINANCE, MARKETING], judge)

    assert [f.verdict for f in findings] == ["CURRENT"]
