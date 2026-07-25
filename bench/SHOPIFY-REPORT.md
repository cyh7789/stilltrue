# Benchmark: fivetran/dbt_shopify

> Regenerate with `python3 bench/run_shopify_bench.py <path-to-dbt_shopify-clone>`.

Labels come from the upstream project's own documentation-fix commits, not from us.
For each positive the drift window is reconstructed: the description as it stood at
c1, against the columns the SQL produced at c2.

**This is a benchmark, not a holdout.** The label miner was written before any
detector existed, but the scoring run then changed `detectors.py`: the branch
that treats a field description differently from a table description was chosen
because 9 of 10 identifier-change positives live there. See
[`docs/VALIDATION-INTEGRITY.md`](../docs/VALIDATION-INTEGRITY.md).

## Where this detector applies

| Category | Detected | Total | Applies to `detect_schema_break` |
|---|---|---|---|
| IDENTIFIER_CHANGE | **9** | 10 | yes — the prose names a field that the schema no longer has |
| DEPRECATION | 6 | 30 | no — see below |

## False positives on the negatives

| Negatives | Scorable | Asserted DRIFT (false positive) |
|---|---|---|
| 2496 | 1933 | **87** (4.50%) |

A negative is a column whose description survived the window unchanged, so any
DRIFT verdict on one is wrong. Recall without this number is half a benchmark: a
reader seeing only 9/10 would assume precision is clean.

The misses are one shape. Descriptions enumerate *values*, and enumerated values
look exactly like column names:

```
  "...such as `in_transit`, `label_printed`, `out_for_delivery`..."
  "...either `fixed_amount` or `percentage`..."
  "...whether the rules are disjunctive (`OR`) or conjunctive (`AND`)..."
```

None of those are fields, and none have a near-match in the schema — but they sit
in a *field* description, where the detector treats an unresolved snake_case token
as drift rather than abstaining. That branch is what earns the 9/10; this is what
it costs.

## Why DEPRECATION is reported separately

A DEPRECATION positive is a description that later gained a `(DEPRECATED)` marker.
17 of those 30 name no identifier at all, so a detector that compares identifiers
against a schema has nothing to work with. Folding them into one denominator would
understate the detector on the problem it does address and overstate it on the one
it does not. Catching a deprecation state requires a different signal — the
deprecation aspect on the upstream entity — which this detector does not read.

## Known distortion

`sql_columns_at` reconstructs a model's columns from its SQL text. That works for
dbt staging models but not for mart models built with `select *` or
`dbt_utils.star()`, where the column list is not in the source at all. Positives on
those models are scored against an incomplete schema and can only lose, never gain.
