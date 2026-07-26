# Demo video — final script

**2:50 total. 428 words of narration at ~150 wpm.** Supersedes `VIDEO-SCRIPT-a.md`
and `-b.md`; the verdict that chose between them is `REVIEW-video-codex.md`.

Structure follows A: the problem and the result land in the first 21 seconds,
because a judge may stop there and the brief says judges need not run anything.
Two changes from A, both from the codex review: the baseline comparison is
inserted at 0:21, and the 29-abstention segment is cut — good engineering, but it
asks the viewer to hold a denominator and three verdict types before it pays off.

Every shot names the file or command that produces it. Nothing here needs footage
that does not exist **except** the two live terminal runs marked ⚑, which have to
be recorded against a running DataHub.

---

| # | Time | On screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:12 | `docs/evidence/02-before-columns.png`, slow push from the schema row to the Summary panel. Highlight `Airport_fee` left, `airport_fee` right. | "This is one DataHub page. The schema says `Airport_fee`. The documentation, in the same frame, says `airport_fee`. In February 2023 the NYC taxi commission changed that one letter. Nothing failed. Every description that spelled it the old way kept running and quietly stopped being true." (55w) |
| 2 | 0:12–0:21 | `docs/evidence/04-after-columns.png`, same crop. | "Nobody opened the editor. An agent read the catalog, found the contradiction, proposed the correction, and a human confirmed it." (21w) |
| 3 | 0:21–0:29 | `bench/REPORT.md` rendered, rows for `B1 coverage only` and `StillTrue` only. Caption: **coverage-only baseline**. | "A coverage check scores this table perfectly — the description exists. Asking whether it is still *correct* is a different question, and it is the one nobody is asking." (30w) |
| 4 | 0:29–0:52 | ⚑ live `stilltrue scan --urn …`, then `stilltrue findings`. Frame the tally line and the three findings. | "The detector never guesses whether a word looks like a column. It asks DataHub's own change log what left this dataset. No entry, no claim — the current schema only supplies the successor's name. Three findings here: the broken reference, an undocumented column, and one more I'll come back to." (52w) |
| 5 | 0:52–1:12 | ⚑ same run continuing: `NOT_APPROVED`, then `STALE`, then `VERIFIED`. | "A write with no confirmation is refused. Confirming one text and submitting another is refused too — the token is a hash of the exact content, so editing it afterwards voids the approval. Only then does it write, and it re-reads the value before believing it landed." (49w) |
| 6 | 1:12–1:24 | `curl` on the timeline endpoint, `docs/L3-EVIDENCE.md:162`. Frame the MODIFY line. | "The correction is now in DataHub's own change log — the same log the detector reads. You can check the write without trusting anything this tool wrote." (27w) |
| 7 | 1:24–1:56 | Split: left `curl …?aspect=editableSchemaMetadata` returning the note; right `05-orphan-present.png`. Then `bash scripts/prove_invisible.sh` output. Cut to the 110-pixel line. | "The third finding is one DataHub cannot show you. Someone documented `airport_fee` while it existed. The pipeline replaced the schema; the note stayed, keyed to a column that is gone. The aspect API returns it. The page renders nothing — it merges descriptions onto current fields, and there is no row left to merge onto. So fixing it changes nothing on screen: a hundred and ten pixels out of one point three million, and all of them are a clock." (81w) |
| 8 | 1:56–2:18 | `bench/REPLAY-REPORT.md` result table, then `bench/tlc-replay-results.jsonl` scrolling. | "Forty-one months of real published taxi schemas, ingested in order. The description is written once and never revised, so the right answer is to report the break in the month it happens and every month after. Forty-one consecutive decisions, all correct, no false alarms — one quiet month, one onset, thirty-nine holds." (54w) |
| 9 | 2:18–2:32 | Terminal: `--mutate-skip-rewrite` run showing 0/2 beside the normal 2/2. `bench/HOLDOUT-orphan-iterable-datahub.md`. | "The orphan benchmark ships with a switch that breaks it on purpose. Remove the schema rewrite and it scores zero. A benchmark that cannot fail is not evidence." (27w) |
| 10 | 2:32–2:44 | Four GitHub PR pages, tiled. | "Four patches went upstream. One of them is the Agent Context Kit fetching field descriptions and deleting them before the merge its own docstring promises — found by needing it to work." (32w) |
| 11 | 2:44–2:50 | Title card: name, repo URL, Apache-2.0. | "StillTrue. Everything shown is in the repo, and every number regenerates." (12w) |

---

## Footage that must be recorded

⚑ **Shot 4–5** — one continuous `make demo` run. Do not splice: the proposal hash
shown in shot 5 must be the one from shot 4's scan. Reloading the benchmark
between takes changes every hash and the timeline version.

⚑ **Shot 9** — the mutation needs the full command, both ways, against a running
DataHub with a `dbt_iterable` clone:

```bash
python3 bench/run_orphan_bench_datahub.py <clone> bench/oracles/orphaned-dbt-iterable.jsonl
python3 bench/run_orphan_bench_datahub.py <clone> bench/oracles/orphaned-dbt-iterable.jsonl --mutate-skip-rewrite
```

Everything else is a committed file or `bash scripts/prove_invisible.sh`.

## Claims to keep off the narration

- **Do not say the PRs are merged.** They are open. Shot 10 says "went upstream".
- **Do not say nine timeline categories.** The skills repo's CLI reference lists
  five (`tag`, `glossary_term`, `technical_schema`, `documentation`, `owner`).
- **Do not say the orphan is "invisible everywhere".** The aspect API returns it —
  shot 7 shows that route on camera first. The claim is the standard pages and
  the Kit.
- **Do not call 41/41 forty-one different events.** It is one onset and thirty-nine
  holds; shot 8 says so.
- **Do not read the change-log quote aloud as fact.** DataHub pairs this rename
  with `cbd_congestion_fee`, which is wrong — its differ matches by position. If
  the quote is legible on screen, the narration must not assert the pairing.

## If it runs long

Cut in this order: shot 3 (−8s), shot 9's second half (−6s), shot 6 (−12s).
Never cut shots 1, 2, 5 or 7 — they are the problem, the result, the refusal, and
the finding nothing else in the field has.
