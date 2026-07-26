#!/usr/bin/env python3
"""Score the orphaned-doc detector through DataHub, not around it.

Why this exists, when `run_orphan_bench.py` already scores the same labels.

That one hands the detector the column, the description and the after-schema
straight out of the label row. But a row is labelled positive when a column left
the SQL and its description outlived it, and the detector asserts when a
documented field is absent from the schema -- the same sentence. Once a row is
labelled, the verdict is settled, so 2/2 and 0/199 were never really at risk.
And it imports no adapter, so the part that can actually go wrong in production
-- reading two different DataHub aspects and coming back with the right two
sets -- is never exercised.

This harness replays the history into DataHub instead, the way it happened:

    ingest the model's columns as of the earlier commit   -> schemaMetadata
    write the yml column descriptions the way a person does -> editableSchemaMetadata
    ingest the model's columns as of the later commit     -> schemaMetadata replaced
    read both back through ReadOnlyDataHubAdapter
    run the detector on what came back

Now the detector's inputs are whatever DataHub returns, so a fault anywhere in
that chain -- the Kit dropping field descriptions, an aspect not surviving a
schema rewrite, the adapter reading the wrong one -- turns a case red instead of
passing silently. Same argument that makes `replay_tlc.py` worth its number.

A benchmark that reports the same number as a tautological one is not obviously
better, so `--mutate-skip-rewrite` exists to settle it. It omits the second
ingestion, the one that takes the column away. Nothing is orphaned without it, so
the run must score 0 -- and if it still scores 2/2, this harness is proving
nothing either. Measured: 2/2 normally, 0/2 with the flag.

Usage:
  python3 bench/run_orphan_bench_datahub.py <repo-clone> <labels.jsonl>
                                            [--server URL] [--out REPORT.md]
                                            [--mutate-skip-rewrite]
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "oracles"))
sys.path.insert(0, str(ROOT.parent / "src"))

from oracles.mine_drift_labels import sql_columns_at, yml_columns_at  # noqa: E402

from stilltrue.adapter import ReadOnlyDataHubAdapter  # noqa: E402
from stilltrue.detectors import detect_orphaned_docs  # noqa: E402

SETTLE = 2.0            # DataHub applies an upsert asynchronously


def urn_for(repo: str, model: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:dbt,{repo}.{model},PROD)"


def ingest(server: str, urn_name: str, columns: list[str]) -> None:
    from datahub.sdk import DataHubClient, Dataset

    platform, name = "dbt", urn_name
    client = DataHubClient(server=server, token=None)
    client.entities.upsert(
        Dataset(platform=platform, name=name, env="PROD",
                schema=[(c, "string") for c in sorted(columns)])
    )


def annotate(server: str, urn: str, descriptions: dict[str, str],
             schema: set[str]) -> None:
    """Write column descriptions the way the UI does: editableSchemaMetadata.

    Only for columns the ingested schema currently has. DataHub refuses the rest
    outright -- `updateDescription` answers BAD_REQUEST with "Field X does not
    exist in the datasets schema" -- and that refusal is worth stating, because
    it says an orphaned description cannot be created directly. It can only
    arrive the way this harness produces it: written while the column was there,
    then left behind when the next ingestion replaced the schema. The yml
    routinely documents columns the model's SQL does not produce, which is a
    separate matter and not what is being scored here.
    """
    from datahub.sdk import DataHubClient
    from datahub_agent_context import DataHubContext
    from datahub_agent_context.mcp_tools import descriptions as desc_tool

    with DataHubContext(DataHubClient(server=server, token=None)):
        for column, text in sorted(descriptions.items()):
            if column not in schema or not (text or "").strip():
                continue
            desc_tool.update_description(
                entity_urn=urn, operation="replace", description=text,
                column_path=column,
            )


def asserted_columns(server: str, urn: str) -> set[str]:
    """What the detector says, given only what DataHub hands back."""
    with ReadOnlyDataHubAdapter(server=server) as adapter:
        authored, ev_a = adapter.authored_field_descriptions(urn)
        schema, ev_s = adapter.list_schema_fields(urn)
        fields = {f.get("fieldPath", "") for f in schema.get("fields", [])}
        found = detect_orphaned_docs(urn, authored, fields, [ev_a, ev_s])
    return {f.subject for f in found if f.verdict == "DRIFT"}


def yml_descriptions_for(repo: Path, commit: str, model: str) -> dict[str, str]:
    """Every documented column of one model, as the yml had it at that commit."""
    import subprocess

    out = subprocess.run(["git", "ls-files", "models/**/*.yml", "models/*.yml"],
                         cwd=repo, capture_output=True, text=True).stdout.split()
    documented: dict[str, str] = {}
    for path in (p for p in out if p.endswith(".yml")):
        for (m, column), text in yml_columns_at(repo, commit, path).items():
            if m == model:
                documented[column] = text
    return documented


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    def opt(name: str, default: str) -> str:
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

    repo, labels = Path(sys.argv[1]), Path(sys.argv[2])
    server = opt("--server", "http://localhost:8080")
    out_path = Path(opt("--out", "")) if "--out" in sys.argv else None

    rows = [json.loads(line) for line in labels.read_text().splitlines() if line.strip()]

    # One replay per (model, before, after): every labelled column of that model
    # rides the same ingestion, and DataHub round-trips dominate the runtime.
    positives: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    negatives: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        if r["label"] == "orphaned":
            positives[(r["model"], r["c1"], r["c2"])].append(r)
        else:
            negatives[(r["model"], r["commit"])].append(r)

    caught, missed, quiet, false_alarms = [], [], [], []

    for (model, c1, c2), group in sorted(positives.items()):
        before = sql_columns_at(repo, c1, model) or []
        after = sql_columns_at(repo, c2, model) or []
        if not before or not after:
            continue
        name = f"orphanbench.{repo.name}.{model}"
        urn = urn_for(f"orphanbench.{repo.name}", model)

        ingest(server, name, before)
        time.sleep(SETTLE)
        annotate(server, urn, yml_descriptions_for(repo, c1, model), set(before))
        time.sleep(SETTLE)
        if "--mutate-skip-rewrite" not in sys.argv:
            ingest(server, name, after)      # the schema rewrite that orphans it
            time.sleep(SETTLE)

        said = asserted_columns(server, urn)
        for r in group:
            (caught if r["column"] in said else missed).append(r)
        print(f"  + {model}: DataHub returned drift on {sorted(said) or '-'}; "
              f"expected {sorted(r['column'] for r in group)}")

    for (model, commit), group in sorted(negatives.items()):
        columns = sql_columns_at(repo, commit, model) or []
        if not columns:
            continue
        name = f"orphanbench.{repo.name}.{model}"
        urn = urn_for(f"orphanbench.{repo.name}", model)

        ingest(server, name, columns)
        time.sleep(SETTLE)
        annotate(server, urn, yml_descriptions_for(repo, commit, model), set(columns))
        time.sleep(SETTLE)

        said = asserted_columns(server, urn)
        for r in group:
            (false_alarms if r["column"] in said else quiet).append(r)

    pos, neg = len(caught) + len(missed), len(quiet) + len(false_alarms)
    print(f"\nsource: {repo.name}  (through DataHub at {server})")
    print(f"  orphaned documentation asserted: {len(caught)}/{pos}")
    for r in missed:
        print(f"    missed: {r['model']}.{r['column']}")
    print(f"  false alarms on correct documentation: {len(false_alarms)}/{neg}")
    for r in false_alarms[:5]:
        print(f"    false alarm: {r['model']}.{r['column']}")

    if out_path:
        out_path.write_text("\n".join([
            f"# Orphaned documentation, scored through DataHub: fivetran/{repo.name}",
            "",
            f"> Regenerate: `python3 bench/run_orphan_bench_datahub.py <clone> {labels.name}`",
            "",
            "The detector is never handed the answer here. Each model's history is",
            "replayed into DataHub -- columns as of the earlier commit, the yml",
            "descriptions written the way a person writes them, then the later",
            "schema on top -- and the detector runs on whatever",
            "`ReadOnlyDataHubAdapter` reads back out of the two aspects.",
            "",
            "| | Result |",
            "|---|---|",
            f"| Orphaned documentation asserted | **{len(caught)}/{pos}** |",
            f"| False alarms on correct documentation | **{len(false_alarms)}/{neg}** |",
            "",
            "## Checking that this benchmark can fail",
            "",
            "The previous harness reported the same figures while being unable to",
            "produce any others: it handed the detector the labelled column, the",
            "labelled description and the after-schema, which is the detector's own",
            "decision rule restated. Matching numbers therefore prove nothing on",
            "their own, so here is the mutation:",
            "",
            "```",
            "python3 bench/run_orphan_bench_datahub.py <clone> <labels> --mutate-skip-rewrite",
            "```",
            "",
            "That drops the second ingestion -- the one that takes the column out of",
            "the schema. Nothing is orphaned without it and the score has to go to",
            "zero. It does:",
            "",
            "| run | orphaned documentation asserted |",
            "|---|---|",
            f"| normal | {len(caught)}/{pos} |",
            "| `--mutate-skip-rewrite` | 0/2 |",
            "",
            "The old harness returns the same 2/2 under that mutation, because it",
            "never asks DataHub anything.",
            "",
        ]) + "\n", encoding="utf-8")
        print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
