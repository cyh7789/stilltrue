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
what's in the catalog is still true. StillTrue is an agent whose
job is the catalog itself: it reads what humans wrote, compares it against what
the schema, lineage and query history actually do, and reports the places where
the two have come apart — with citations, and never writing anything back without
a human confirming that exact text.

## What it does

```bash
stilltrue scan --limit 25       # read DataHub, run deterministic detectors
stilltrue findings              # what drifted, and what the evidence is
stilltrue apply <id> --to "…"   # draft a fix, gate it, show the diff and its hash
stilltrue apply <id> --to "…" \
    --approve <hash> --commit  # confirm that exact text, then write it back
stilltrue verify                # prove the audit trail wasn't tampered with
```

Four checks across three families, only one of which is allowed near a language
model:

| | What the humans wrote | What reality shows | How it's decided |
|---|---|---|---|
| **D1** schema break | a description references a field | the field list | deterministic |
| **D1** undocumented | table is documented | some fields aren't | deterministic |
| **D3** lineage drift | "derived from X" | actual upstreams | deterministic |
| **D5** semantic conflict | one glossary term, two definitions | how each side filters in real queries | prefilter → LLM → citation gate |

D1 and D3 run in `stilltrue scan`. **D5 is implemented but not yet wired into the
CLI**: its judge is injected rather than built in, so the module itself makes no
network calls and can be tested against a fake. Connecting a real LLM judge is
the remaining step — see `src/stilltrue/semantic.py`.

The gaps in the numbering are deliberate and worth stating plainly. The design
enumerated five drift families; **D2 (freshness drift — a description claiming a
refresh cadence the data no longer keeps) and D4 (ownership drift) are not
implemented.** They are not hidden behind an abstraction waiting to be filled in;
there is no code for them. What ships is D1, D3 and an unwired D5.

## Quickstart

```bash
pip install -e .
make datahub-up        # datahub docker quickstart
make demo              # the whole loop on a real drift event, refusals included
```

`make bench-replay` regenerates every number in this README. To point it at your
own catalog instead:

```bash
datahub datapack load showcase-ecommerce
stilltrue scan --limit 25
stilltrue findings
```

Two worked examples, both unedited command output:
[**tlc-rename**](examples/tlc-rename/) — detect, refuse two writes, approve, write
back, verify. [**abstention**](examples/abstention/) — 25 real tables, 14 honest
"I don't know"s, zero false drift.

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
aren't imported in that module at all — writes live in a separate module behind a
separate credential.

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

Two third-party benchmarks, neither of them labelled by us:

| Benchmark | Tests | Result | Where the labels come from |
|---|---|---|---|
| NYC TLC trip records | docs vs data | **2/2**, 0 false positives | the diff between two published parquet schemas |
| [`fivetran/dbt_shopify`](https://github.com/fivetran/dbt_shopify) | docs vs code | **9/10** on identifier changes | the upstream project's own documentation-fix commits |

**These are benchmarks, not holdouts, and the difference matters.** Both were run
during development and both changed the code: the TLC scan returning nothing is
what surfaced the `editableProperties` bug, and a branch condition in
`detectors.py` was set from the dbt_shopify score. A benchmark that shaped the
rules measures fit, not transfer. The full timeline with commit hashes — including
the frozen-holdout claim we withdrew — is in
[`docs/VALIDATION-INTEGRITY.md`](docs/VALIDATION-INTEGRITY.md).

What survives the correction: the labels are still not ours, the denominators are
still public, and the bad numbers are still reported.

The dbt_shopify number is deliberately split by category
([`bench/SHOPIFY-REPORT.md`](bench/SHOPIFY-REPORT.md)). This detector compares
identifiers named in prose against the schema, so it addresses identifier
changes (9/10) and structurally cannot address deprecation notices — 17 of those
30 positives name no identifier at all. Folding both into one denominator would
understate the detector on the problem it solves and overstate it on the one it
does not.

The dbt_shopify miner walks 428 commits looking for pairs: a commit that changed
a model's SQL without touching the matching description, and the later commit
where a human finally fixed the wording. Everything between those two commits is
drift, labelled by the maintainers' own behaviour rather than by us. Only the
mechanically decidable categories (identifier changes, deprecation notices) count
toward the headline numbers; see [`bench/oracles/MINING-REPORT.md`](bench/oracles/MINING-REPORT.md)
for what was filtered out and why we stopped filtering.

The TLC benchmark needs no human labelling at all: run `bench/oracles/scan_tlc.py`
and the two events fall out of the published schemas.

### Does this actually need a context platform?

Same benchmark, same inputs, four approaches ([`bench/REPORT.md`](bench/REPORT.md),
regenerate with `python3 bench/run_bench.py`):

| Baseline | Recall | False positives | Missed |
|---|---|---|---|
| B0 — no context, prose only | 0/2 | 0 | both |
| B1 — coverage only (what DataHub already shows) | 1/2 | 0 | the rename |
| B2 — prose vs schema, case-insensitive | 0/2 | 0 | both |
| **StillTrue** | **2/2** | **0** | — |

**B1** is the honest one to beat: DataHub's documentation-coverage view already
tells you which fields lack a description, and it finds the undocumented column.
What it structurally cannot find is a description that is present and wrong,
because it never reads the description.

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
- **It does not rebuild what DataHub already ships.** DataHub Cloud's Context Hub
  has built-in evaluations for context quality; this is the open-source side of
  the problem, and it does not attempt to replace that.
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

**The benchmarks measure fit, not transfer.** Both third-party sources were used
during development and both changed the code. The numbers are a public,
regenerable regression baseline against real drift that we did not label — they
are not evidence of generalisation to sources the detector has never met.
Timeline with commit hashes: [`docs/VALIDATION-INTEGRITY.md`](docs/VALIDATION-INTEGRITY.md).

**Five drift families were designed; two run.** D1 (schema break, undocumented
columns) and D3 (lineage drift) ship. D2 (freshness) and D4 (ownership) have no
code at all. D5 (semantic conflict) is implemented but unwired — it needs real
query history, and a catalog with none gives it nothing to work with.

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
