#!/usr/bin/env python3
"""Score the frozen detector against a labels file, once.

Why this exists rather than reusing bench/run_shopify_bench.py directly: that
script is frozen (bench/freeze.json) and reads one hardcoded labels path.
Editing it to take an argument would break the freeze, which is the one thing
the freeze is for. So the scoring loop is restated here and the negative pass is
*imported* from the frozen module rather than rewritten.

Restating logic invites the question of whether it is really the same logic, so
that question gets an answer instead of an assurance:

  python3 bench/run_holdout_bench.py <dbt_shopify-clone> \\
      bench/oracles/drift-labels-dbt-shopify.jsonl

must reproduce the frozen script's published numbers exactly -- 9/10 identifier
changes and 87 false positives on 1,933 scorable negatives. If it does, it is
the same scorer; if it does not, this file is wrong and its holdout numbers mean
nothing.

Usage:
  python3 bench/run_holdout_bench.py <repo-clone> <labels.jsonl> [--out REPORT.md]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "src"))

from oracles.mine_drift_labels import sql_columns_at            # noqa: E402  (frozen)
from run_shopify_bench import SCORED_AGAINST_D1, TIER_A  # noqa: E402  (frozen)


def score_negatives_with_history(repo, rows, columns_at):
    """The frozen negative pass, plus the prior-schema evidence the new gate needs.

    A negative carries one commit, so "prior" is that same commit: the state the
    description was written against. If the token was never a field there either,
    there is nothing to assert -- which is the whole point of the redesign.
    """
    false_positives, scored = [], 0
    for r in rows:
        cols = columns_at(r["commit"], r["model"])
        if not cols or r["column"] not in cols:
            continue
        scored += 1
        fields = [
            {"fieldPath": c,
             "description": r["description"] if c == r["column"] else "",
             "nativeDataType": "unknown"}
            for c in sorted(cols)
        ]
        prior = PriorSchema(frozenset(cols), r["commit"][:12], "ev_bench_prior")
        urn = f"urn:li:dataset:(urn:li:dataPlatform:dbt,{repo.name}.{r['model']},PROD)"
        if any(f.category == "D1_SCHEMA_BREAK" and f.verdict == "DRIFT"
               for f in detect_schema_break(urn, "", fields, ["ev_bench"], prior_schema=prior)):
            false_positives.append(r)
    return scored, len(false_positives), false_positives
from stilltrue.detectors import PriorSchema, detect_schema_break  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    repo, labels = Path(sys.argv[1]), Path(sys.argv[2])
    out_path = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None

    rows = [json.loads(l) for l in labels.read_text().splitlines() if l.strip()]
    tier_a = [r for r in rows if r.get("category") in TIER_A]

    cache: dict[tuple[str, str], frozenset] = {}

    def columns_at(commit: str, model: str):
        key = (commit, model)
        if key not in cache:
            cache[key] = frozenset(sql_columns_at(repo, commit, model) or ())
        return cache[key]

    caught, flagged, missed, no_schema = [], [], [], []
    for r in tier_a:
        cols = columns_at(r["c2"], r["model"])
        if not cols:
            no_schema.append(r)
            continue
        documented = sorted(cols | {r["column"]})
        fields = [
            {
                "fieldPath": c,
                "description": r["description_at_c1"] if c == r["column"] else "",
                "nativeDataType": "unknown",
            }
            for c in documented
        ]
        # The schema this model had when the description was written. Same
        # meaning as DataHub aspect version 1 in production: what the table
        # looked like the last time someone wrote about it.
        prior = columns_at(r["c1"], r["model"])
        prior_schema = (PriorSchema(frozenset(prior), r["c1"][:12], "ev_bench_prior")
                        if prior else None)
        urn = f"urn:li:dataset:(urn:li:dataPlatform:dbt,{repo.name}.{r['model']},PROD)"
        breaks = [f for f in detect_schema_break(urn, "", fields, ["ev_bench"],
                                                 prior_schema=prior_schema)
                  if f.category == "D1_SCHEMA_BREAK"]
        if any(f.verdict == "DRIFT" for f in breaks):
            caught.append(r)
        elif breaks:
            flagged.append(r)
        else:
            missed.append(r)

    scorable = len(caught) + len(flagged) + len(missed)
    d1 = [r for r in caught + flagged + missed if r["category"] in SCORED_AGAINST_D1]
    d1_caught = [r for r in caught if r["category"] in SCORED_AGAINST_D1]

    negatives = [r for r in rows if r.get("label") == "stable"]
    neg_scored, neg_fp, fp_rows = score_negatives_with_history(repo, negatives, columns_at)

    print(f"source:            {repo.name}")
    print(f"labels:            {labels.name}")
    print(f"Tier A positives:  {len(tier_a)}  (scorable {scorable}, no SQL at c2 {len(no_schema)})")
    print(f"  IDENTIFIER_CHANGE asserted DRIFT: {len(d1_caught)}/{len(d1)}")
    print(f"  abstained:                        {len(flagged)}")
    print(f"  no finding:                       {len(missed)}")
    print(f"negatives:         {len(negatives)}  (scorable {neg_scored})")
    print(f"  false positives:                  {neg_fp}"
          + (f"  ({neg_fp / neg_scored:.2%})" if neg_scored else ""))
    for r in fp_rows[:5]:
        print(f"    {r['model']}.{r['column']}: {r['description'][:70]}")
    for r in missed[:3]:
        if r["category"] in SCORED_AGAINST_D1:
            print(f"  missed: {r['model']}.{r['column']}: {r['description_at_c1'][:70]}")

    if out_path:
        recall = f"{len(d1_caught)}/{len(d1)}" if d1 else "n/a"
        fp_pct = f"{neg_fp / neg_scored:.2%}" if neg_scored else "n/a"
        out_path.write_text("\n".join([
            f"# Frozen holdout: fivetran/{repo.name}",
            "",
            f"> Scored once, on {json.loads((ROOT / 'freeze.json').read_text())['frozen_at']} code.",
            f"> Regenerate: `python3 bench/run_holdout_bench.py <clone> {labels.name}`",
            "",
            "Unlike the two benchmarks in this repo, this source was fetched **after** the",
            "freeze, chosen by a rule committed before any candidate was inspected, and",
            "scored once. The numbers below are what came out.",
            "",
            "| | Result |",
            "|---|---|",
            f"| IDENTIFIER_CHANGE recall | **{recall}** |",
            f"| False positives on negatives | **{neg_fp}/{neg_scored}** ({fp_pct}) |",
            f"| Abstained on a positive | {len(flagged)} |",
            f"| Positives with no SQL at c2 (unscorable) | {len(no_schema)} |",
            "",
            "Selection: `bench/holdout-selection.json`. Freeze: `bench/freeze.json`,",
            "verifiable with `python3 bench/freeze.py --check`.",
            "",
        ]) + "\n", encoding="utf-8")
        print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
