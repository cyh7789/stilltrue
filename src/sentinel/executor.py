"""寫入執行器 — 唯一會改動 DataHub 的地方。

與 adapter 的分工（SPEC §1.2 第 2、9–12 條）：adapter 只讀、拿唯讀憑證；
executor 只在拿到核准後寫，且寫入前後都自己重讀一次確認。
提案由誰產生不影響這裡的判斷 —— 沒有核准、或核准對不上內容，就不寫。

三個保護，各擋一種真實會發生的事：
- 寫前重讀：從產生提案到核准之間，別人可能已經改過同一個欄位（TOCTOU）
- 冪等鍵：重跑腳本、重試網路失敗時，不會把同一個變更套用兩次
- 寫後回讀：API 回 200 不代表值真的寫進去了
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from .evidence import canonical_hash
from .proposal import Proposal

warnings.filterwarnings("ignore", category=UserWarning)

ExecutionStatus = Literal[
    "VERIFIED",        # 寫入成功且回讀確認
    "CONFLICT",        # 寫入前發現現況已與提案基準不同，未寫入
    "DUPLICATE",       # 同一個冪等鍵已經執行過，未重複寫入
    "VERIFY_FAILED",   # 寫入後回讀對不上 —— 不自動重試，交給人
    "FAILED",          # 呼叫本身失敗
]


@dataclass
class Receipt:
    idempotency_key: str
    proposal_hash: str
    entity_urn: str
    status: ExecutionStatus
    detail: str
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "idempotency_key": self.idempotency_key,
            "proposal_hash": self.proposal_hash,
            "entity_urn": self.entity_urn,
            "status": self.status,
            "detail": self.detail,
            "executed_at": self.executed_at,
        }


def idempotency_key(p: Proposal) -> str:
    """同一個 (entity, aspect, subject, 提案內容) 只該被套用一次。"""
    return canonical_hash({
        "urn": p.entity_urn, "aspect": p.aspect,
        "subject": p.subject, "proposal": p.proposal_hash,
    })


class WriteExecutor:
    """把已核准的提案寫回 DataHub。

    reader 參數是一個「重讀目前值」的函式，注入而非內建 —— 讓寫前檢查與寫後回讀
    可以在測試中不碰真實 DataHub，也讓 executor 不需要知道值是怎麼讀出來的。
    """

    def __init__(
        self,
        reader: Callable[[Proposal], str],
        server: str = "http://localhost:8080",
        token: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self.reader = reader
        self.server = server
        self.token = token
        self.dry_run = dry_run
        self._receipts: dict[str, Receipt] = {}

    def execute(self, p: Proposal, approved_hash: str) -> Receipt:
        key = idempotency_key(p)

        if approved_hash != p.proposal_hash:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "FAILED",
                                        "核准的 proposal_hash 與提案內容不符，提案可能在核准後被修改"))

        prior = self._receipts.get(key)
        if prior is not None and prior.status in ("VERIFIED", "DUPLICATE"):
            return Receipt(key, p.proposal_hash, p.entity_urn, "DUPLICATE",
                           f"此變更已於 {prior.executed_at} 套用，未重複寫入")

        current = self.reader(p)
        if canonical_hash({"urn": p.entity_urn, "aspect": p.aspect,
                           "subject": p.subject, "value": current}) != p.before_hash:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "CONFLICT",
                                        "寫入前重讀發現現況已與提案基準不同，未寫入"))

        if self.dry_run:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "VERIFIED",
                                        "dry-run：未實際寫入"))

        try:
            self._write(p)
        except Exception as exc:
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "FAILED",
                                        f"{type(exc).__name__}: {exc}"))

        after = self.reader(p)
        if after.strip() != p.after_value.strip():
            return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "VERIFY_FAILED",
                                        "寫入後回讀的內容與提案不符 —— 不自動重試，需人工確認"))

        return self._record(Receipt(key, p.proposal_hash, p.entity_urn, "VERIFIED",
                                    "寫入完成並經回讀確認"))

    def _write(self, p: Proposal) -> None:
        """實際呼叫 DataHub。每次只做一個白名單內的變更。"""
        from datahub.sdk import DataHubClient
        from datahub_agent_context import DataHubContext
        from datahub_agent_context.mcp_tools import descriptions

        client = DataHubClient(server=self.server, token=self.token)
        with DataHubContext(client):
            if p.aspect == "dataset_description":
                descriptions.update_description(
                    entity_urn=p.entity_urn, operation="replace", description=p.after_value
                )
            elif p.aspect == "field_description":
                descriptions.update_description(
                    entity_urn=p.entity_urn, operation="replace",
                    description=p.after_value, column_path=p.subject,
                )
            else:
                raise ValueError(f"executor 不支援的 aspect: {p.aspect}")

    def _record(self, r: Receipt) -> Receipt:
        self._receipts[r.idempotency_key] = r
        return r
