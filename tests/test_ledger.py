"""Hash 鏈審計帳本的行為測試。

每一條都模擬一種真實竄改手法：直接改寫 JSONL 檔再跑 verify()。
測的是「竄改會被抓到、位置回報正確」這個行為 ——
把 verify 的任一個檢查弄壞，對應的測試就會紅；只改名字不會。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.evidence import canonical_hash  # noqa: E402
from sentinel.ledger import AuditLedger  # noqa: E402

URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"


def _build_ledger(path: Path, n: int = 5) -> AuditLedger:
    led = AuditLedger(path)
    for i in range(n):
        led.append(stage="detect", run_id="run-1", entity_urn=URN, payload={"seq": i})
    return led


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_intact_chain_verifies(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    ok, msg = led.verify()

    assert ok
    assert "5" in msg


def test_empty_ledger_is_valid(tmp_path: Path) -> None:
    """檔案還不存在的帳本視為有效 —— 第一次 scan 之前跑 verify 不該報錯。"""
    led = AuditLedger(tmp_path / "audit.jsonl")

    ok, _ = led.verify()

    assert ok


def test_content_tamper_is_caught_at_position(tmp_path: Path) -> None:
    """改一筆 payload 但沒重算 hash —— 最直接的竄改手法。"""
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    entry = json.loads(lines[2])
    entry["payload"] = {"seq": 999}
    lines[2] = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    assert "第 3 筆" in msg


def test_recomputed_hash_tamper_is_still_caught(tmp_path: Path) -> None:
    """竄改者連 entry_hash 一起重算 —— 下一筆的 prev_hash 仍會咬住它。

    這條擋掉「verify 只重算單筆 hash、不追鏈」的偷懶實作。
    """
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    entry = json.loads(lines[2])
    entry["payload"] = {"seq": 999}
    del entry["entry_hash"]
    entry["entry_hash"] = canonical_hash(entry)
    lines[2] = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    assert "第 4 筆" in msg


def test_deleted_middle_entry_is_caught(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    del lines[2]
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    # 原第 4 筆補上來變成第 3 行，它的 prev_hash 指向被刪的那筆 → 在這裡斷鏈
    assert "第 3 筆" in msg


def test_swapped_entries_are_caught(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    led = _build_ledger(path)

    lines = _lines(path)
    lines[1], lines[2] = lines[2], lines[1]
    _write(path, lines)

    ok, msg = led.verify()
    assert not ok
    assert "第 2 筆" in msg


def test_reopened_ledger_continues_chain(tmp_path: Path) -> None:
    """跨次執行必須接在既有鏈尾 —— 重開若另起新鏈，後續紀錄會全部斷鏈。"""
    path = tmp_path / "audit.jsonl"
    _build_ledger(path, n=2)

    led2 = AuditLedger(path)
    led2.append(stage="write", run_id="run-2", entity_urn=URN, payload={"seq": 99})

    ok, msg = led2.verify()
    assert ok
    assert "3" in msg
