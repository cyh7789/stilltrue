"""Policy Gate 的行為測試。

Gate 的價值在於「擋得住」，所以每個測試都是一種攻擊：
引用假證據、清空內容、改動不該改的東西、換湯不換藥。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.evidence import Evidence, EvidenceStore  # noqa: E402
from sentinel.proposal import PolicyGate, Proposal  # noqa: E402

URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"


def _store_with_one_evidence() -> tuple[EvidenceStore, str]:
    store = EvidenceStore()
    ev_id = store.add(Evidence(entity_urn=URN, source_function="list_schema_fields",
                               payload={"fields": [{"fieldPath": "Airport_fee"}]}))
    return store, ev_id


def _valid_proposal(ev_id: str, **overrides) -> Proposal:
    base = dict(
        entity_urn=URN, aspect="dataset_description", verdict="DRIFT", subject="description",
        before_value="Fare breakdown includes airport_fee for LGA/JFK pickups.",
        after_value="Fare breakdown includes Airport_fee for LGA/JFK pickups.",
        rationale="schema 中欄位名為 Airport_fee，描述沿用舊的 airport_fee。",
        evidence_ids=[ev_id],
    )
    base.update(overrides)
    return Proposal(**base)


def test_valid_proposal_passes():
    store, ev = _store_with_one_evidence()
    assert PolicyGate(store).check(_valid_proposal(ev)).passed


def test_fabricated_evidence_is_rejected():
    """LLM 最容易犯的錯：引用一個聽起來合理但不存在的 evidence_id。"""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, evidence_ids=["ev_deadbeef12345678"]))

    assert not result.passed
    assert any("不存在的證據" in v for v in result.violations)


def test_proposal_without_evidence_is_rejected():
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, evidence_ids=[]))

    assert not result.passed
    assert any("沒有引用任何證據" in v for v in result.violations)


def test_clearing_content_is_rejected():
    """把描述清空也是一種「修正」，但刪除不在允許範圍內。"""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, after_value="   "))

    assert not result.passed
    assert any("清空" in v for v in result.violations)


def test_non_drift_verdict_cannot_produce_a_change():
    """棄權或判定無漂移時，不該有任何寫入提案冒出來。"""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, verdict="INSUFFICIENT_EVIDENCE"))

    assert not result.passed
    assert any("不應產生變更提案" in v for v in result.violations)


def test_aspect_outside_whitelist_is_rejected():
    """白名單之外的變更類型一律拒絕 —— 包含看起來無害的。"""
    store, ev = _store_with_one_evidence()
    result = PolicyGate(store).check(_valid_proposal(ev, aspect="ownership"))

    assert not result.passed
    assert any("白名單" in v for v in result.violations)


def test_editing_a_proposal_invalidates_the_old_approval():
    """核准綁在 proposal_hash 上：內容一改，hash 就變，舊核准不能沿用。"""
    store, ev = _store_with_one_evidence()
    original = _valid_proposal(ev)
    edited = _valid_proposal(ev, after_value=original.after_value + " (updated)")

    assert original.proposal_hash != edited.proposal_hash


def test_same_content_yields_same_hash():
    """同一份提案重建後 hash 必須一致，否則核准會在重跑後全部失效。"""
    store, ev = _store_with_one_evidence()
    assert _valid_proposal(ev).proposal_hash == _valid_proposal(ev).proposal_hash
