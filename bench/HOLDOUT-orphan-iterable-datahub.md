# Orphaned documentation, scored through DataHub: fivetran/dbt_iterable

> Regenerate: `python3 bench/run_orphan_bench_datahub.py <clone> orphaned-dbt-iterable.jsonl`

The detector is never handed the answer here. Each model's history is
replayed into DataHub -- columns as of the earlier commit, the yml
descriptions written the way a person writes them, then the later
schema on top -- and the detector runs on whatever
`ReadOnlyDataHubAdapter` reads back out of the two aspects.

| | Result |
|---|---|
| Orphaned documentation asserted | **2/2** |
| False alarms on correct documentation | **0/199** |

## Checking that this benchmark can fail

The previous harness reported the same figures while being unable to
produce any others: it handed the detector the labelled column, the
labelled description and the after-schema, which is the detector's own
decision rule restated. Matching numbers therefore prove nothing on
their own, so here is the mutation:

```
python3 bench/run_orphan_bench_datahub.py <clone> <labels> --mutate-skip-rewrite
```

That drops the second ingestion -- the one that takes the column out of
the schema. Nothing is orphaned without it and the score has to go to
zero. It does:

| run | orphaned documentation asserted |
|---|---|
| normal | 2/2 |
| `--mutate-skip-rewrite` | 0/2 |

The old harness returns the same 2/2 under that mutation, because it
never asks DataHub anything.

