# Demo video — final script

**2:50 total. 396 words of narration — 140 wpm overall, no shot above 154.**
Supersedes `VIDEO-SCRIPT-a.md` and `-b.md`; the verdict that chose between them
is `REVIEW-video-codex.md`, and the review of this file is
`REVIEW-video-final-codex.md`.

The first draft ran 440 words with two unreadable shots (275 and 225 wpm) and
ten narration claims that could be disproved from this repo. Both are fixed
below; the second review is what found them.

Structure follows A: the problem and the result land in the first 21 seconds,
because a judge may stop there and the brief says judges need not run anything.
Two changes from A, both from the codex review: the baseline comparison is
inserted at 0:21, and the 29-abstention segment is cut — good engineering, but it
asks the viewer to hold a denominator and three verdict types before it pays off.

Every shot names the file or command that produces it. Four shots need material
that has to be produced first — see **Footage that must be recorded** below. The
first draft claimed only two did, and was wrong about which.

---

| # | Time | On screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:12 | `docs/evidence/02-before-columns.png`, slow push from the schema row to the Summary panel. Highlight `Airport_fee` left, `airport_fee` right. | "One DataHub page. The schema says `Airport_fee`. The documentation, same frame, says `airport_fee`. The taxi commission changed that letter in 2023. The docs never followed." (25w) |
| 2 | 0:12–0:21 | `docs/evidence/04-after-columns.png`, same crop. | "Nobody opened the editor. An agent read the catalog, found the contradiction, and wrote only against a hash of the reviewed text." (22w) |
| 3 | 0:21–0:29 | `bench/REPORT.md` rendered, rows for `B1 coverage only` and `StillTrue` only. Caption: **coverage-only baseline**. | "A coverage check finds the undocumented column and misses the rename. It sees what's missing, not what's wrong." (18w) |
| 4 | 0:29–0:52 | ⚑ live `stilltrue scan --urn …`, then `stilltrue findings`. Frame the tally line and the three findings. | "The detector never guesses whether a word looks like a column. For a broken reference it asks DataHub's change log what left this dataset — no entry, no claim. The current schema only supplies the successor's name. Three findings here: the broken reference, an undocumented column, and one more I'll come back to." (54w) |
| 5 | 0:52–1:12 | ⚑ same run continuing: `NOT_APPROVED`, then `STALE`, then `VERIFIED`. | "A write with no confirmation is refused. Confirming one text and submitting another is refused too — the token is a hash of the exact content, so editing it afterwards voids the approval. Only then does it write, and it re-reads the value before believing it landed." (49w) |
| 6 | 1:12–1:24 | `curl` on the timeline endpoint, `docs/L3-EVIDENCE.md:162`. Frame the MODIFY line. | "The correction is now in DataHub's own change log — the same service the detector reads. You can check the write without trusting anything this tool wrote." (27w) |
| 7 | 1:24–1:56 | Split: left `curl …?aspect=editableSchemaMetadata` returning the note; right `05-orphan-present.png`. Then `bash scripts/prove_invisible.sh` output. Cut to the 110-pixel line. | "The third finding is one no DataHub page will show you. Document a column while `airport_fee` exists; the pipeline replaces the schema, and the note stays, keyed to a column that is gone. The aspect API returns it. The page renders nothing — descriptions merge onto current fields, and there is no row left to merge onto. So fixing it changes nothing on screen: a hundred and ten pixels out of one point three million, and every one of them is a clock." (82w) |
| 8 | 1:56–2:18 | `bench/REPLAY-REPORT.md` result table, then `bench/tlc-replay-results.jsonl` scrolling. | "Forty-one months of real published taxi schemas, ingested in order. The same description is re-ingested every month and never corrected, so the right answer is to report the break in the month it happens and every month after. Forty-one consecutive decisions, all correct, no false alarms — one quiet month, one onset, thirty-nine holds." (55w) |
| 9 | 2:18–2:32 | Terminal: `--mutate-skip-rewrite` run showing 0/2 beside the normal 2/2. `bench/HOLDOUT-orphan-iterable-datahub.md`. | "The orphan benchmark ships with a switch that breaks it on purpose. Remove the schema rewrite and it scores zero. A benchmark that cannot fail is not evidence." (27w) |
| 10 | 2:32–2:44 | `docs/evidence/prs/pr-{18622,18628,18630,49}.png`, tiled. `pr-18628.png` shows the Open pill, 38 checks and the bug write-up in one frame. | "Four patches went upstream. One is the Agent Context Kit fetching field descriptions and deleting them before the merge its docstring promises — found by needing it to work." (29w) |
| 11 | 2:44–2:50 | `docs/evidence/07-title-card.png`. | "StillTrue. Every number here regenerates from the repo." (8w) |

---

## Footage that must be recorded

⚑ **Shot 4–5** — one continuous `make demo` run. Do not splice: the proposal hash
in shot 5 must be the one from shot 4's scan. Reloading the benchmark between
takes changes every hash and the timeline version, and a judge comparing the two
frames would see one write with two different hashes.

⚑ **Shot 7** — `prove_invisible.sh` is a live run, not a comparison of two
committed images: it rebuilds the benchmark, writes to DataHub, captures, removes
the orphan and captures again. It now writes to `runs/invisible/` by default, so
filming it cannot overwrite the committed pair the documents cite; regenerating
those is `--publish`, deliberately.

⚑ **Shot 9** — both directions, against a running DataHub and a clone:

```bash
git clone --quiet https://github.com/fivetran/dbt_iterable /tmp/dbt_iterable
python3 bench/run_orphan_bench_datahub.py /tmp/dbt_iterable bench/oracles/orphaned-dbt-iterable.jsonl
python3 bench/run_orphan_bench_datahub.py /tmp/dbt_iterable bench/oracles/orphaned-dbt-iterable.jsonl --mutate-skip-rewrite
```

Each pass replays ~50 cases through DataHub, so allow several minutes per run —
this is not a shot you can improvise on the day. The committed table in
`bench/HOLDOUT-orphan-iterable-datahub.md` is the fallback and loses only the
live-terminal feel.

**Shot 10** — `python3 scripts/capture_prs.py` writes the four PR pages to
`docs/evidence/prs/`. Committed; no browser needed on the day.

**Shot 11** — `python3 scripts/capture_card.py` renders `scripts/title_card.html`
to `docs/evidence/07-title-card.png` at 1920×1080. Edit the HTML, not the PNG.

Everything else is a committed file.

## Claims kept out, and why each one had to be

Ten of these were in the first draft's narration. They are listed with the file
that disproves them, because the same sentences will look reasonable again in a
month.

**Now fixed in the text above:**

| Was | Why it failed | Now |
|---|---|---|
| "a human confirmed it" (S2) | `scripts/demo.sh:26-32` extracts the token from the dry run and hands it to the commit — no human input anywhere in the shot. The token carries no identity (`proposal.py:99-114`) | "wrote only against a hash of the reviewed text" |
| "a coverage check scores this table perfectly" (S3) | the row on screen reads **1/2** (`bench/REPORT.md:22`) | "finds the undocumented column and misses the rename" |
| "the description is written once" (S8) | `replay_tlc.py:83-96` upserts it every month; only the *column* docs are written once | "the same description is re-ingested every month and never corrected" |
| "everything shown is in the repo" (S11) | shots 4–5, 7 and 9 are live terminals, shot 10 is a GitHub page, and the title card does not exist | "every number here regenerates from the repo" |
| "Nothing failed / every description kept running" (S1) | the oracle proves the schema changed; it checks no consumer at all, and a description does not run | cut |
| "the one nobody is asking" (S3) | Cloud Context Hub evaluates context quality (`NATIVE-COMPARISON.md:131-146`) | cut; the narrow claim lives in the README |
| "no entry, no claim" unqualified (S4) | true of `D1_SCHEMA_BREAK` only — the undocumented and orphaned detectors never read the change log | "for a broken reference…" |
| "one DataHub cannot show you" (S7) | the next sentence says the aspect API returns it | "one no DataHub page will show you" |
| "someone documented `airport_fee`" (S7) | that note is a fixture written by `build_tlc_benchmark.py:76-96`, not a user's history | "document a column while `airport_fee` exists" — the mechanism, not a person |
| "the same log the detector reads" (S6) | same timeline service, different category: the detector reads TECHNICAL_SCHEMA, the correction lands in DOCUMENTATION | "the same service the detector reads" |

**Still to keep out, in delivery:**

- **The PRs are open, not merged.** Shot 10 says "went upstream".
- **Nine timeline categories is wrong** — the skills repo's CLI reference lists
  five (`tag`, `glossary_term`, `technical_schema`, `documentation`, `owner`).
- **41/41 is not forty-one different events.** One onset, thirty-nine holds.
- **Do not read the change-log quote aloud as fact.** DataHub pairs this rename
  with `cbd_congestion_fee`, which is wrong — its differ matches by position. If
  the quote is legible on screen, the narration must not assert the pairing.

## If it runs long

Cut shot 3 (−8s), then shot 9's second half (−6s). **Those are the only two safe
cuts.**

The first draft listed shot 6 third. That was a mistake carried over from a
misread of the earlier verdict, which said the opposite: two before/after stills
do not establish that *this tool* caused the change, and the DataHub timeline
entry is the only shot that does. Cutting shot 6 removes the causal link and
leaves the video asserting authorship it never demonstrates.

If more than 14 seconds has to go, take it out of shot 7's pixel-diff tail or
shot 8's breakdown — not from 1, 2, 5, 6 or the first half of 7, which are the
problem, the result, the refusal, the proof of authorship, and the finding
nothing else in the field has.
