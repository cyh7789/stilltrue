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

## The one thing that would restore it

A source acquired *after* a recorded freeze, scored once, with the code untouched
afterwards regardless of outcome. That requires `freeze.json` pinning the hashes
of the detectors, the category definitions and the scoring scripts, committed
before the source is fetched. It has not been done yet; if it is, it will appear
here with the freeze commit and the single scoring run.

Until then, this project reports benchmarks.
