"""Read-only DataHub adapter: the system's single entry point to the context graph.

Security constraint (SPEC 1.2 item 2): this module wraps **only** the read
tools of the Agent Context Kit. The mutation tools (add_tags,
add_glossary_terms, descriptions, documents, add_owners) are deliberately
absent and never imported here. Writes go through executor.py under a
separate credential.

Every call registers its result as Evidence, so any later claim can point back
to which function read which URN, when, and what it returned.
"""

from __future__ import annotations

import warnings
from typing import Any

from .evidence import Evidence, EvidenceStore

warnings.filterwarnings("ignore", category=UserWarning)

def authored_description(entity: dict) -> str:
    """The description a human would actually see in the DataHub UI.

    DataHub keeps two of them: `properties.description` comes from ingestion,
    `editableProperties.description` is what someone typed in the UI or wrote
    through the API. The UI shows the editable one when it exists, so that is
    the text a reader believes — and therefore the text that can be lying.
    Reading only `properties` misses it entirely.
    """
    editable = (entity.get("editableProperties") or {}).get("description") or ""
    ingested = (entity.get("properties") or {}).get("description") or ""
    return editable.strip() or ingested.strip()


# Whitelist: the only Agent Context Kit tools this adapter may call
READ_ONLY_TOOLS = (
    "get_entities",
    "list_schema_fields",
    "get_lineage",
    "get_dataset_queries",
    "grep_documents",
)


class ReadOnlyDataHubAdapter:
    """A read-only window onto DataHub.

    Usage:
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

    # --- read-only tools: thin wrappers that register evidence ---------

    def get_entity(self, urn: str) -> tuple[dict, str]:
        """Fetch one entity's metadata, including the human-authored description."""
        from datahub_agent_context.mcp_tools import get_entities

        result = get_entities([urn])
        payload = result[0] if result else {}
        return payload, self._record(urn, "get_entities", payload)

    def list_schema_fields(self, urn: str, limit: int = 100) -> tuple[dict, str]:
        """List the dataset's fields: the main source of reality-side signal."""
        from datahub_agent_context.mcp_tools import list_schema_fields

        payload = list_schema_fields(urn, limit=limit)
        return payload, self._record(urn, "list_schema_fields", payload)

    def get_lineage(self, urn: str, upstream: bool = True, max_hops: int = 1) -> tuple[dict, str]:
        """Fetch lineage, used to check whether a claimed source is still upstream."""
        from datahub_agent_context.mcp_tools import get_lineage

        payload = get_lineage(urn, upstream=upstream, max_hops=max_hops)
        return payload, self._record(urn, "get_lineage", payload)

    def get_dataset_queries(self, urn: str, column: str | None = None, count: int = 10) -> tuple[dict, str]:
        """Fetch real query history: how D5 sees the way a field is actually used."""
        from datahub_agent_context.mcp_tools import get_dataset_queries

        payload = get_dataset_queries(urn, column=column, count=count)
        return payload, self._record(urn, "get_dataset_queries", payload)

    def grep_documents(self, urns: list[str], pattern: str) -> tuple[dict, str]:
        """Search inside documents for prose still referencing an old field name."""
        from datahub_agent_context.mcp_tools import grep_documents

        payload = grep_documents(urns, pattern)
        return payload, self._record(f"pattern:{pattern}", "grep_documents", payload)
