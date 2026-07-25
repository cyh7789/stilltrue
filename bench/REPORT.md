# Benchmark: NYC TLC

> Generated 2026-07-25T18:10:46+00:00 by `bench/run_bench.py`. Rerun it to reproduce every number below.

**Expected findings (2):** `airport_fee`, `cbd_congestion_fee`

These are not our labels. They are the difference between the TLC's own
published parquet schemas for 2023-01 and 2025-01, extracted by
`oracles/scan_tlc.py`. Anyone can rerun that script and get the same two
events without running this project at all.

**This is a benchmark, not a holdout.** It was run during development and
the results changed the code -- this scan returning nothing is what
surfaced the `editableProperties` bug. See
[`docs/VALIDATION-INTEGRITY.md`](../docs/VALIDATION-INTEGRITY.md) for the
timeline and the frozen-holdout claim that was withdrawn.

**Denominator:** 20 fields in the dataset, of which 18 must produce no finding.

| Baseline | Recall | False positives | Caught | Missed |
|---|---|---|---|---|
| B0 no context | 0/2 | 0 | — | `airport_fee`, `cbd_congestion_fee` |
| B1 coverage only | 1/2 | 0 | `cbd_congestion_fee` | `airport_fee` |
| B2 case-insensitive | 0/2 | 0 | — | `airport_fee`, `cbd_congestion_fee` |
| StillTrue | 2/2 | 0 | `airport_fee`, `cbd_congestion_fee` | — |

## What each baseline shows

**B0 (no context)** has only the prose. There is nothing to compare it
against, so it cannot report drift at all. This is where every agent
starts before a context platform is wired up.

**B1 (coverage only)** is what DataHub's own documentation-coverage view
already gives you: which fields lack a description. It finds the
undocumented column and, by construction, can never find a description
that is present but wrong -- it never reads the description.

**B2 (case-insensitive)** compares prose against schema the way most
people would write it first: lowercase both sides. Normalising the case
erases exactly the difference that constitutes the drift. This is not a
strawman -- it is the bug this project shipped in its own first version,
caught by the TLC regression test.

## Reproducing

```bash
datahub docker quickstart
python3 bench/oracles/build_tlc_benchmark.py   # loads the benchmark from public data
python3 bench/run_bench.py                   # regenerates this file
```
