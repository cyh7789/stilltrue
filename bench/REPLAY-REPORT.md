# Benchmark: 41 months of NYC TLC schema history, replayed

> Regenerate: `python3 bench/oracles/scan_tlc.py` then `python3 bench/oracles/replay_tlc.py --months 41`
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
| Months replayed | **41** (2023-01 → 2026-05, every month the TLC has published) |
| Months scored exactly right | **41/41** |
| False alarms | **0** |

Broken out, because "41/41" on its own suggests more variety than there is:

| | |
|---|---|
| Quiet before anything happened (2023-01) | 1/1 |
| The rename caught in the month it happened (2023-02) | 1/1 |
| Still reported every month after, never withdrawn | 39/39 |

**What this harness does not score.** The TLC's other 2025-01 change was an
*addition* — `cbd_congestion_fee` — with nothing removed. `expected_state()`
unions the `removed` fields only, and the run keeps `D1_SCHEMA_BREAK` findings
only, so that month's score is just the `airport_fee` state being right again.
An earlier version of this table called that "drift caught in the month it
happened: 2/2", which counted an event the harness never looked at. The
undocumented-column detector does fire on `cbd_congestion_fee` — visible in
`docs/L3-EVIDENCE.md` — but it is not scored here.

Scored on *state*, not events. `airport_fee` was renamed in February 2023 and
the description was never corrected, so the right answer is to report it in
2023-02 **and in every month after** — reporting it once and going quiet would be
a failure. The detector has to produce exactly the right set 41 times, not twice.

```
OK   2023-01  expected -                asserted -
OK * 2023-02  expected ['airport_fee']  asserted ['airport_fee']
OK   2023-03  expected ['airport_fee']  asserted ['airport_fee']
     …
OK * 2025-01  expected ['airport_fee']  asserted ['airport_fee']
OK   2026-05  expected ['airport_fee']  asserted ['airport_fee']
```

## What the evidence looks like

The claim is not "this identifier looks unresolved". It is DataHub's own record,
quoted verbatim, with the successor's name taken from the current schema:

```
DataHub's change log records it leaving at v9.0.0-computed: A forwards &
backwards compatible change due to renaming of the field 'airport_fee to
cbd_congestion_fee'.; the schema now has `Airport_fee`
```

**DataHub is half wrong there and the quote is left as it came.** `airport_fee`
was not renamed to `cbd_congestion_fee`; DataHub's differ matches schema versions
by position, so a month that drops one column, renames another and appends a
third emits renames nobody performed. The half the log is reliable for is that
`airport_fee` left at that version, and that is the only half an assertion rests
on — the successor comes from the current schema. `vanished_fields()` further
drops any claimed departure whose field is still present, which removes the
phantom side of the differ's output.

For a deletion with no successor the reality reads as the log alone:

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
check whether the prose kept up. 41 consecutive correct decisions is a different
kind of evidence from a single snapshot score.

**Where 41 comes from**, and a mistake worth recording. It is every month the
TLC has published as of this run: 2026-05 is the last one, 2026-06 is not there
yet. An earlier run of this harness reported 31 months and said the rest were
"not yet published" — that was wrong, and the way it was wrong is the same
mistake this whole project is about. `fsspec` raises `FileNotFoundError` for a
rate limit and for a missing file alike, and the S3 origin behind this
CloudFront has no ListBucket permission, so even a file that does not exist
answers 403 rather than 404. The status code cannot separate them. `is_published()`
does it with a sentinel: ask for `2023-01` too, and if that is also unreachable
then nothing can be concluded about any month, so the run stops instead of
writing a rate limit down as a fact about the TLC.

**Why the earlier dbt benchmarks are gone.** Three dbt packages were scored
before this and their numbers are not comparable, because the labels turned out
not to measure this. `fivetran/dbt_shopify` labels "descriptions that were later
edited" — and on inspection, in 9 of its 10 identifier-change positives the
referenced token was never a column of that model at either end of the window.
They were enumerated values (`fixed_amount`, `percentage`) and upstream model
names. The old detector scored them by firing on those tokens, which a
label-based oracle credits as a hit. Those corpora are kept in the repo with
that finding recorded; they are no longer headline evidence.
