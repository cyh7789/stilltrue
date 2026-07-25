"""Write Executor 的行為測試。

三個保護各測一遍，用注入的 reader 模擬真實會發生的狀況：
別人搶先改了、腳本被重跑、API 說成功但值沒進去。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.executor import WriteExecutor  # noqa: E402
from sentinel.proposal import Proposal  # noqa: E402

URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"
BEFORE = "Fare breakdown includes airport_fee for LGA/JFK pickups."
AFTER = "Fare breakdown includes Airport_fee for LGA/JFK pickups."


def _proposal() -> Proposal:
    return Proposal(
        entity_urn=URN, aspect="dataset_description", verdict="DRIFT", subject="description",
        before_value=BEFORE, after_value=AFTER,
        rationale="schema 欄位名為 Airport_fee。", evidence_ids=["ev_1"],
    )


def test_dry_run_verifies_without_writing():
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=True)
    assert ex.execute(p, p.proposal_hash).status == "VERIFIED"


def test_conflict_when_someone_changed_it_first():
    """從產生提案到核准之間，別人已經改過同一段描述 —— 不能覆蓋掉。"""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: "someone else rewrote this", dry_run=True)
    r = ex.execute(p, p.proposal_hash)

    assert r.status == "CONFLICT"
    assert "未寫入" in r.detail


def test_second_run_is_idempotent():
    """重跑腳本不該把同一個變更套用兩次。"""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=True)

    assert ex.execute(p, p.proposal_hash).status == "VERIFIED"
    assert ex.execute(p, p.proposal_hash).status == "DUPLICATE"


def test_approval_hash_must_match_proposal_content():
    """核准後又改內容 —— 舊核准不能拿來執行新內容。"""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=True)
    r = ex.execute(p, "approved_hash_of_a_different_version")

    assert r.status == "FAILED"
    assert "核准" in r.detail


def test_readback_mismatch_does_not_auto_retry():
    """API 回成功但值沒進去：標記 VERIFY_FAILED，交給人，不自己重試。"""
    p = _proposal()
    calls = {"n": 0}

    def reader(_):
        calls["n"] += 1
        return BEFORE   # 寫入後重讀仍是舊值 —— 代表沒寫進去

    ex = WriteExecutor(reader=reader, dry_run=False)
    ex._write = lambda _p: None   # 假裝 API 呼叫成功
    r = ex.execute(p, p.proposal_hash)

    assert r.status == "VERIFY_FAILED"
    assert calls["n"] == 2        # 寫前一次、寫後一次，沒有第三次重試


def test_write_failure_is_recorded_not_raised():
    """呼叫爆掉時要留下收據，不是把例外往上丟讓整批中斷。"""
    p = _proposal()
    ex = WriteExecutor(reader=lambda _: BEFORE, dry_run=False)

    def boom(_p):
        raise ConnectionError("gms unreachable")

    ex._write = boom
    r = ex.execute(p, p.proposal_hash)

    assert r.status == "FAILED"
    assert "ConnectionError" in r.detail
