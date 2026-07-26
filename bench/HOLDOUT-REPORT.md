# Frozen holdout: fivetran/dbt_fivetran_log

> Scored once, on 2026-07-26T03:21:59+00:00 code.
> Regenerate: `python3 bench/run_holdout_bench.py <clone> drift-labels-dbt-fivetran-log.jsonl`

Unlike the two benchmarks in this repo, this source was fetched **after** the
freeze, chosen by a rule committed before any candidate was inspected, and
scored once. The numbers below are what came out.

| | Result |
|---|---|
| IDENTIFIER_CHANGE recall | **13/32** |
| False positives on negatives | **7/73** (9.59%) |
| Abstained on a positive | 2 |
| Positives with no SQL at c2 (unscorable) | 0 |

Selection: `bench/holdout-selection.json`. Freeze: `bench/freeze.json`,
verifiable with `python3 bench/freeze.py --check`.

---

## What the gap means

*Written after the single scored run. The system was not modified in response —
`python3 bench/freeze.py --check` still passes.*

| | dbt_shopify (development) | dbt_fivetran_log (frozen holdout) |
|---|---|---|
| IDENTIFIER_CHANGE recall | 9/10 — **90%** | 13/32 — **41%** |
| False positives | 87/1,933 — 4.50% | 7/73 — 9.59% |

**Recall halved and false positives doubled.** That gap is the whole reason to
run a holdout: the 90% was measured on the corpus that set the rule, and it does
not transfer. Anyone quoting the 90% alone would be quoting a fitted number.

The rule in question is the branch that asserts drift when a *field* description
names an unresolved identifier. It was chosen because 9 of 10 dbt_shopify
identifier changes lived there
([`docs/VALIDATION-INTEGRITY.md`](../docs/VALIDATION-INTEGRITY.md)). On a corpus
it never saw, that same branch finds under half.

## Where it goes wrong here, unfixed

The false positives are two shapes, one familiar and one new:

```
connection_health          "...status of the connection. Possible values..."   enumerated values
account_membership.account_id  "Foreign key referencing the ID of the `account`..."  another table
write_to_table_start_day   "The `write_to_table_start` field truncated to..."   another model's column
```

The first shape is the one dbt_shopify already showed: descriptions list values,
and a value looks like a column name. The second is new — `dbt_fivetran_log`
writes relational prose, and a foreign-key description naming the table it points
at (`account`, `user`, `destination`) is correct documentation that this detector
reads as a broken field reference. `self_reference_tokens()` covers a table
naming *itself*; it does not cover a table naming its neighbours.

The misses cluster in the same package. `fivetran_platform__connector_status`
accounts for several on its own: its descriptions carry quoted status literals
(`"broken"`, `"deleted"`) and JSON fragments, which the identifier extractor
does not treat as references at all, so a genuine rename inside that prose has
nothing to match against.

## Why nothing was changed

Both failure modes are addressable — a cross-model reference check would take
out most of the false positives, and a quoted-literal rule would recover some
misses. Neither was made, because the point of the freeze is that this number
survives being disappointing. A holdout that gets fixed until it agrees with the
development set is a development set.

The number to carry forward is **41%, not 90%**.
