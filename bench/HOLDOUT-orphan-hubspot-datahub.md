# Orphaned documentation, scored through DataHub: fivetran/dbt_hubspot

> Regenerate: `python3 bench/run_orphan_bench_datahub.py <clone> orphaned-dbt-hubspot.jsonl`

The detector is never handed the answer here. Each model's history is
replayed into DataHub -- columns as of the earlier commit, the yml
descriptions written the way a person writes them, then the later
schema on top -- and the detector runs on whatever
`ReadOnlyDataHubAdapter` reads back out of the two aspects.

| | Result |
|---|---|
| Orphaned documentation asserted | **4/4** |
| False alarms on correct documentation | **0/432** |
| Orphans the label file missed | **4** |
| Assertions nothing accounts for | **0** |

The last two rows exist because scoring only the labelled column would
hide a detector that fires on everything. Anything else the detector
says is checked against the same git history the labels come from: if
the column was in the model's SQL at the earlier commit and gone at the
later one, the assertion is right and the label file simply has no row
for it -- `mine_orphaned_docs.py` dedupes by `(model, column)` and keeps
the first row it built, so a column that is current at one commit and
orphaned at a later one never gets a second entry. Only the final row
would be a false positive.

Each case also gets its own dataset name, keyed to the commits that
define it: `editableSchemaMetadata` is never cleared, so a shared URN
would carry one case's descriptions into the next.

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
| normal | 4/4 |
| `--mutate-skip-rewrite` | 0/2 |

The old harness returns the same 2/2 under that mutation, because it
never asks DataHub anything.

