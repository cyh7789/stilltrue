# Second holdout: the declaration, written before the walk

Committed 2026-07-31, before `bench/select_holdout_v2.py` was run for the first
time. Nothing below was written with a result in hand.

## Why a second one

The first holdout (`fivetran/dbt_iterable`) carries 2 positives. It shows the
mechanism transfers to a source the system never saw; it cannot support a rate.
This walk exists to raise that count, and it is worth stating plainly that the
motive is a number we already know is thin.

## What is not being changed

- The selection rule stays where it was frozen: `bench/freeze.json`,
  `selection_rule`, commit `d3e6ccb`.
- The nine frozen files stay untouched. `bench/freeze.py --check` must remain
  green through this exercise; if it goes red, the exercise is invalid.
- `bench/select_holdout.py` is one of the nine, so the v2 walk imports it rather
  than editing it. The thresholds cannot drift apart because there is only one
  copy of them.

## The one thing that changes

`dbt_iterable` joins the already-seen exclusion set. It was selected by the v1
walk and scored; a source the system has been graded on cannot grade it again.
Everything else about the walk is identical: fivetran repositories whose name
starts with `dbt_`, alphabetical order, take the first that satisfies every
threshold (Apache-2.0/MIT/BSD, >= 200 commits, >= 12 months of history, >= 50
column descriptions, >= 30 mined positives, >= 100 mined negatives).

## What counts as the result

Whatever repository the walk stops on. Not the best of several, not a second
attempt if the first is unflattering. The run prints every rejection with the
threshold it missed, so the walk is auditable end to end.

Scoring uses the existing frozen harness with no arguments changed:

```
python3 bench/run_orphan_bench_datahub.py <clone> bench/oracles/orphaned-<repo>.jsonl
python3 bench/run_orphan_bench_datahub.py <clone> bench/oracles/orphaned-<repo>.jsonl --mutate-skip-rewrite
```

The mutation run is part of the result, not an optional extra: a benchmark that
cannot fail is not evidence.

## What the number will and will not mean

If the count of positives is again small, the report says so and the claim stays
"the mechanism transfers", not "the rate is X". The v1 report was written that
way and this one inherits the constraint. The failure mode being guarded against
is the one this project already committed once and documented in
`docs/VALIDATION-INTEGRITY.md`: letting a number acquire a stronger name than
the process that produced it.
