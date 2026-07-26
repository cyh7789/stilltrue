# Benchmark: 27 months of NYC TLC schema history, replayed

> Regenerate: `python3 bench/oracles/replay_tlc.py --months 35`
> Per-month results: `bench/tlc-replay-results.jsonl`

A description is written once, against the schema as it stood in January 2023,
and never revised. Then the pipeline keeps running: every month's actually
published TLC parquet schema is ingested into DataHub in order. Nobody goes back
to update the docs. That is the whole setup, and it is the ordinary one.

Two things happened in those months, neither announced:

| Month | Event |
|---|---|
| 2023-02 | `airport_fee` renamed to `Airport_fee` |
| 2025-01 | `cbd_congestion_fee` appeared |

Both fall out of the published files. `bench/oracles/scan_tlc.py` derives them by
diffing the parquet schemas month over month, so the labels are the TLC's, not
ours.

## Result

| | |
|---|---|
| Months replayed | **27** (2023-01 → 2025-03; later months not yet published) |
| Months scored exactly right | **27/27** |
| Drift caught in the month it happened | **2/2** |
| False alarms | **0** |

Scored on *state*, not events. `airport_fee` was renamed in February 2023 and
the description was never corrected, so the right answer is to report it in
2023-02 **and in every month after** — reporting it once and going quiet would be
a failure. The detector has to produce exactly the right set 27 times, not twice.

```
OK   2023-01  expected -                asserted -
OK * 2023-02  expected ['airport_fee']  asserted ['airport_fee']
OK   2023-03  expected ['airport_fee']  asserted ['airport_fee']
     …
OK * 2025-01  expected ['airport_fee']  asserted ['airport_fee']
OK   2025-03  expected ['airport_fee']  asserted ['airport_fee']
```

## What the evidence looks like

The claim is not "this identifier looks unresolved". It is DataHub's own record:

```
the schema has no `airport_fee`, but it does have `Airport_fee`
```

and, for deletions with no successor to point at, the change log verbatim:

```
DataHub's change log records it leaving at v1.0.0:
  A backwards incompatible change due to removal of field: 'airport_fee'
```

Every finding carries the evidence id of the `timeline` read that produced it.

## What this is and is not

**It is a development benchmark.** The TLC data shaped this detector — it is
where the `editableProperties` bug surfaced and where the rename rule was
validated. Real published data with mechanical labels is a good benchmark; it is
not a claim of generalisation.

**What it does establish** is that the mechanism works end-to-end on real schema
history: ingest what a real pipeline would ingest, ask DataHub what changed, and
check whether the prose kept up. 27 consecutive correct decisions is a different
kind of evidence from a single snapshot score.

**Why the earlier dbt benchmarks are gone.** Three dbt packages were scored
before this and their numbers are not comparable, because the labels turned out
not to measure this. `fivetran/dbt_shopify` labels "descriptions that were later
edited" — and on inspection, in 9 of its 10 identifier-change positives the
referenced token was never a column of that model at either end of the window.
They were enumerated values (`fixed_amount`, `percentage`) and upstream model
names. The old detector scored them by firing on those tokens, which a
label-based oracle credits as a hit. Those corpora are kept in the repo with
that finding recorded; they are no longer headline evidence.
