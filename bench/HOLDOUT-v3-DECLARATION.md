# Third holdout: what is being changed, and what is not

Written and committed before the walk ran. Same discipline as
[`HOLDOUT-v2-DECLARATION.md`](HOLDOUT-v2-DECLARATION.md).

## Why a third one at all

The first two holdouts are `fivetran/dbt_iterable` and
`fivetran/dbt_microsoft_ads`. Both are dbt packages, both from one organisation,
both mined by the same script. 14 positives found of 14, no false alarms across
503 correct descriptions, and every one of those numbers comes from inside a
single company's dbt style. The fair reading of that is "the mechanism transfers
between two repositories written by the same people," which is a weaker claim
than the numbers look.

This walk attacks the narrowest of the three axes: the organisation.

## What is not changed

- **The six thresholds are the frozen ones**, imported from
  `bench/select_holdout.py` rather than restated: licence in {Apache-2.0, MIT,
  BSD-2, BSD-3}, at least 200 commits, at least 12 months of history, at least
  50 column descriptions, at least 30 mined positives, at least 100 mined
  negatives.
- **The miner is the frozen `mine_drift_labels.py`**, invoked as a subprocess,
  unmodified. Running a script that was written and frozen before this corpus
  was chosen, over a corpus it was not developed on, is the point. A new miner
  written for a new source could be tuned to it; this one cannot.
- **The scorer is the frozen `run_orphan_bench_datahub.py`**, replaying through
  a live DataHub and reading back through the adapter.
- **None of the nine frozen files is edited.** `bench/freeze.py --check` stays
  green. The new selector is a separate file, `bench/select_holdout_v3.py`.

## The one change: the population

| | v1 and v2 | v3 |
|---|---|---|
| Population | public non-archived repos under `github.com/fivetran` whose name starts with `dbt_` | public non-archived repos under the organisations below whose name contains `dbt`, case-insensitive |
| Order | alphabetical by repository name | alphabetical by `owner/name` |
| Take | first that satisfies every threshold | same |

Organisations, fixed here before any of them was cloned or mined, chosen only
because each publishes more than one public dbt package and none is fivetran:

`brooklyn-data`, `calogica`, `dbt-labs`, `elementary-data`, `infinitelambda`,
`montreal-analytics`

The count of dbt-named repositories per organisation was read from the GitHub
API before writing this file (11, 8, 4, 4, 3, 2 in descending order) to confirm
the population is not empty. Nothing was cloned, no descriptions were counted
and no labels were mined before this file was committed.

## What counts as the result

Whatever repository the walk stops on, and whatever it scores. Not the best of
several. `runs_allowed` is 1, and every rejection is printed with the threshold
it missed, so the walk is auditable the same way the first two were.

**If no candidate satisfies the thresholds, that is the published result.** It
would say something worth knowing: that the corpus shape the first two holdouts
came from is uncommon outside the organisation that produced them, which is a
limit on the claim rather than a reason to widen the rule until something
passes.

## What a positive result would and would not support

It would support: the mechanism transfers across organisations, not only across
two repositories by the same authors.

It would still not support transfer beyond dbt. All three would be dbt packages
with `models/**/*.yml` descriptions, and the orphan phenomenon is legible there
partly because dbt keeps prose and SQL in one repository.

A source outside dbt was probed first and rejected on measurement rather than on
preference. `snowplow/iglu-central` holds 683 versioned JSON schemas and 4,896
field descriptions, but across the entire corpus only 15 fields are removed
between consecutive versions of the same schema, and only 2 of those are still
named by surviving description text, both of them the word "event" in ordinary
prose. Two dubious positives is a weaker corpus than the ones already published,
so it was not pursued. That probe counted schema shapes only; the detector was
never run against it.
