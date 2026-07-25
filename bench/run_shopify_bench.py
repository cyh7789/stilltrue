#!/usr/bin/env python3
"""Score the detector against the fivetran/dbt_shopify benchmark.

For every Tier A positive, reconstruct the drift window: the description as it
stood at c1 (before anyone fixed it), against the model's columns as the SQL
defined them at c2 (after the code changed, before the docs caught up).

Taking the schema from c1 instead was the first attempt and scored 0/40 -- of
course it did: at c1 the description and the schema still agreed. The drift
lives between the two commits, not at either end.

The system never sees git. It sees exactly what it would see if that state were
sitting in DataHub today.

Usage:
  python3 bench/run_shopify_bench.py <path-to-dbt_shopify-clone>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "src"))

from oracles.mine_drift_labels import sql_columns_at  # noqa: E402
from stilltrue.detectors import detect_schema_break  # noqa: E402

TIER_A = ("IDENTIFIER_CHANGE", "DEPRECATION")

# detect_schema_break compares identifiers named in prose against the schema.
# DEPRECATION positives are a description gaining an "(DEPRECATED)" marker --
# 17 of those 30 name no identifier at all, so there is nothing for this
# detector to compare. Scored separately rather than diluting one denominator
# with a category the detector structurally cannot address.
SCORED_AGAINST_D1 = ("IDENTIFIER_CHANGE",)


def score_negatives(repo: Path, rows: list[dict], columns_at) -> tuple[int, int, list[dict]]:
    """How often does the detector cry drift on a description that never drifted?

    Recall without this number is half a benchmark. A reader who sees "9/10" and
    no false-positive count will assume precision is clean, so leaving it
    unmeasured states a claim nobody wrote down.

    A negative is a column whose description survived the window unchanged. It is
    reconstructed exactly like a positive -- same schema source, same field
    shape -- so the two numbers come off the same machinery.
    """
    false_positives, scored = [], 0
    for r in rows:
        # A negative carries one commit, not a window: the description never
        # moved, so the state to reconstruct is the schema alongside it.
        cols = columns_at(r["commit"], r["model"])
        if not cols or r["column"] not in cols:
            continue        # same skip as the positives: SQL not resolvable there
        scored += 1
        fields = [
            {
                "fieldPath": c,
                "description": r["description"] if c == r["column"] else "",
                "nativeDataType": "unknown",
            }
            for c in sorted(cols)
        ]
        urn = f"urn:li:dataset:(urn:li:dataPlatform:dbt,shopify.{r['model']},PROD)"
        found = detect_schema_break(urn, "", fields, ["ev_bench"])
        if any(f.category == "D1_SCHEMA_BREAK" and f.verdict == "DRIFT" for f in found):
            false_positives.append(r)
    return scored, len(false_positives), false_positives


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    repo = Path(sys.argv[1])
    rows = [json.loads(l) for l in (ROOT / "oracles" / "drift-labels-dbt-shopify.jsonl").read_text().splitlines() if l]
    tier_a = [r for r in rows if r.get("category") in TIER_A]

    # sql_columns_at shells out to git; the 2,496 negatives collapse onto far
    # fewer (commit, model) pairs, so without this the negative pass dominates
    # the runtime.
    _col_cache: dict[tuple[str, str], frozenset] = {}

    def columns_at(commit: str, model: str):
        key = (commit, model)
        if key not in _col_cache:
            _col_cache[key] = frozenset(sql_columns_at(repo, commit, model) or ())
        return _col_cache[key]

    # Three outcomes, not two. Abstaining on the right column is not the same
    # as missing it: the steward still gets pointed at the exact spot, the
    # system just refuses to assert what happened to it.
    caught, flagged, missed, no_schema = [], [], [], []
    for r in tier_a:
        # Schema from c2: the code has already changed, the description has not
        cols = columns_at(r["c2"], r["model"])
        if not cols:
            no_schema.append(r)
            continue
        # Reconstruct the dataset as DataHub would hold it inside the drift
        # window. The drifted text is that *column's own* description, not the
        # table's -- attaching it to the table was the second scoring bug here.
        # The documented column may no longer be produced by the SQL at c2 --
        # that is exactly what a rename looks like from the catalog's side. dbt
        # keeps the yml entry (and DataHub ingests it from the manifest), so the
        # description is still attached to a field that reality no longer has.
        # Dropping it here silently discarded 18 of 40 positives.
        documented = sorted(cols | {r["column"]})
        fields = [
            {
                "fieldPath": c,
                "description": r["description_at_c1"] if c == r["column"] else "",
                "nativeDataType": "unknown",
            }
            for c in documented
        ]
        urn = f"urn:li:dataset:(urn:li:dataPlatform:dbt,shopify.{r['model']},PROD)"
        found = detect_schema_break(urn, "", fields, ["ev_bench"])
        breaks = [f for f in found if f.category == "D1_SCHEMA_BREAK"]
        if any(f.verdict == "DRIFT" for f in breaks):
            caught.append(r)
        elif breaks:
            flagged.append(r)
        else:
            missed.append(r)

    scorable = len(caught) + len(flagged) + len(missed)
    print(f"Tier A positives: {len(tier_a)}")
    print(f"  scorable (model SQL resolvable at c2): {scorable}")
    print(f"  skipped (no SQL found at c2):          {len(no_schema)}")
    print()
    pct = (lambda n: f"  ({n/scorable:.0%})" if scorable else "")
    print(f"  asserted as DRIFT:        {len(caught)}/{scorable}{pct(len(caught))}")
    print(f"  flagged but abstained:    {len(flagged)}/{scorable}{pct(len(flagged))}")
    print(f"  no finding at all:        {len(missed)}/{scorable}{pct(len(missed))}")
    print()
    print("  by category:")
    for cat in TIER_A:
        c = sum(1 for r in caught if r["category"] == cat)
        fl = sum(1 for r in flagged if r["category"] == cat)
        m = sum(1 for r in missed if r["category"] == cat)
        if c + fl + m:
            print(f"    {cat:20s} drift {c}  abstained {fl}  nothing {m}")

    negatives = [r for r in rows if r.get("label") == "stable"]
    print(f"\n  negatives (description unchanged across the window): {len(negatives)}")
    neg_scored, neg_fp, fp_rows = score_negatives(repo, negatives, columns_at)
    print(f"    scorable:        {neg_scored}")
    print(f"    false positives: {neg_fp}" + (f"  ({neg_fp/neg_scored:.2%})" if neg_scored else ""))
    for r in fp_rows[:3]:
        print(f"      {r['model']}.{r['column']}: {r['description'][:80]}")

    # Write the report so the numbers are reproducible without reading stdout
    d1 = [r for r in caught + flagged + missed if r["category"] in SCORED_AGAINST_D1]
    d1_caught = [r for r in caught if r["category"] in SCORED_AGAINST_D1]
    other = [r for r in caught + flagged + missed if r["category"] not in SCORED_AGAINST_D1]
    other_caught = [r for r in caught if r["category"] not in SCORED_AGAINST_D1]

    report = [
        "# Benchmark: fivetran/dbt_shopify",
        "",
        "> Regenerate with `python3 bench/run_shopify_bench.py <path-to-dbt_shopify-clone>`.",
        "",
        "Labels come from the upstream project's own documentation-fix commits, not from us.",
        "For each positive the drift window is reconstructed: the description as it stood at",
        "c1, against the columns the SQL produced at c2.",
        "",
        "**This is a benchmark, not a holdout.** The label miner was written before any",
        "detector existed, but the scoring run then changed `detectors.py`: the branch",
        "that treats a field description differently from a table description was chosen",
        "because 9 of 10 identifier-change positives live there. See",
        "[`docs/VALIDATION-INTEGRITY.md`](../docs/VALIDATION-INTEGRITY.md).",
        "",
        "## Where this detector applies",
        "",
        f"| Category | Detected | Total | Applies to `detect_schema_break` |",
        f"|---|---|---|---|",
        f"| IDENTIFIER_CHANGE | **{len(d1_caught)}** | {len(d1)} | yes — the prose names a field that the schema no longer has |",
        f"| DEPRECATION | {len(other_caught)} | {len(other)} | no — see below |",
        "",
        "## False positives on the negatives",
        "",
        f"| Negatives | Scorable | Asserted DRIFT (false positive) |",
        f"|---|---|---|",
        f"| {len(negatives)} | {neg_scored} | **{neg_fp}** ({neg_fp/neg_scored:.2%}) |"
        if neg_scored else "| — | 0 | not scorable |",
        "",
        "A negative is a column whose description survived the window unchanged, so any",
        "DRIFT verdict on one is wrong. Recall without this number is half a benchmark: a",
        "reader seeing only 9/10 would assume precision is clean.",
        "",
        "The misses are one shape. Descriptions enumerate *values*, and enumerated values",
        "look exactly like column names:",
        "",
        "```",
        "  \"...such as `in_transit`, `label_printed`, `out_for_delivery`...\"",
        "  \"...either `fixed_amount` or `percentage`...\"",
        "  \"...whether the rules are disjunctive (`OR`) or conjunctive (`AND`)...\"",
        "```",
        "",
        "None of those are fields, and none have a near-match in the schema — but they sit",
        "in a *field* description, where the detector treats an unresolved snake_case token",
        "as drift rather than abstaining. That branch is what earns the 9/10; this is what",
        "it costs.",
        "",
        "## Why DEPRECATION is reported separately",
        "",
        "A DEPRECATION positive is a description that later gained a `(DEPRECATED)` marker.",
        "17 of those 30 name no identifier at all, so a detector that compares identifiers",
        "against a schema has nothing to work with. Folding them into one denominator would",
        "understate the detector on the problem it does address and overstate it on the one",
        "it does not. Catching a deprecation state requires a different signal — the",
        "deprecation aspect on the upstream entity — which this detector does not read.",
        "",
        "## Known distortion",
        "",
        "`sql_columns_at` reconstructs a model's columns from its SQL text. That works for",
        "dbt staging models but not for mart models built with `select *` or",
        "`dbt_utils.star()`, where the column list is not in the source at all. Positives on",
        "those models are scored against an incomplete schema and can only lose, never gain.",
    ]
    (ROOT / "SHOPIFY-REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\n-> {ROOT / 'SHOPIFY-REPORT.md'}")

    if caught:
        print("\n  example caught:")
        r = caught[0]
        print(f"    {r['model']}.{r['column']}")
        print(f"      before fix: {r['description_at_c1'][:100]}")
    if flagged:
        print("\n  example flagged-but-abstained:")
        r = flagged[0]
        print(f"    {r['model']}.{r['column']} [{r['category']}]")
        print(f"      before fix: {r['description_at_c1'][:100]}")
    if missed:
        print("\n  example with no finding:")
        r = missed[0]
        print(f"    {r['model']}.{r['column']} [{r['category']}]")
        print(f"      before fix: {r['description_at_c1'][:100]}")


if __name__ == "__main__":
    main()
