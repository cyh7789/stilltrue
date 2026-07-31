# Second holdout, scored through DataHub: fivetran/dbt_microsoft_ads

> Regenerate:
> `python3 bench/run_orphan_bench_datahub.py <clone> bench/oracles/orphaned-dbt-microsoft-ads.jsonl`
> Mutation control: same command with `--mutate-skip-rewrite`.

Selected 2026-07-31 by `bench/select_holdout_v2.py`, which continues the walk
frozen in `bench/freeze.json` (commit `d3e6ccb`) with one more name in the
already-seen set. The declaration was committed before the walk ran:
[`HOLDOUT-v2-DECLARATION.md`](HOLDOUT-v2-DECLARATION.md), commit `8299e28`.
The nine frozen files were not touched; `bench/freeze.py --check` stays green.

## Why this repository and not another

The alphabet chose it. The walk skipped 20 repositories before it, each with the
threshold it missed printed in the log: `dbt_amazon_ads` (87 commits < 200),
`dbt_apple_store` (188 < 200), `dbt_demo_justin_small` (no licence), and so on.
`dbt_microsoft_ads` is the first that satisfied all six thresholds.

| | |
|---|---|
| Commits | 252 |
| History | 70 months |
| Column descriptions | 877 |
| Mined orphan positives | 12 |
| Mined negatives (descriptions still attached to live columns) | 304 |

## Result

The detector is never handed the answer. Each model's history is replayed into
DataHub, columns as of the earlier commit with the yml descriptions written the
way a person writes them, then the later schema on top, and the detector runs on
whatever `ReadOnlyDataHubAdapter` reads back out of the two aspects.

```
source: dbt_microsoft_ads  (through DataHub at http://localhost:8080)
  orphaned documentation asserted: 12/12
  false alarms on correct documentation: 0/304
  orphans the label file missed (git confirms the departure): 0
  assertions nothing accounts for: 0
```

## The mutation control

Removing the schema rewrite takes the same run to zero. A benchmark that cannot
fail is not evidence, so the failing direction is part of the result:

```
  orphaned documentation asserted: 0/12
    missed: microsoft_ads__ad_group_report.account_name
    missed: microsoft_ads__campaign_report.campaign_id
    …
  false alarms on correct documentation: 0/304
```

## What this number means, and what it does not

It means the mechanism transfers to a source the system has never read: 12
orphaned descriptions found in a 877-description repository, no false alarms
across 304 correct ones. Combined with the first holdout
([`dbt_iterable`](HOLDOUT-orphan-iterable-datahub.md), 2/2 and 0/199), that is
**14 positives and 0 false alarms across 503 negatives, on two repositories
neither the code nor its author had opened.**

It does not establish a rate for catalogs in general. Two repositories from one
organisation, both dbt, both mined by the same script. The population the
selection rule draws from is `fivetran/dbt_*`, and every claim here is bounded
by that.
