#!/usr/bin/env python3
"""Run every baseline against the NYC TLC benchmark and write REPORT.md.

The expected set is not hand-written here: it comes from the diff between two
published TLC parquet schemas (see oracles/tlc-drift-events.json), so the same
two events fall out whether or not this project exists.

Usage:
  python3 bench/run_bench.py [--server http://localhost:8080]
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "src"))

BENCHMARK_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)"


def expected_from_oracle() -> set[str]:
    """Derive the expected findings from the published schema diff."""
    events = json.loads((ROOT / "oracles" / "tlc-drift-events.json").read_text())
    expected: set[str] = set()
    for e in events:
        for r in e.get("removed", []):
            expected.add(r)          # renamed away: the description still cites it
        for a in e.get("added", []):
            if a not in {x for ev in events for x in ev.get("case_rename", [])}:
                expected.add(a)      # newly added: nobody documented it
    # case_rename entries appear on both sides; keep the old name only
    for e in events:
        for pair in e.get("case_rename", []):
            old, new = pair.split("->")
            expected.discard(new)
    return expected


def main() -> None:
    server = "http://localhost:8080"
    if "--server" in sys.argv:
        server = sys.argv[sys.argv.index("--server") + 1]

    from baselines import evaluate
    from sentinel.adapter import ReadOnlyDataHubAdapter, authored_description

    expected = expected_from_oracle()

    with ReadOnlyDataHubAdapter(server=server) as adapter:
        entity, _ = adapter.get_entity(BENCHMARK_URN)
        schema, _ = adapter.list_schema_fields(BENCHMARK_URN)

    description = authored_description(entity)
    fields = schema.get("fields", [])
    if not fields:
        print("benchmark not loaded; run bench/oracles/build_tlc_benchmark.py first")
        sys.exit(1)

    scored = evaluate(description, fields, BENCHMARK_URN, expected)

    lines = [
        "# Benchmark: NYC TLC",
        "",
        f"> Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        f"by `bench/run_bench.py`. Rerun it to reproduce every number below.",
        "",
        f"**Expected findings ({len(expected)}):** {', '.join(f'`{e}`' for e in sorted(expected))}",
        "",
        "These are not our labels. They are the difference between the TLC's own",
        "published parquet schemas for 2023-01 and 2025-01, extracted by",
        "`oracles/scan_tlc.py`. Anyone can rerun that script and get the same two",
        "events without running this project at all.",
        "",
        "**This is a benchmark, not a holdout.** It was run during development and",
        "the results changed the code -- this scan returning nothing is what",
        "surfaced the `editableProperties` bug. See",
        "[`docs/VALIDATION-INTEGRITY.md`](../docs/VALIDATION-INTEGRITY.md) for the",
        "timeline and the frozen-holdout claim that was withdrawn.",
        "",
        f"**Denominator:** {len(fields)} fields in the dataset, of which "
        f"{len(fields) - len(expected)} must produce no finding.",
        "",
        "| Baseline | Recall | False positives | Caught | Missed |",
        "|---|---|---|---|---|",
    ]
    for name, r in scored.items():
        caught = ", ".join(f"`{c}`" for c in r["caught"]) or "—"
        missed = ", ".join(f"`{m}`" for m in r["missed"]) or "—"
        lines.append(f"| {name} | {r['recall']} | {r['false_positives']} | {caught} | {missed} |")

    lines += [
        "",
        "## What each baseline shows",
        "",
        "**B0 (no context)** has only the prose. There is nothing to compare it",
        "against, so it cannot report drift at all. This is where every agent",
        "starts before a context platform is wired up.",
        "",
        "**B1 (coverage only)** is what DataHub's own documentation-coverage view",
        "already gives you: which fields lack a description. It finds the",
        "undocumented column and, by construction, can never find a description",
        "that is present but wrong -- it never reads the description.",
        "",
        "**B2 (case-insensitive)** compares prose against schema the way most",
        "people would write it first: lowercase both sides. Normalising the case",
        "erases exactly the difference that constitutes the drift. This is not a",
        "strawman -- it is the bug this project shipped in its own first version,",
        "caught by the TLC regression test.",
        "",
        "## Reproducing",
        "",
        "```bash",
        "datahub docker quickstart",
        "python3 bench/oracles/build_tlc_benchmark.py   # loads the benchmark from public data",
        "python3 bench/run_bench.py                   # regenerates this file",
        "```",
    ]

    out = ROOT / "REPORT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"expected: {sorted(expected)}")
    for name, r in scored.items():
        print(f"  {name:26s} recall {r['recall']}  fp {r['false_positives']}")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
