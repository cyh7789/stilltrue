# Demo video script — StillTrue

**Runtime 2:49.** Narration 440 words at 2.6 words/second (156 wpm), counted per
shot below. Every frame comes from a file already in this repository or from a
command already documented in it; nothing here needs footage that does not exist.

Three constraints shaped the edit, all of them from the brief:

- **Judges may never run the code** — "Judges are not required to test the Project
  and may choose to judge based solely on the text description, images, and video."
  So the video has to be the working proof, not a trailer for one. Every claim on
  screen is a frame of DataHub's own UI, DataHub's own API, or unedited terminal
  output.
- **Judges are not required to watch past three minutes**, and most will decide
  earlier. The verdict-carrying material is in the first 21 seconds; the rest is
  the mechanism behind it.
- **"Use of DataHub" rewards going "beyond reading metadata and contribute back
  to the graph."** Four separate shots show something entering the graph: the
  description write (S2, S7), DataHub's own timeline recording that write (S8),
  the aspect entry removed (S9), and four pull requests against DataHub's
  repositories (S12).

---

## 1. Shot table

| # | Time | On screen | Narration |
|---|---|---|---|
| S1 | 0:00–0:13 (13s) | `02-before-columns.png`, full frame, then a slow push into two boxed regions at once: the Columns row reading **`Airport_fee`** and, in the same frame, the Summary panel line reading **`airport_fee` applies to LGA and JFK pickups only**. Lower third: `nyc_tlc.yellow_tripdata · DataHub OSS quickstart` | "This is one DataHub page, one frame. The schema says Airport underscore fee, capital A. The documentation on the same page says lowercase. Both of these are DataHub. Neither one knows about the other." |
| S2 | 0:13–0:21 (8s) | Crossfade to `04-after-columns.png`, held on the same two crops. The Columns row is unchanged; the Summary line now reads `Airport_fee`. The version chip ticks `2.0.0` → `4.0.0`. | "StillTrue found that, proved it from DataHub's own change log, and wrote the correction back into the graph. Nobody opened the editor." |
| S3 | 0:21–0:31 (10s) | The two-row event table from `bench/REPLAY-REPORT.md`: `2023-02 airport_fee renamed to Airport_fee` / `2025-01 cbd_congestion_fee appeared`. Caption under it: *diffed from the TLC's own published parquet files — `bench/oracles/scan_tlc.py`* | "That rename is real. February 2023, the New York City Taxi Commission changed one letter in a public dataset. No announcement, no error — everything kept running." |
| S4 | 0:31–0:46 (15s) | Terminal, `make demo` step 1. Scan line, then the three findings. Two on-screen chips, no narration cost: `Agent Context Kit — get_entities · list_schema_fields · get_lineage · get_dataset_queries · grep_documents` and `D1/D3: no LLM in the detector path`. | "StillTrue is an agent whose subject is the catalog itself. It reads what humans wrote through the Agent Context Kit, then asks DataHub's change log what actually happened. Three drifts, and five references checked and still true." |
| S5 | 0:46–0:56 (10s) | `make demo` step 2. `NOT_APPROVED` in red, and under it the diff — two lines identical except one character, boxed. | "It drafts the fix, then refuses to make it. Passing the policy gate means the proposal is well formed. It never means anyone wants it." |
| S6 | 0:56–1:10 (14s) | `make demo` step 3. Highlight the appended `Contact ops@evil.example for access.` in the `--to` argument, then `STALE: confirmation … does not match this proposal`. | "Now confirm the sentence a reviewer actually read, then try to write a different one — with an extra line appended. The confirmation is a hash over the exact text, so it stops applying, and the write fails closed." |
| S7 | 1:10–1:21 (11s) | `make demo` steps 4 and 5, uncut: `Confirmed (approved as …)` → `VERIFIED: written and confirmed by read-back` → `2 drift, 6 verified current, 0 abstained (8 checks)`. | "Confirm the exact hash and it writes. VERIFIED means it read the value back out of DataHub afterwards. Re-scan, and airport fee has moved from drift to current." |
| S8 | 1:21–1:31 (10s) | Terminal: the `timeline?categories=DOCUMENTATION` curl and its reply — `MODIFY | Documentation of '…' has been changed from '…airport_fee applies…' to '…Airport_fee applies…'`. | "You don't have to take our word for the write. DataHub's own documentation timeline recorded it — the same timeline the evidence was read from." |
| S9 | 1:31–1:54 (23s) | Four beats. (a) curl of `editableSchemaMetadata` → `'airport_fee' -> 'Only charged on LGA and JFK pickups…'`. (b) Cut to `04-after-columns.png` with `Matched 1 column of 20` boxed — the note is on none of it. (c) `stilltrue apply <orphan-id>` dry run: `field_description_removal on 'airport_fee'` / `- Only charged on LGA…` / `+ (removed)`, then `make demo` steps 6–7. (d) The same curl again → `[]`. Corner label through (b): *same file as the previous shot — `docs/evidence/04-after-columns.png`*. | "There's a second fault on the same page, and it has no pixels. The rename left a column description keyed to a column that no longer exists. No row to render it on, and the Agent Context Kit drops the aspect. StillTrue removes it — and the page afterwards is the same file. So the before and after has to be the aspect." |
| S10 | 1:54–2:15 (21s) | `bench/tlc-replay-results.jsonl` scrolling all 41 lines fast, settling on the `REPLAY-REPORT.md` result table. Then its own breakdown on screen: `1 quiet month · 1 event month · 39 months it kept saying so`. Cut to the `examples/abstention` block: `1 drift, 6 verified current, 29 abstained (36 checks)`. | "Forty-one months of the TLC's own published parquet schemas, ingested in order. The description is wrong from February 2023 onward, so the right answer is to report it every month after — forty-one consecutive decisions, all correct, zero false alarms. On DataHub's own showcase catalog it abstains twenty-nine times out of thirty-six, and reports no false drift." |
| S11 | 2:15–2:26 (11s) | The ten-line ledger stage list, with rows 2, 4 and 6 (`NOT_APPROVED`, `NOT_APPROVED`, `STALE`) boxed. Then `stilltrue verify --run …` → `OK: chain valid (10 records)`. | "Ten records in the chain for that one fix, because the two refusals are in it too. A ledger that only recorded successful writes would be a changelog." |
| S12 | 2:26–2:39 (13s) | Four GitHub PR headers stacked, each with its number, title and state visible: `datahub#18622`, `#18628`, `#18630`, `datahub-skills#49`. | "Building this hit four things in DataHub itself. Three fixes to the Agent Context Kit, and the drift workflow submitted as a DataHub skill, in DataHub's own repository. Four pull requests upstream — not plans." |
| S13 | 2:39–2:49 (10s) | README first screen, the `make demo` line, the Apache-2.0 badge. End card: repo URL, held to the last frame. | "One command against a DataHub quickstart, and every number regenerates from a named script. Your documentation is already lying to you somewhere. This finds out where." |

Word counts, for re-timing if the read comes in long or short: S1 34 · S2 22 ·
S3 26 · S4 37 · S5 25 · S6 38 · S7 28 · S8 24 · S9 62 · S10 56 · S11 28 ·
S12 34 · S13 26. Total 440.

**If it overruns**, cut in this order and nothing else: the second sentence of S6
("The confirmation is a hash…" — the on-screen `STALE` line already says it, −5s),
then the last sentence of S10 (the abstention figure, −8s), then S3 entirely
(−10s; S1's frame already carries the problem). That is 23 seconds of slack
without touching a shot that shows the graph changing.

---

## 2. Where each shot's footage comes from

Every path is relative to the repo root.

| # | Source | Notes |
|---|---|---|
| S1 | `docs/evidence/02-before-columns.png` | Exists. Regenerate: `python3 scripts/capture_ui.py "$URN" out.png --tab Columns --search airport` (the command in `docs/L3-EVIDENCE.md`). |
| S2 | `docs/evidence/04-after-columns.png` | Exists. Same command, run after the write. |
| S3 | `bench/REPLAY-REPORT.md`, the Month/Event table | Screen-record the rendered markdown. Underlying derivation: `bench/oracles/scan_tlc.py`. |
| S4 | `make demo` → `scripts/demo.sh` step 1 (`stilltrue scan --urn …` + `stilltrue findings`) | Live terminal. |
| S5 | `make demo` step 2 (`scripts/demo.sh:18-19`) | The refusal prints the diff itself — `src/stilltrue/cli.py` prints `- before` / `+ after` on the not-authorised path. |
| S6 | `make demo` step 3 (`scripts/demo.sh:21-29`) | The `--to` argument with the appended sentence is visible in the command line; the `STALE` reply follows. |
| S7 | `make demo` steps 4–5 (`scripts/demo.sh:31-36`) | |
| S8 | The `curl … /openapi/v2/timeline/v1/${URN}?categories=DOCUMENTATION&start=-1d&end=0` block in `docs/L3-EVIDENCE.md` §6 | Run it live right after S7's write; the reply is quoted in that section. |
| S9 | (a) and (d): the `curl … /aspects/${URN}?aspect=editableSchemaMetadata&version=0` block in `docs/L3-EVIDENCE.md`. (b) `docs/evidence/04-after-columns.png`, reused. (c) `stilltrue apply <orphan-id>` with no `--approve`, then `make demo` steps 6–7. | **(c) needs a separate take.** `scripts/demo.sh:45` pipes the dry run to `grep`, so the removal diff never reaches the screen during `make demo`. Run the dry run on its own first, then the demo. |
| S10 | `bench/tlc-replay-results.jsonl` (41 lines), `bench/REPLAY-REPORT.md` result and breakdown tables, `examples/abstention/README.md` scan block | All committed. Regenerate: `python3 bench/oracles/replay_tlc.py --months 41`. |
| S11 | `make demo` step 8 (`stilltrue verify --run "$RUN"`), plus the ledger stage list as printed in `examples/tlc-rename/README.md` §5; raw records in `docs/evidence/run-94b7e03ee841/audit-ledger.jsonl` | |
| S12 | `gh pr view` on datahub-project/datahub #18622, #18628, #18630 and datahub-project/datahub-skills #49, or the four PR pages | Verified OPEN on 2026-07-26. Titles: *expose description resolution for read paths* / *merge editableSchemaMetadata into schema fields* / *list_schema_fields crashes on a dataset with no schema aspect* / *add datahub-context-drift skill*. |
| S13 | `README.md`, `Makefile`, `LICENSE` | |

---

## 3. If it had to be twenty seconds

**Keep S1 and S2 — 0:00 to 0:20, trimming one second off S2's tail.**

That is deliberately the same edit as the opening, so front-loading and the
twenty-second cut are one decision instead of two.

Why those twenty and not the refusals, which are the better engineering:

- They are the only stretch that carries a claim a README cannot make. A judge
  can read "descriptions drift from schemas" in the text description and nod
  without believing anything. Watching DataHub's own page contradict itself in a
  single frame is not an argument, it is an observation — and the schema column
  and the documentation panel being in the *same* frame is what removes the
  "you cropped that" objection.
- The second half of it is the graph changing. "Use of DataHub" is scored on
  whether the project goes "beyond reading metadata and contribute[s] back to
  the graph"; twenty seconds that end on the corrected DataHub page pay that
  criterion directly, and Originality with it, because the fault shown is one
  no shipped DataHub view surfaces.
- Everything cut survives in text. The refusals, the audit chain, the 41 months
  and the pull requests are all in the README and the two `examples/` folders,
  and a judge who wants them will find them. The one thing text cannot carry is
  a frame that contradicts itself.

The cost, stated: those twenty seconds show detection and correction but not the
gate, so a judge who watches only them could believe this writes to a catalog
autonomously. That is the reason S5 and S6 sit at 0:46, not later.

---

## 4. The riskiest claim, and how it is worded

**The claim:** that the orphaned column description cannot be seen — S9.

**Why it is the riskiest one in the script.** It is load-bearing: the orphaned
note is the most original finding in the submission, and the reason it is worth a
detector is that nothing else surfaces it. It is also the easiest claim on the
list to disprove, and disproving it takes one command:

```bash
curl -s -u datahub:datahub "http://localhost:8080/aspects/${URN}?aspect=editableSchemaMetadata&version=0"
```

That returns the description. Anyone on this judging panel who has worked on the
Agent Context Kit will think of that route within seconds of hearing the word
"invisible", and the whole section — plus the credibility of everything after it
— goes with it.

**The wording that fails:** "DataHub can't see this description", "invisible in
DataHub", "documentation nothing can read". All three are false, and false in a
way the judge can check faster than we can explain.

**The wording in the script:** *"No row to render it on, and the Agent Context
Kit drops the aspect."*

That is scoped to two named surfaces and states the mechanism for each. The
dataset page's Columns tab iterates the current `schemaMetadata.fields` and
merges an `editableSchemaMetadata` entry onto a field it matches by `fieldPath`;
an entry whose `fieldPath` matches no current field is never reached by that
loop, so there is no row for it to render into. The Kit's
`clean_get_entities_response` deletes the aspect and nothing merges it back —
that is what `datahub#18628` is a fix for. Neither sentence says the data is
unreachable, and both stay true after the curl.

**And the shot shows the disproof route itself.** S9 opens on that exact curl
returning the description, which is how the detector's own before/after gets
made. Demonstrating the one route that *does* return it is what makes the narrow
claim credible instead of defensive — the judge does not get to discover the
exception, because the shot hands it over first.

Two runners-up, handled the same way:

- **"41 out of 41"** invites the reading that forty-one separate events were
  caught. They were not: one quiet month, one event month, and thirty-nine months
  of continuing to report an uncorrected description. The narration says
  "forty-one consecutive decisions", and S10 puts that 1 / 1 / 39 breakdown on
  screen, which is the same breakdown `bench/REPLAY-REPORT.md` prints — a judge
  who opens the report finds it already conceded.
- **"Four open pull requests"** is true today and decays: a maintainer merging or
  closing one changes the sentence without anyone touching the video. The
  narration says "four pull requests upstream", and the on-screen GitHub headers
  carry whatever state they are in. Merged would be better than open; either way
  the spoken line stays true.

---

## Production notes

1. **The one-letter difference needs a real zoom.** The captures are 1440×900;
   downscaled to 1080p, `airport_fee` versus `Airport_fee` is a couple of pixels.
   S1 and S2 must push to at least 300% on the documentation line, or the whole
   opening lands as two identical screenshots.
2. **Do not put `03-after-documentation.png` on screen uncropped.** Its main body
   correctly reads `Airport_fee`, but the Summary panel on the right of that same
   frame still reads lowercase `airport_fee`. Whatever the cause, it looks like
   the fix did not take. Safe pairs: `01`→`03` cropped to the main documentation
   body, or `02`→`04` cropped to the Summary panel. Never mix panels across a
   before/after pair.
3. **Pick one run and stay in it.** The hashes quoted in `docs/L3-EVIDENCE.md`
   (`a844edb7f3b94d57`, run `94b7e03ee841`) belong to the committed run; a fresh
   `make demo` produces different ids. If S4–S8 are re-recorded live, S11's ledger
   has to be recaptured from the same run, or a judge comparing frames sees two
   different proposal hashes for one write.
4. **S9(c) does not exist inside `make demo`.** Steps 3 and 6 capture their dry
   runs through a pipe, so the `+ (removed)` diff is never printed to the screen.
   Shoot `stilltrue apply <orphan-id>` on its own before running the demo.
5. **Burn in the key lines as on-screen text.** A judge working through many
   submissions may watch muted, and the two chips in S4 plus the boxed diffs in
   S5, S6 and S9 mean the video still argues its case with no audio.
6. **Terminal at ~100 columns, large font, bold `== N.` headers left intact.**
   `scripts/demo.sh` already prints them; they are the chapter markers.

## What was deliberately left out

Named so it is a decision rather than an omission, and so it can be reversed if
the runtime frees up:

- **The B0/B1/B2 baseline table** (`bench/REPORT.md`) — the sharpest answer to
  "doesn't DataHub already do this", and 15 seconds to read on screen. It stays
  in the README, which is where a judge scoring Originality will already be.
- **The orphaned-doc corpora** (4/4 on `dbt_hubspot`, 2/2 on `dbt_iterable`) —
  two positives cannot be spoken aloud without the paragraph explaining what two
  positives do and do not establish, and that paragraph does not fit.
- **The freeze, the mutation test, and the withdrawn benchmark** — the strongest
  integrity material in the repo and the least filmable; three of the shots above
  already rest on it silently.
- **Scope honesty about D2, D4 and D5** — stated plainly in the README's support
  boundary. Spending video seconds on what is not built, in a format where the
  judge cannot ask a follow-up, buys nothing the text does not already buy.
