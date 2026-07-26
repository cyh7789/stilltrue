# Validation integrity: what these numbers are, and what they are not

Every number this project reports comes from third-party data with labels we did
not write. That part holds. What does **not** hold is the stronger claim we
originally drafted — that the system was frozen before the data was acquired and
that the results never fed back into the code.

They did. This page documents exactly how, with commit hashes, so the claim can
be checked rather than trusted.

## The claim we withdrew

An earlier draft of `docs/BENCHMARK-nyc-tlc.md` contained this sentence, staged
to go into the submission verbatim:

> System code, prompts, policies, and category definitions were frozen before
> the NYC TLC source was acquired. […] Holdout outcomes were not used to modify
> the frozen system.

That sentence is false. It has been removed rather than reworded.

## What actually happened

| When | Commit | Event |
|---|---|---|
| 07-25 22:44 | `30cb453` | dbt_shopify label miner written — **before** any detector code existed |
| 07-25 23:12 | `29be464` | first detector (D1) written |
| 07-25 23:23 | `c54ad70` | policy gate, audit ledger |
| 07-25 23:29 | `3c58ce2` | write executor, D5 skeleton |
| 07-26 00:00 | `457b190` | TLC loader **and** `authored_description()` **and** the D1 tightening — see below |
| 07-26 00:19 | `0757ee3` | dbt_shopify scored; `detectors.py` changed in the same commit — see below |

### Two places where results changed the code

**1. `457b190` — the TLC scan returning nothing changed the adapter.**

Its own commit message says so:

> `authored_description()`: DataHub keeps two descriptions and the UI shows
> editableProperties, which is the text a reader believes. Reading only
> properties missed it entirely and **made the TLC holdout scan return nothing**.

The same commit tightened D1 to require a rename candidate, justified by
`showcase-ecommerce` false positives and validated against TLC: "*this takes it
to 0 while both TLC ground-truth events are still caught*". The TLC result was
used as an acceptance check on a code change.

**2. `0757ee3` — the dbt_shopify score set a branch condition.**

The comment sitting in `detectors.py` today, added by that commit, states the
dependency in the source itself:

```python
# A table description is prose and cites other tables, entity types and
# placeholders; a field description rarely does. Measured on
# fivetran/dbt_shopify: 9 of 10 identifier-change positives live here.
verdict, confidence = "DRIFT", "medium"
```

The rule that produces the 9/10 was chosen because of the 9/10.

## What this means for each number

(The table below covers the two development benchmarks. The frozen holdout added
afterwards is a separate thing and is described at the end of this page.)

| Source | Still true | No longer claimable |
|---|---|---|
| NYC TLC — 2/2, 0 FP | labels are the diff of two published TLC parquet schemas; anyone can regenerate them without running this project | that the system never saw the result before being finalised |
| dbt_shopify — 9/10 identifier changes | labels are the upstream maintainers' own documentation-fix commits, mined by a script written before the detector | that it is an untouched holdout scored once |
| `showcase-ecommerce` — 0 false positives on 25 tables | measured on the official datapack | never claimed as a holdout |

Both sources are **third-party benchmarks used during development**. That is a
weaker and more common form of evidence than a frozen holdout, and it is what we
have. Wherever this repo previously said "holdout", it now says "benchmark".

## Why the numbers are still worth reading

Three properties survive the correction, and they are the reasons these sources
were chosen in the first place:

1. **The labels are not ours.** A case-only rename in a public parquet schema and
   a maintainer's own "fix the docs" commit exist independently of this project.
   No one on this team decided what counts as a positive.
2. **The denominators are public.** 20 TLC fields of which 18 must stay silent;
   40 dbt_shopify positives against 2,496 negatives. Both are regenerable by
   scripts in `bench/oracles/`.
3. **The negative results are reported.** DEPRECATION scores 6/30 and is broken
   out rather than folded into a flattering aggregate.

What they cannot support is a generalisation claim. A benchmark that shaped the
rules measures fit, not transfer.

## What restored it, and what it cost

Two rounds, because the first one's answer was worth acting on.

**Round 1.** `bench/freeze.json` pinned the hashes of the detector, the
description resolver, the evidence record, the category definitions and the
scoring script at `f1661c0` — before any new source was fetched. The selection
rule was committed one commit earlier still, so the choice of source could not be
an outcome of preferring one that scores well. `fivetran/dbt_fivetran_log` was
scored once: **13/32 — 41%** against 90% on the development benchmark, with false
positives at 9.59%.

Publishing that unchanged was right and is not retracted. Refusing to *ever* fix
what it found was not. A peer review put the missing number next to it: on the
development benchmark the detector surfaced 9 true findings against 87 false ones
— **9.4% precision**. A platform team receiving 96 alerts of which 87 are wrong
turns the tool off. The freeze rule bars modifying the graded files *in response*
— that is, re-grading the same source after a fix — not improving the product.

**Round 2.** Both failure modes were fixed (`954415d`), `dbt_fivetran_log` was
retired to a development benchmark, everything the first selection walk had mined
was added to the exclusion list, and a second freeze drew `fivetran/dbt_hubspot`.
Scored once: **4/12 — 33%**, false positives 13.78%.

| | recall | false positives |
|---|---|---|
| dbt_shopify — development | 70% | 2.2% |
| dbt_fivetran_log — holdout v1 | **41%** | 9.6% |
| dbt_hubspot — holdout v2 | **33%** | 13.8% |

**Two independently drawn holdouts agree.** One can be unlucky; two is a property
of the tool. They are not a before/after of the fix — different sources and
different code — so nothing here claims the fix raised recall.

One correction the fix forced, worth stating because it cuts against us: the old
9/10 was partly accidental. `shopify__discounts.value_type` and
`.target_selection` scored as hits because the detector fired on `fixed_amount`,
`percentage`, `all` and `entitled` — the enumerated values in their descriptions,
not a broken reference. A label-based oracle credits a correct verdict reached for
the wrong reason. The honest development figure was always nearer 7/10.

`python3 bench/freeze.py --check` verifies the graded files have not moved since.
It exited 1 when the round-1 fix landed, which is how round 2 began.
Full results: [`bench/HOLDOUT-REPORT.md`](../bench/HOLDOUT-REPORT.md) and
[`HOLDOUT-REPORT-v1.md`](../bench/HOLDOUT-REPORT-v1.md).
