"""唯讀 DataHub adapter — 系統讀取 context graph 的唯一入口。

安全約束（SPEC §1.2 第 2 條）：本模組**只** wrap Agent Context Kit 的讀取工具。
寫入工具（add_tags / add_glossary_terms / descriptions / documents / add_owners）
刻意不在此出現，也不 import —— 寫入路徑走 executor.py，且由另一組憑證執行。

每次呼叫都會把結果登記成 Evidence，讓後續任何主張都能指回「哪個 function、
對哪個 URN、在什麼時候、拿到什麼內容」。
"""

from __future__ import annotations

import warnings
from typing import Any

from .evidence import Evidence, EvidenceStore

warnings.filterwarnings("ignore", category=UserWarning)

# 白名單：唯一允許被 adapter 呼叫的 Agent Context Kit 工具
READ_ONLY_TOOLS = (
    "get_entities",
    "list_schema_fields",
    "get_lineage",
    "get_dataset_queries",
    "grep_documents",
)


class ReadOnlyDataHubAdapter:
    """對 DataHub 的唯讀視窗。

    使用方式：
        with ReadOnlyDataHubAdapter(server="http://localhost:8080") as adapter:
            entity, ev_id = adapter.get_entity(urn)
    """

    def __init__(self, server: str = "http://localhost:8080", token: str | None = None) -> None:
        self.server = server
        self.token = token
        self.evidence = EvidenceStore()
        self._ctx = None
        self._client = None

    def __enter__(self) -> "ReadOnlyDataHubAdapter":
        from datahub.sdk import DataHubClient
        from datahub_agent_context import DataHubContext

        self._client = DataHubClient(server=self.server, token=self.token)
        self._ctx = DataHubContext(self._client)
        self._ctx.__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._ctx is not None:
            self._ctx.__exit__(*exc)

    def _record(self, urn: str, fn: str, payload: Any) -> str:
        return self.evidence.add(Evidence(entity_urn=urn, source_function=fn, payload=payload))

    # --- 唯讀工具，逐個薄包裝並登記證據 -------------------------------

    def get_entity(self, urn: str) -> tuple[dict, str]:
        """取單一 entity 的 metadata（含人寫的 description）。"""
        from datahub_agent_context.mcp_tools import get_entities

        result = get_entities([urn])
        payload = result[0] if result else {}
        return payload, self._record(urn, "get_entities", payload)

    def list_schema_fields(self, urn: str, limit: int = 100) -> tuple[dict, str]:
        """取 dataset 的欄位清單 —— 「資料現實」的主要來源。"""
        from datahub_agent_context.mcp_tools import list_schema_fields

        payload = list_schema_fields(urn, limit=limit)
        return payload, self._record(urn, "list_schema_fields", payload)

    def get_lineage(self, urn: str, upstream: bool = True, max_hops: int = 1) -> tuple[dict, str]:
        """取上下游 —— 用於比對描述宣稱的來源表是否還在上游集合裡。"""
        from datahub_agent_context.mcp_tools import get_lineage

        payload = get_lineage(urn, upstream=upstream, max_hops=max_hops)
        return payload, self._record(urn, "get_lineage", payload)

    def get_dataset_queries(self, urn: str, column: str | None = None, count: int = 10) -> tuple[dict, str]:
        """取實際查詢紀錄 —— 語意漂移（D5）靠它看欄位真正怎麼被用。"""
        from datahub_agent_context.mcp_tools import get_dataset_queries

        payload = get_dataset_queries(urn, column=column, count=count)
        return payload, self._record(urn, "get_dataset_queries", payload)

    def grep_documents(self, urns: list[str], pattern: str) -> tuple[dict, str]:
        """在文件內容中搜尋 —— 找出還在引用舊欄位名的說明文件。"""
        from datahub_agent_context.mcp_tools import grep_documents

        payload = grep_documents(urns, pattern)
        return payload, self._record(f"pattern:{pattern}", "grep_documents", payload)
