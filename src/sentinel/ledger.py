"""Hash 鏈審計帳本 — 所有階段的動作都留下可事後驗證的痕跡（SPEC §4）。

設計約束：
- append-only JSONL：一行一筆、只增不改。竄改偵測靠 hash 鏈本身，
  不依賴檔案權限 —— 拿得到寫入權的人本來就繞得過權限。
- 每筆的 prev_hash 指向前一筆的 entry_hash，genesis 指向固定字串，
  所以改內容、刪紀錄、調順序三種竄改都會在某個位置斷鏈。
- 純檔案 IO、不碰 DataHub —— ledger 是最後一道防線，
  不能依賴任何被它審計的元件。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import canonical_hash

# genesis 的 prev_hash 固定值 —— 讓「第一筆被整段換掉」也能被驗出來
GENESIS_HASH = "genesis"


class AuditLedger:
    """append-only 審計帳本。一個實例對應一個 JSONL 檔。"""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        # 重開帳本必須接在既有鏈尾，不是另起新鏈 ——
        # 否則跨次執行之間的順序與完整性保證就斷了
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._path.exists():
            return GENESIS_HASH
        last = GENESIS_HASH
        with self._path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line:
                    last = json.loads(line)["entry_hash"]
        return last

    def append(self, stage: str, run_id: str, entity_urn: str, payload: Any) -> dict[str, Any]:
        """寫入一筆紀錄並回傳完整內容（含算好的 entry_hash）。"""
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": run_id,
            "stage": stage,
            "entity_urn": entity_urn,
            "payload": payload,
            "prev_hash": self._last_hash,
        }
        # entry_hash 涵蓋 prev_hash 與全部欄位 —— 只要有一個欄位被改，
        # 這筆的 hash 就對不上；prev_hash 進 hash 則讓鏈的順序不可換
        entry["entry_hash"] = canonical_hash(entry)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        self._last_hash = entry["entry_hash"]
        return entry

    def verify(self) -> tuple[bool, str]:
        """重讀整個檔案驗證鏈的完整性。回傳 (是否有效, 說明)。

        逐筆做兩個檢查，回報第一個出問題的位置（1-based 行號）：
        1. 重算 entry_hash —— 抓「內容被改但 hash 沒重算」
        2. prev_hash 必須等於前一筆的 entry_hash —— 抓刪除與順序調換；
           內容被改且 hash 有重算的情況，也會在下一筆的這個檢查斷鏈
        """
        if not self._path.exists():
            return (True, "空帳本，鏈有效（0 筆）")

        expected_prev = GENESIS_HASH
        count = 0
        with self._path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line:
                    continue
                count += 1
                try:
                    entry: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    return (False, f"第 {lineno} 筆不是合法 JSON")

                stored_hash = entry.get("entry_hash")
                body = {k: v for k, v in entry.items() if k != "entry_hash"}
                if canonical_hash(body) != stored_hash:
                    return (False, f"第 {lineno} 筆內容與 entry_hash 不符，內容遭竄改")
                if entry.get("prev_hash") != expected_prev:
                    return (False, f"第 {lineno} 筆 prev_hash 斷鏈，紀錄遭刪除或順序遭調換")
                expected_prev = str(stored_hash)

        return (True, f"鏈有效（{count} 筆）")
