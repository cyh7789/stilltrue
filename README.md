# StillTrue

**Your data documentation is already lying to you. This finds out where.**

---

In February 2023, the NYC Taxi & Limousine Commission renamed a column in its
public trip records from `airport_fee` to `Airport_fee`. One letter. No
announcement, no deprecation notice, no error anywhere. Every query, every
dbt model and every piece of documentation that spelled it the old way kept
running and quietly stopped meaning what it said.

In January 2025 they added `cbd_congestion_fee`. The published data dictionary
still doesn't mention it.

This is not a taxi problem. DataHub's own writing names it precisely:

> **Context problems don't announce themselves as context problems.** They show
> up as agents that give stale answers, documentation that drifts from reality,
> and AI tools that work in demos but fail in production.

Everyone is busy pointing agents *at* the catalog. Nobody is checking whether
what's in the catalog is still true. DataHub's own framing of an audit is
"[how complete is our metadata](docs/NATIVE-COMPARISON.md)" — and its seven
assertion types are all about the data, none about the documentation. Complete,
not correct.

StillTrue is an agent whose job is the catalog itself: it reads what humans
wrote, compares it against what the schema and lineage actually do, and reports
where the two have come apart — with citations, and never writing anything back
without a human confirming that exact text.

## What it does

```bash
stilltrue scan --limit 25       # read DataHub, run deterministic detectors
stilltrue findings              # what drifted, and what the evidence is
stilltrue apply <id> --to "…"   # draft a fix, gate it, show the diff and its hash
stilltrue apply <id> --to "…" \
    --approve <hash> --commit  # confirm that exact text, then write it back
stilltrue verify                # prove the audit trail wasn't tampered with
```

How a claim gets made: **the detector never decides whether a token looks like a
field name.** It asks DataHub what changed. One thing counts as evidence that a
token *was* a field here — DataHub's change log recording it leave. The current
schema then names the successor when there is one, which is how a rename reads
differently from a deletion. A lookalike column with no entry in the change log
is not evidence of anything, and abstains.

That is why no English word list decides a drift assertion. Descriptions
enumerate values, name neighbouring tables, cite entity types and carry
unexpanded Jinja; every corpus writes a form the last one did not. Subtracting
those shapes one by one is an open-world problem. Requiring evidence closes it —
an enumerated value never appears in a schema change log, so no rule had to be
written to exclude it.

One word list survives, and it is worth being precise about: thirteen nouns
(`schema`, `table`, `model`, …) that suppress an *abstention* when the author
already said what kind of thing they were naming — "the `orders` table". It can
only turn a shrug into silence; `qualified_as_non_field` is checked before any
evidence is consulted and can never overturn a verdict the change log supports.
D3's lineage check does use English trigger phrases, and D3 is not one of the two
detectors any number here rests on.

Five checks across three families, only one of which is allowed near a language
model:

| | What the humans wrote | What reality shows | How it's decided |
|---|---|---|---|
| **D1** schema break | a description references a field | DataHub's change log | deterministic |
| **D1** orphaned doc | a field is documented | the field is not in the schema | deterministic |
| **D1** undocumented | table is documented | some fields aren't | deterministic |
| **D3** lineage drift | "derived from X" | actual upstreams | deterministic |
| **D5** semantic conflict | one glossary term, two definitions | how each side filters in real queries | prefilter → LLM → citation gate |

D1 and D3 run in `stilltrue scan`. **D5 is implemented but not yet wired into the
CLI**: its judge is injected rather than built in, so the module itself makes no
network calls and can be tested against a fake. Connecting a real LLM judge is
the remaining step — see `src/stilltrue/semantic.py`.

The gaps in the numbering are deliberate and worth stating plainly. The design
enumerated five drift families; **D2 (freshness drift) and D4 (ownership drift)
are not implemented.** There is no code for them, hidden behind an abstraction or
otherwise. What ships is D1, D3 and an unwired D5.

D2 and D5 are blocked by the catalog rather than by effort, and the measurements
are in [`docs/D2-FEASIBILITY.md`](docs/D2-FEASIBILITY.md): across 76 datasets in
DataHub's own showcase catalog, **zero** descriptions claim a refresh cadence and
**zero** freshness assertions exist, while `get_dataset_queries` returns
`total: 0`. A description can drift from schema and lineage because DataHub
stores schema and lineage. Open-source DataHub does not store refresh cadence or
query history, so building those detectors here would mean authoring both the
claim and the evidence — and grading ourselves on answers we wrote.

## Quickstart

```bash
pip install -e .
make datahub-up        # datahub docker quickstart
make demo              # the whole loop on a real drift event, refusals included
```

Each number below is regenerated by its own script, named in the report it
produces — `bench/oracles/replay_tlc.py` for the 41 months,
`bench/run_orphan_bench_datahub.py` for the orphaned-doc corpora. (`make
bench-replay` runs the older baseline set, not those.) To point the scanner at
your own catalog instead:

```bash
datahub datapack load showcase-ecommerce
stilltrue scan --limit 25
stilltrue findings
```

Two worked examples, both unedited command output:
[**tlc-rename**](examples/tlc-rename/) — detect, refuse two writes, approve, write
back, verify. [**abstention**](examples/abstention/) — 25 real tables, 14 honest
"I don't know"s, zero false drift.

If you would rather look than run:
[**docs/L3-EVIDENCE.md**](docs/L3-EVIDENCE.md) walks one URN from the DataHub
page that contradicts itself, through the two refused writes, to the same page
after the correction — with the receipt, the audit chain, and DataHub's own
change-log entry for the write.

## Design: the model proposes, the code decides

```
read-only adapter ──→ deterministic detectors ──→ proposal ──→ Policy Gate
    (5 read tools)      D1 / D3 (no LLM)                            │
                        D5 (LLM, fenced)                  human confirmation
                                                                    │
                       write executor ←───────────────────────────┘
                  (re-read → write → read-back)
                              │
                    hash-chained audit ledger
```

Three properties this buys, each of which is a real failure being prevented:

**The model cannot reach a write.** The adapter wraps five read tools from the
Agent Context Kit — `get_entities`, `list_schema_fields`, `get_lineage`,
`get_dataset_queries`, `grep_documents`. The Kit also offers `search` and
`search_documents`; neither is wrapped, because scope arrives as a URN list or a
`--limit`, so nothing in the detector path needs to search. The mutation tools
aren't imported in that module at all — writes live in a separate module that
nothing in the detector path can call.

That separation is structural, not privileged: `cli.py` builds the adapter and
the executor against the same DataHub connection, so a distinct write credential
is a deployment step this repo does not take. The executor accepts a `token`
argument for it; nothing here passes a different one.

**Every claim carries a citation.** Each observation becomes an evidence record
addressed by its content hash. The Policy Gate rejects any proposal citing an
evidence id that doesn't exist, which is exactly what a hallucinated citation
looks like.

**Confirmation binds to the content, not the session.** `proposal_hash` covers
the URN, the aspect, the before and after text, the verdict and the cited
evidence. Confirming one wording and then writing another produces a different
hash, so the token stops applying and the write fails closed — the refusal is in
[`examples/tlc-rename`](examples/tlc-rename/#2-two-writes-that-get-refused).
Passing the Policy Gate means the proposal is well formed, never that anyone
wants it.

*This is a content lock, not an authorisation boundary.* It proves the write
matches a text that was displayed and confirmed; it does not prove a separate
reviewer did the confirming, and anyone who can run `apply` can read the token
off a dry run. See [support boundary](#support-boundary).

**Abstaining is a valid answer.** Verdicts are `DRIFT`, `CURRENT` or
`INSUFFICIENT_EVIDENCE`, and all three are recorded. When a description mentions
an identifier that is not a field and has no near-match, the honest output is "I
don't know", not a guess. Recording the references that *did* resolve is what
lets a scan say how much it checked: `2 drift, 5 verified current, 0 abstained`
is a different claim from `2 findings`.

That decision is what makes the numbers hold up. Real descriptions are prose:
they cite other tables, DataHub entity types, placeholders like `table_name`.
Reporting every unresolved token as drift produced 6 false drift verdicts across
25 tables from the `showcase-ecommerce` datapack. Requiring a rename candidate
before calling anything drift takes that to **zero**, while both NYC TLC
ground-truth events are still caught:

```
$ stilltrue scan --urn "urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)"
  2 drift, 5 verified current, 0 abstained (7 checks)

  D1_SCHEMA_BREAK  airport_fee -> likely renamed to `Airport_fee`
  D1_UNDOCUMENTED  cbd_congestion_fee exists in the schema but has no description
```

The cost is stated plainly: a column that was genuinely deleted, with no
similarly named replacement, now reads as abstention rather than drift.

## Evidence

Every number below is produced by ingesting into a real DataHub and reading back
through the adapter. None of them is scored by handing the detector its own
answer — which an earlier version of the orphaned-doc harness did, and which is
described in full [below](#the-benchmark-that-could-not-fail).

| | corpus | result |
|---|---|---|
| **schema break** — the prose names a field that is gone | NYC TLC, 41 months of published schema history | **41/41** months exactly right, 0 false alarms |
| **orphaned doc** — documentation attached to a field that is gone | `fivetran/dbt_hubspot` | **4/4**, 0 false alarms on 432 |
| **orphaned doc** | `fivetran/dbt_iterable` | **2/2**, 0 false alarms on 199 |

Every assertion either matches a label or is accounted for: **0 the labels cannot
explain**, across both corpora. Four on HubSpot match no label and are right
anyway — the column left the model's SQL in that window and git says so; the
label file has no row for them because its miner keeps only the first entry per
`(model, column)`. They are counted separately rather than folded into either
column.

### The 41 months

A description written once against the January 2023 schema and never revised,
then every month's real TLC parquet schema ingested in order — the ordinary
situation, where the pipeline keeps running and the docs do not keep up. Two
things happened and neither was announced: `airport_fee` became `Airport_fee` in
2023-02, `cbd_congestion_fee` appeared in 2025-01.

Scored on *state*, not events. The rename was never corrected, so the right
answer is to report it in 2023-02 **and every month after**; reporting it once
and going quiet would be a failure. That is 41 consecutive decisions, not two.
Labels come from diffing the TLC's own published files
([`bench/REPLAY-REPORT.md`](bench/REPLAY-REPORT.md)).

### The benchmark that could not fail

The orphaned-doc numbers used to come from a harness that could not have
produced any others, and the way that happened is worth more than the numbers.

The oracle called a case positive when a column left the model's SQL and its yml
description outlived it. The scorer then handed the detector that column, that
description and the after-schema. And the detector asserts when a documented
field is absent from the schema. Three statements of one sentence — so labelling
a row already settled the verdict. 2/2 and 0/199 were never at risk. Worse, that
harness never imported `adapter.py`, so the part that actually fails in
production — reading two different DataHub aspects and coming back with the right
two sets, which is exactly where the Agent Context Kit drops field descriptions
([datahub#18628](https://github.com/datahub-project/datahub/pull/18628)) — was
never touched.

`bench/run_orphan_bench_datahub.py` replays each model's history instead:
ingest the columns as of the earlier commit, write the yml descriptions the way a
person writes them (into `editableSchemaMetadata`, via the same Kit call the UI
uses), ingest the later schema on top, then run the detector on whatever
`ReadOnlyDataHubAdapter` reads back. The detector's inputs are now DataHub's
answers, not the label's.

It reports the same figures, which is exactly why it ships with the mutation that
proves the difference:

| | normal | `--mutate-skip-rewrite` |
|---|---|---|
| `run_orphan_bench_datahub.py` | 2/2 | **0/2** |
| the old `run_orphan_bench.py` | 2/2 | 2/2 |

Dropping the second ingestion means nothing gets orphaned, so a benchmark with
any power has to go to zero. The new one does. The old one does not notice,
because it never asks DataHub anything.

One thing DataHub settled along the way: `updateDescription` refuses a column the
schema does not have (`BAD_REQUEST`, *"Field X does not exist in the datasets
schema"*). An orphaned description cannot be written directly — it can only be
left behind, which is why this replay has to run in the order the events did.

### Selection integrity, and one inconsistency

`dbt_iterable` was fetched **after** the graded files were hashed, by a rule
committed before any candidate was inspected, and scored once — sixteen
repositories rejected on the way, each with a mechanical reason.
`python3 bench/freeze.py --check` re-derives the hashes.

Recorded rather than smoothed over: the rule's `mined_positives >= 30` threshold
was evaluated with the *previous* oracle, which counted documentation edits
rather than orphaned documentation. The denominator that actually turned up was
2, not 30 ([the report](bench/HOLDOUT-orphan-iterable.md)). Two positives
establish that the mechanism survives the round trip; they do not establish a
rate.

**What the freeze covers, and what round 5 changed.** Nine files are hashed —
the detector, the adapter, the evidence store, both scorers, both miners, and
the source-selection rule. Three of those were added in round 5: `select_holdout.py`
(it decides which source gets graded), `mine_drift_labels.py` (both round-4
frozen files imported it while it sat outside the hashes), and the new scorer.
The extension is checkable as an extension rather than a reset: of the six files
frozen in round 4, five are byte-identical, and the sixth is `detectors.py`,
whose change is the rename rule described above. `git show HEAD~1:bench/freeze.json`
against the current one shows this.

A freeze proves the graded code did not move once the numbers were seen. It does
not prove a run happened only once, and self-recorded hashes never could.

### What was withdrawn, and why

Three dbt packages were scored under a previous design and those numbers are
gone. The labels measured "descriptions that were later edited", which is
doc-editing behaviour rather than what this system decides: in **9 of
`dbt_shopify`'s 10** identifier-change positives the referenced token was never
a column of that model at either end of the window — enumerated values like
`fixed_amount`, and upstream model names. The old detector scored them by firing
on exactly those tokens, and a label-based oracle credits a correct verdict
reached for the wrong reason. Fixing the oracle is what exposed the orphaned-doc
gap. Full history, including a frozen-holdout claim drafted and withdrawn:
[`docs/VALIDATION-INTEGRITY.md`](docs/VALIDATION-INTEGRITY.md).

### Does this actually need a context platform?

Same benchmark, same inputs, four approaches ([`bench/REPORT.md`](bench/REPORT.md),
regenerate with `python3 bench/run_bench.py`):

| Baseline | Recall | False positives | Missed |
|---|---|---|---|
| B0 — no context, prose only | 0/2 | 0 | both |
| B1 — coverage only (what DataHub already shows) | 1/2 | 0 | the rename |
| B2 — prose vs schema, case-insensitive | 0/2 | 0 | both |
| **StillTrue** | **2/2** | **0** | — |

**B1** is the honest one to beat: it reimplements the strongest thing DataHub
gives you for free — which fields lack a description — and it finds the
undocumented column. What it structurally cannot find is a description that is
present and wrong, because it never reads the description. (It *approximates*
DataHub's completeness surface rather than reimplementing a specific feature
line by line; the distinction is spelled out in
[`docs/NATIVE-COMPARISON.md`](docs/NATIVE-COMPARISON.md).)

**B2** is not a strawman. Lowercasing both sides is what most people write
first, and it erases exactly the difference that constitutes a case-only rename.
It is also the bug this project shipped in its own first version — the TLC
regression test is what caught it, and it is still in `tests/test_detectors.py`
with the mistake documented in the docstring.

## What this does not do

- **It does not judge whether your documentation is well written.** Only whether
  it still matches reality. A beautifully worded description of a table that no
  longer exists is drift; a terse one that is accurate is not.
- **It cannot see context that isn't in DataHub.** Detection quality equals graph
  completeness. Nothing in the catalog means nothing to check.
- **It does not rebuild what DataHub already ships.** DataHub's Data Quality
  Agent creates assertions whose subject is the **data** — row counts,
  distributions, freshness of the underlying table. StillTrue's subject is the
  documentation: whether the prose a human wrote still matches the schema and
  lineage DataHub already stores. DataHub's assertion type system has no type
  that can express the second question — `DATASET`, `FRESHNESS`, `VOLUME`,
  `SQL`, `FIELD`, `DATA_SCHEMA`, `CUSTOM`, all about data. You cannot write
  "assert this description still names columns that exist", not because it would
  fail but because there is nowhere to put it.

  The closest of DataHub's four proposed agents is the **Data Steward Agent**,
  which "applies glossary terms and descriptions". StillTrue is that agent run
  backwards: it reads what was applied and asks whether it is still true. Same
  object, opposite direction. DataHub Cloud's Context Hub does evaluate context
  quality — it is Cloud-only and in private beta, so the open-source user has
  nothing. Full comparison, in DataHub's own words:
  [`docs/NATIVE-COMPARISON.md`](docs/NATIVE-COMPARISON.md).
- **It never writes without approval.** There is no autonomous mode, no
  `--yes-to-all`. A write always requires a token for the exact text being
  written; see the support boundary below for what that token does not prove.
- **It does not detect data quality problems.** Bad values, nulls, freshness of
  the *data* — those belong to DataHub's quality features. This watches the
  *description* of the data.

## Support boundary

Three things this project is careful **not** to claim, stated here rather than
discovered later.

**The confirmation token is a content lock, not an authorisation boundary.**
`--approve <hash>` proves the write matches a text that was displayed and
confirmed. It carries no identity, no signature and no privilege separation:
whoever can run `apply` can obtain the token from a dry run. It closes "approve
one thing, write another"; it does not close "the writer approved their own
change". Enforcing *who* may approve needs a receipt the executor can verify but
not issue — that is not built.

**The benchmarks measure fit, not transfer.** Three sources are scored — NYC TLC,
`dbt_hubspot`, `dbt_iterable` — and none is a blind holdout for the code as it
now stands. TLC and HubSpot shaped the detector directly. Iterable was a blind
holdout for the *old* orphaned-doc harness, but the harness that scores it now
was written after its result was known, so its blindness is spent. What carries
those numbers is the mutation in
[`bench/HOLDOUT-orphan-iterable-datahub.md`](bench/HOLDOUT-orphan-iterable-datahub.md) —
that the benchmark scores 0/2 when the schema rewrite is removed — not the order
things were run in. The labels are still ones we did not write.
Timeline with commit hashes: [`docs/VALIDATION-INTEGRITY.md`](docs/VALIDATION-INTEGRITY.md).

**Five drift families were designed; two run.** D1 (schema break, undocumented
columns) and D3 (lineage drift) ship. D2 (freshness) and D4 (ownership) have no
code at all. D5 (semantic conflict) is implemented but unwired. For D2 and D5 the
blocker is measured, not estimated — see
[`docs/D2-FEASIBILITY.md`](docs/D2-FEASIBILITY.md).

## Known limitations

- D5 needs real query history to compare filter logic. On a catalog without
  captured queries it has nothing to work with and abstains.
- The `D1_UNDOCUMENTED` detector only fires when the table itself has a
  description. A table with no documentation anywhere is out of scope by design
  — that is "never started", not "fallen out of sync".
- Lineage claims are matched by name against upstream URNs. A claimed source
  that exists under a very different name will read as drift.
- The audit ledger's final record has nothing after it to anchor against. An
  attacker who edits the last entry *and* recomputes its hash cannot be caught by
  `verify` alone; that needs an external anchor, such as publishing the root hash.

## License

Apache 2.0
