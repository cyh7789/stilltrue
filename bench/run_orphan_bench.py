#!/usr/bin/env python3
"""Score the detector against orphaned-documentation labels from a dbt repo.

The detector's evidence in production is DataHub's change log: "this field left
the dataset at version X". A dbt repo carries the same fact in its git history --
the column was in the model's SQL at one commit and gone at the next. So the
harness supplies it as `vanished`, which is the same statement from a different
record-keeper, not a benchmark-only privilege.

Positives: the column left the SQL and its yml description outlived it. The
detector must assert.
Negatives: the column is in both the SQL and the yml. The detector must not.

Usage:
  python3 bench/run_orphan_bench.py <repo-clone> <labels.jsonl> [--out REPORT.md]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "oracles"))
sys.path.insert(0, str(ROOT.parent / "src"))

from oracles.mine_drift_labels import sql_columns_at  # noqa: E402

from stilltrue.detectors import VanishedField, detect_schema_break  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    repo, labels = Path(sys.argv[1]), Path(sys.argv[2])
    out_path = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None

    rows = [json.loads(line) for line in labels.read_text().splitlines() if line.strip()]
    cache: dict[tuple[str, str], frozenset] = {}

    def columns_at(commit: str, model: str) -> frozenset:
        key = (commit, model)
        if key not in cache:
            cache[key] = frozenset(sql_columns_at(repo, commit, model) or ())
        return cache[key]

    def asserts_drift(model: str, column: str, description: str,
                      schema: frozenset, vanished: dict) -> bool:
        # The dataset as DataHub would hold it: the surviving columns, with the
        # orphaned description still attached to the column it describes.
        fields = [{"fieldPath": c, "description": "", "nativeDataType": "unknown"}
                  for c in sorted(schema)]
        fields.append({"fieldPath": column, "description": description,
                       "nativeDataType": "unknown"})
        urn = f"urn:li:dataset:(urn:li:dataPlatform:dbt,{repo.name}.{model},PROD)"
        found = detect_schema_break(urn, "", fields, ["ev_bench"], vanished=vanished)
        return any(f.category == "D1_SCHEMA_BREAK" and f.verdict == "DRIFT" for f in found)

    caught, missed = [], []
    for r in [x for x in rows if x["label"] == "orphaned"]:
        before = columns_at(r["c1"], r["model"])
        after = columns_at(r["c2"], r["model"])
        if not before or not after:
            continue
        gone = {
            name: VanishedField(name=name, operation="REMOVE", observed_at=0,
                                semantic_version="(git)",
                                datahub_says=f"column left the SQL at {r['c2'][:12]}")
            for name in before - after
        }
        (caught if asserts_drift(r["model"], r["column"], r["description"], after, gone)
         else missed).append(r)

    quiet, false_alarms = [], []
    for r in [x for x in rows if x["label"] == "current"]:
        schema = columns_at(r["commit"], r["model"])
        if not schema:
            continue
        # Nothing left this model at this commit, so there is nothing to assert.
        (false_alarms if asserts_drift(r["model"], r["column"], r["description"], schema, {})
         else quiet).append(r)

    pos, neg = len(caught) + len(missed), len(quiet) + len(false_alarms)
    print(f"source: {repo.name}")
    print(f"  orphaned documentation: {len(caught)}/{pos} asserted")
    for r in missed:
        print(f"    missed: {r['model']}.{r['column']}: {r['description'][:70]}")
    print(f"  correct documentation:  {len(false_alarms)}/{neg} false alarms")
    for r in false_alarms[:5]:
        print(f"    false alarm: {r['model']}.{r['column']}: {r['description'][:70]}")

    if out_path:
        out_path.write_text("\n".join([
            f"# Orphaned-documentation benchmark: fivetran/{repo.name}",
            "",
            f"> Regenerate: `python3 bench/run_orphan_bench.py <clone> {labels.name}`",
            "",
            "A column left the model's SQL and its description stayed in the yml. That is",
            "the fact this detector decides, and git records it without anyone judging",
            "intent -- unlike \"descriptions that were later edited\", which is what the",
            "earlier oracle labelled and which turned out to measure something else.",
            "",
            "| | Result |",
            "|---|---|",
            f"| Orphaned documentation asserted | **{len(caught)}/{pos}** |",
            f"| False alarms on correct documentation | **{len(false_alarms)}/{neg}** |",
            "",
        ]) + "\n", encoding="utf-8")
        print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
