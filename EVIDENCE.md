# Three minutes, no install: every claim and the file it comes from

Nothing here asks you to run anything. Each row names the artefact in this
repository that produced it, and the artefacts cross-reference each other: the
run id in the ledger is the run id in the findings file is the run id quoted in
the walkthrough. If you would rather run it, `make codespace-demo` or
[`README.md`](README.md#try-it-without-installing-anything).

## 1. The fault, in one frame of DataHub's own UI

| | |
|---|---|
| The schema says `Airport_fee` | [`docs/evidence/02-before-columns.png`](docs/evidence/02-before-columns.png), Columns tab |
| The documentation on the same page says `airport_fee` | same file, Summary panel on the right |
| After the agent's write | [`docs/evidence/04-after-columns.png`](docs/evidence/04-after-columns.png) |

The rename is real and it is not ours: the NYC TLC renamed the column in
February 2023 and added `cbd_congestion_fee` in January 2025. Both are derived
by diffing the TLC's own published parquet schemas month over month
([`bench/oracles/scan_tlc.py`](bench/oracles/scan_tlc.py)), so the labels are
the TLC's, not ours.

## 2. The gate, as ten records in one hash chain

Run `94b7e03ee841`, complete ledger at
[`docs/evidence/run-94b7e03ee841/audit-ledger.jsonl`](docs/evidence/run-94b7e03ee841/audit-ledger.jsonl):

| # | stage | entry hash | outcome | proposal |
|---|---|---|---|---|
| 1 | scan | `ef2de1e014b7` | | |
| 2 | propose | `49fe1eac964b` | | `a844edb7f3b9` |
| 3 | approve | `10b4ea0d4dd1` | **NOT_APPROVED** | `a844edb7f3b9` |
| 4 | propose | `220ea4e7265a` | | `a844edb7f3b9` |
| 5 | approve | `acddfad21955` | **NOT_APPROVED** | `a844edb7f3b9` |
| 6 | propose | `e660fabba6bf` | | `ec39d56f76df` |
| 7 | approve | `4f9edb4b3642` | **STALE** | `ec39d56f76df` |
| 8 | propose | `808f5f3cab04` | | `a844edb7f3b9` |
| 9 | approve | `6c72cbcd9b78` | APPROVED | `a844edb7f3b9` |
| 10 | execute | `160f5ef2d8fa` | **VERIFIED** | `a844edb7f3b9` |

Row 7 is the one worth reading twice. The confirmation token `a844edb7f3b9` was
issued for one piece of text; the write that arrived carried a different text,
so its proposal hashed to `ec39d56f76df` and the token no longer matched. The
write failed closed. A ledger that recorded only successful writes would be a
changelog, so the two refusals are in the chain with everything else.

`stilltrue verify --run 94b7e03ee841` recomputes the chain and prints
`OK: chain valid (10 records)`.

## 3. The write, recorded by DataHub rather than by us

The correction appears in DataHub's own documentation timeline, the same
service the detector reads its evidence from. Command and unedited response:
[`docs/L3-EVIDENCE.md`](docs/L3-EVIDENCE.md) section 6.

```
category: DOCUMENTATION   operation: MODIFY
Documentation of 'urn:li:dataset:(...nyc_tlc.yellow_tripdata,PROD)' has been changed
  from '...improvement_surcharge; airport_fee applies to LGA and JFK pickups only. ...'
  to   '...improvement_surcharge; Airport_fee applies to LGA and JFK pickups only. ...'
```

## 4. The fault with no pixels

A rename can leave a column description attached to a field that no longer
exists. No row renders it, and the Agent Context Kit drops the aspect
([`datahub#18628`](https://github.com/datahub-project/datahub/pull/18628) is the
fix for the second half of that sentence). Removing it changes almost nothing on
screen, which is the point, so the proof is a pixel diff of two captures taken by
the same script before and after:

```
1440x900, 1296000 pixels
differing pixels: 168  (0.0130%)
all differences inside x 76-774, y 90-264
```

Reproduce: [`scripts/prove_invisible.sh`](scripts/prove_invisible.sh). The
region that differs is the version chip's clock, not the note.

## 5. The numbers, and the denominator under each one

| Claim | Denominator | Where |
|---|---|---|
| 11 drifted, 12 still true, 58 abstained | 81 checks over 77 datasets | [`docs/L3-EVIDENCE.md`](docs/L3-EVIDENCE.md) |
| 1 drift, 6 current, 29 abstained, zero false drift | 36 checks over 25 tables | [`examples/abstention/`](examples/abstention/) |
| 6 false verdicts without the change-log requirement, 0 with it | the same 25 tables | [`README.md`](README.md) |
| 41 months scored exactly right, 0 false alarms | 41 consecutive months, 2023-01 to 2026-05 | [`bench/REPLAY-REPORT.md`](bench/REPLAY-REPORT.md) |
| 2 orphans found of 2, 0 false alarms | 199 correct descriptions | [`bench/HOLDOUT-orphan-iterable-datahub.md`](bench/HOLDOUT-orphan-iterable-datahub.md) |
| 12 orphans found of 12, 0 false alarms | 304 correct descriptions | [`bench/HOLDOUT-orphan-microsoft-ads-datahub.md`](bench/HOLDOUT-orphan-microsoft-ads-datahub.md) |
| A coverage check finds 1 of the 2 | the same dataset | [`bench/REPORT.md`](bench/REPORT.md) |

Both holdout repositories were chosen by a rule frozen before the search ran
([`bench/freeze.json`](bench/freeze.json), commit `d3e6ccb`; the second walk's
declaration is [`bench/HOLDOUT-v2-DECLARATION.md`](bench/HOLDOUT-v2-DECLARATION.md),
committed before it was run). Both benchmarks ship with `--mutate-skip-rewrite`,
which removes the schema rewrite and takes the score to zero. A benchmark that
cannot fail is not evidence.

## 6. What is deliberately not claimed

- The TLC replay was once described as a holdout. It is not one: the code was
  changed after seeing its scores. It is a third-party benchmark, and the
  timeline of who knew what when is written down in
  [`docs/VALIDATION-INTEGRITY.md`](docs/VALIDATION-INTEGRITY.md).
- The official DataHub datapacks are the development set, so the 77-dataset scan
  is scale, not generalisation.
- Two repositories from one organisation, both dbt, both mined by the same
  script. That is what the 14/14 rests on.
- D2 (freshness) and D5 (semantic conflict) are not implemented. The reason is a
  measurement, not a shrug: [`docs/D2-FEASIBILITY.md`](docs/D2-FEASIBILITY.md).
- The four upstream pull requests are open, not merged.
