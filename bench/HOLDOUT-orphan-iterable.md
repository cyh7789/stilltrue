# Orphaned-documentation benchmark: fivetran/dbt_iterable

> Regenerate: `python3 bench/run_orphan_bench.py <clone> orphaned-dbt-iterable.jsonl`

A column left the model's SQL and its description stayed in the yml. That is
the fact this detector decides, and git records it without anyone judging
intent -- unlike "descriptions that were later edited", which is what the
earlier oracle labelled and which turned out to measure something else.

| | Result |
|---|---|
| Orphaned documentation asserted | **2/2** |
| False alarms on correct documentation | **0/199** |

## How it was kept honest

| | |
|---|---|
| Selection rule committed | before any candidate was inspected (`bench/freeze.json`) |
| Graded files hashed | before the source was fetched — `python3 bench/freeze.py --check` |
| Walk | 16 repositories rejected, each with a mechanical reason |
| Runs | one |

Every source touched in any earlier round is on the exclusion list, including
ones only cloned to test a threshold.

**One inconsistency, recorded rather than smoothed over.** The selection rule's
`mined_positives >= 30` threshold is evaluated by `select_holdout.py` using the
*previous* oracle, which counts documentation edits rather than orphaned
documentation. The rule was frozen before this round and applied mechanically,
so it stands as written; but it means the threshold that admitted
`dbt_iterable` measured something other than what was then scored. The
consequence is visible in the denominator: 2 positives, not 30.

## What 2/2 does and does not establish

Two positives is a small denominator and the result is stated as such. What it
shows is that the mechanism transfers: a source this code had never seen,
scored once, and both instances of the exact failure it targets were asserted
with no false alarm across 199 correctly documented columns.

What it cannot show is a rate. For that the positives would have to be far more
numerous, and orphaned documentation appears to be genuinely rare in
well-maintained dbt packages — 4 in dbt_hubspot, 2 here. That rarity is itself
worth reporting: the failure mode is real, verifiable and quiet, not common.
