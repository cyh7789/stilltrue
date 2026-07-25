"""Context Drift Sentinel CLI.

One subcommand per state transition:
    scan      read DataHub, run deterministic detectors, persist findings + evidence
    findings  list what the scan found
    apply     turn a finding into a proposal, gate it, confirm the exact text, write back
    verify    check that the audit ledger has not been tampered with

Deliberately non-interactive: every step leaves files behind, so a reviewer can
open them directly and the whole flow can be scripted end to end. Approval is a
`--approve <proposal_hash>` argument rather than a y/n prompt for the same
reason — and because a token bound to the content is what makes editing the
text after approval fail closed. A prompt would just ask again.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

import typer

from .adapter import ReadOnlyDataHubAdapter, authored_description
from .detectors import detect_lineage_drift, detect_schema_break
from .executor import WriteExecutor
from .ledger import AuditLedger
from .proposal import PolicyGate, Proposal, check_approval

app = typer.Typer(add_completion=False, help="Find DataHub context that has drifted out of sync with reality.")

WORK_DIR = Path("runs")
FINDINGS_FILE = "findings.jsonl"
EVIDENCE_FILE = "evidence.jsonl"
LEDGER_FILE = "audit-ledger.jsonl"


def _run_dir(run_id: str) -> Path:
    d = WORK_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _latest_run() -> Path:
    runs = sorted(WORK_DIR.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        raise typer.BadParameter("No scan results found. Run `sentinel scan` first.")
    return runs[0]


@app.command()
def scan(
    urn: Optional[str] = typer.Option(None, help="Scan a single dataset; otherwise scan --limit datasets"),
    limit: int = typer.Option(25, help="How many datasets to scan when --urn is not given"),
    server: str = typer.Option("http://localhost:8080", help="DataHub GMS address"),
) -> None:
    """Read DataHub, run the deterministic detectors, persist findings and evidence."""
    import base64
    import urllib.request

    run_id = uuid.uuid4().hex[:12]
    out = _run_dir(run_id)
    ledger = AuditLedger(out / LEDGER_FILE)

    if urn:
        urns = [urn]
    else:
        req = urllib.request.Request(f"{server}/openapi/v3/entity/dataset?count={limit}")
        req.add_header("Authorization", "Basic " + base64.b64encode(b"datahub:datahub").decode())
        urns = [e["urn"] for e in json.load(urllib.request.urlopen(req)).get("entities", [])]

    typer.echo(f"run {run_id}: scanning {len(urns)} datasets")
    findings = []

    with ReadOnlyDataHubAdapter(server=server) as adapter:
        for u in urns:
            try:
                entity, ev_entity = adapter.get_entity(u)
                schema, ev_schema = adapter.list_schema_fields(u)
            except Exception as exc:
                typer.echo(f"  skipped {u}: {type(exc).__name__}")
                continue

            description = authored_description(entity)
            fields = schema.get("fields", [])
            evidence_ids = [ev_entity, ev_schema]

            found = detect_schema_break(u, description, fields, evidence_ids)

            try:
                lineage, ev_lineage = adapter.get_lineage(u)
                upstreams = [x.get("urn", "") for x in (lineage.get("upstreams") or [])]
                found += detect_lineage_drift(u, description, upstreams, evidence_ids + [ev_lineage])
            except Exception:
                pass  # missing lineage must not invalidate the schema-side verdict

            findings.extend(found)
            ledger.append("scan", run_id, u, {"findings": len(found), "evidence": evidence_ids})

        (out / EVIDENCE_FILE).write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in adapter.evidence.to_list()),
            encoding="utf-8",
        )

    with (out / FINDINGS_FILE).open("w", encoding="utf-8") as fh:
        for i, f in enumerate(findings):
            row = f.to_dict() | {"finding_id": f"{run_id}-{i:04d}"}
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    tally = {v: sum(1 for f in findings if f.verdict == v)
             for v in ("DRIFT", "CURRENT", "INSUFFICIENT_EVIDENCE")}
    typer.echo(
        f"  {tally['DRIFT']} drift, {tally['CURRENT']} verified current, "
        f"{tally['INSUFFICIENT_EVIDENCE']} abstained ({len(findings)} checks)"
    )
    typer.echo(f"  -> {out}")


@app.command()
def findings(
    run: Optional[str] = typer.Option(None, help="Run id; defaults to the most recent scan"),
    verdict: str = typer.Option("DRIFT", help="Filter by verdict; ALL shows everything"),
) -> None:
    """List what the scan found."""
    d = _run_dir(run) if run else _latest_run()
    rows = [json.loads(l) for l in (d / FINDINGS_FILE).read_text(encoding="utf-8").splitlines() if l]
    if verdict != "ALL":
        rows = [r for r in rows if r["verdict"] == verdict]

    typer.echo(f"{d.name}: {len(rows)} findings")
    for r in rows:
        rename = f" -> likely renamed to `{r['suspected_rename']}`" if r.get("suspected_rename") else ""
        typer.echo(f"  [{r['finding_id']}] {r['category']} {r['subject']}{rename}")
        typer.echo(f"      {r['reality']}")


@app.command()
def verify(run: Optional[str] = typer.Option(None, help="Run id; defaults to the most recent scan")) -> None:
    """Check that the audit ledger's hash chain is intact."""
    d = _run_dir(run) if run else _latest_run()
    ok, detail = AuditLedger(d / LEDGER_FILE).verify()
    typer.echo(f"{'OK' if ok else 'FAILED'}: {detail}")
    raise typer.Exit(0 if ok else 1)


@app.command()
def apply(
    finding_id: str = typer.Argument(..., help="Which finding to act on"),
    new_value: str = typer.Option(..., "--to", help="The corrected content"),
    approve: Optional[str] = typer.Option(
        None, "--approve",
        help="The proposal_hash you are confirming. Run without it first to see the diff and the hash.",
    ),
    commit: bool = typer.Option(False, "--commit", help="Actually write to DataHub; dry-run by default"),
    server: str = typer.Option("http://localhost:8080"),
) -> None:
    """Turn a finding into a proposal, run the Policy Gate, then write it back."""
    d = _latest_run()
    rows = {json.loads(l)["finding_id"]: json.loads(l)
            for l in (d / FINDINGS_FILE).read_text(encoding="utf-8").splitlines() if l}
    if finding_id not in rows:
        raise typer.BadParameter(f"No such finding: {finding_id}")

    f = rows[finding_id]
    ledger = AuditLedger(d / LEDGER_FILE)

    with ReadOnlyDataHubAdapter(server=server) as adapter:
        # Reload the evidence this run captured, otherwise the Gate rejects the
        # proposal for citing ids it cannot resolve -- correctly so.
        ev_path = d / EVIDENCE_FILE
        if ev_path.exists():
            rows = [json.loads(l) for l in ev_path.read_text(encoding="utf-8").splitlines() if l]
            adapter.evidence.hydrate(rows)

        entity, ev = adapter.get_entity(f["entity_urn"])
        before = authored_description(entity)

        p = Proposal(
            entity_urn=f["entity_urn"], aspect="dataset_description", verdict="DRIFT",
            subject="description", before_value=before, after_value=new_value,
            rationale=f["reality"], evidence_ids=f["evidence_ids"] + [ev],
        )
        result = PolicyGate(adapter.evidence).check(p)

    ledger.append("propose", d.name, p.entity_urn,
                  {"proposal_hash": p.proposal_hash, "gate_passed": result.passed})

    if not result.passed:
        typer.echo("Blocked by the Policy Gate:")
        for v in result.violations:
            typer.echo(f"  - {v}")
        raise typer.Exit(2)

    typer.echo(f"Gate passed, proposal_hash={p.proposal_hash[:16]}")

    decision = check_approval(p, approve)
    ledger.append("approve", d.name, p.entity_urn,
                  {"proposal_hash": p.proposal_hash, "status": decision.status})

    if not decision.authorised:
        # The gate says the proposal is well formed. Nobody has said they want
        # it. Showing the diff here is the point: this is what gets reviewed.
        typer.echo(f"\n{decision.status}: {decision.detail}\n")
        typer.echo(f"  - {before}")
        typer.echo(f"  + {new_value}")
        raise typer.Exit(3)

    typer.echo(f"Confirmed ({decision.detail})")

    def reread(prop: Proposal) -> str:
        """Fetch the live value. Must actually hit DataHub, or the read-back
        check compares the proposal against a stale copy and always fails."""
        with ReadOnlyDataHubAdapter(server=server) as a:
            current, _ = a.get_entity(prop.entity_urn)
            return authored_description(current)

    executor = WriteExecutor(reader=reread, server=server, dry_run=not commit)
    receipt = executor.execute(p, p.proposal_hash)
    ledger.append("execute", d.name, p.entity_urn, receipt.to_dict())

    typer.echo(f"{receipt.status}: {receipt.detail}")
    raise typer.Exit(0 if receipt.status in ("VERIFIED", "DUPLICATE") else 1)


if __name__ == "__main__":
    app()
