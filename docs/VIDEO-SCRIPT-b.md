# Video script B — the credibility cut

> Target: 2:50 (170s), the Devpost ceiling. Written 2026-07-26 against the repo
> at `HEAD`. Every frame named here already exists as a file or a command in this
> repository; nothing in this document asks for footage that has to be invented.
>
> Deliberately **not** the product-demo cut. The argument for that choice is in
> §4, and the strongest case against this cut is in §5.

---

## 1. Thesis

**This video is not a feature tour — it is the evidence packet, and it spends its
170 seconds proving that this project's numbers could have come out wrong and
didn't, because everything that separates StillTrue from `datahub-enrich` is
invisible on a product screen.**

Two brief facts force it. First: *"Judges are not required to test the Project
and may choose to judge based solely on the text description, images, and video
provided in the Submission."* Whatever is not in the video may never exist.
Second: the criteria are equally weighted and the tie-break walks them in order,
**Use of DataHub first**. Both of those reward showing the machinery that would
have caught us lying, and neither rewards watching a description change on a page.

---

## 2. Shot list

Narration pace assumed: **150 words per minute = 2.5 words/second**, an
unhurried read for a technical audience. Word counts are literal counts of the
narration cell; hyphenated numbers are counted as spoken ("Twenty-five" = two
words). Shots 1, 2, 3, 5 and 8 carry the slack — that is where output lands and
the read can breathe. Shots 4, 6 and 7 run 0.2–0.6s past their cell and are read
at pace; the surplus elsewhere absorbs them, and the total holds.

| # | Timecode | Dur | On screen | Narration | Words | Spoken |
|---|---|---|---|---|---|---|
| 1 | 0:00–0:14 | 14s | Full-frame DataHub dataset page, `nyc_tlc.yellow_tripdata`, Columns tab filtered to `airport`. Two callouts drawn on the same frame: the single row `Airport_fee`, and the Summary panel on the right reading "…`airport_fee` applies to LGA and JFK pickups only." Header shows "Matched 1 column of 20". | "February 2023. New York's taxi commission renamed one column — airport underscore fee became capital-A Airport underscore fee. Nothing broke. This DataHub page has disagreed with itself ever since, and nothing on it says so." | 35 | 14.0s |
| 2 | 0:14–0:28 | 14s | Title card quoting `datahub-project/datahub-skills` frontmatter, the `datahub-search` line pulled large: *"For systematic audits ("how complete is our metadata"), use /datahub-audit."* The word **complete** underlined, then **not correct** typed in beneath it. | "Every catalog audit asks whether a description exists. DataHub's own search skill says it in one line — how complete is our metadata. Complete, not correct. Nobody checks whether the writing is still true." | 33 | 13.2s |
| 3 | 0:28–0:50 | 22s | Live terminal. `stilltrue scan --urn "…nyc_tlc.yellow_tripdata…"` runs; output lands: `3 drift, 5 verified current, 0 abstained (8 checks)` then the three finding lines (`D1_SCHEMA_BREAK`, `D1_UNDOCUMENTED`, `D1_ORPHANED_DOC`). Hold on the `5 verified current` as it is highlighted. | "StillTrue reads what the human wrote, then asks DataHub's timeline what actually happened. It does not decide that a word looks like a column name. A reference counts as broken only when DataHub's own change log records that field leaving. Five other columns in that sentence still resolve, and it reports those too." | 53 | 21.2s |
| 4 | 0:50–1:15 | 25s | Live terminal, second scan: `stilltrue scan --limit 25` against DataHub's own `showcase-ecommerce` datapack. Output: the truncation warning line `schema read incomplete (15 of 55), skipping the orphaned-doc check`, then `1 drift, 6 verified current, 29 abstained (36 checks)`. Highlight `29 abstained`, then pull the truncation line up and hold it. | "Twenty-five tables from DataHub's own showcase pack: twenty-nine times it answered I don't know. Look at the first line. That table has fifty-five columns; the read returned fifteen. A column missing from a short page looks like a column that was deleted — so the check that would delete its description refuses to run. Before that guard existed, it would have." | 63 | 25.2s |
| 5 | 1:15–1:53 | 38s | Four beats, cut tight. **(a)** back to the Columns frame from shot 1 — caption: "there is no `airport_fee` row". **(b)** terminal: `curl` on the `editableSchemaMetadata` aspect; output prints `'airport_fee' -> 'Only charged on LGA and JFK pickups. Zero for every other pickup zone, so filter it out before averaging.'` **(c)** three-line mechanism card: *DataHub never removes it / the Columns tab iterates current `schemaMetadata.fields`, so there is no row to render it into / the Agent Context Kit deletes the aspect* — cut straight to the GitHub page for `datahub#18628`, title legible, state **Open**. **(d)** terminal: `stilltrue apply <orphan> --approve <hash> --commit` → `VERIFIED`, the same `curl` returning `[]`, then the after-screenshot placed beside the before-screenshot — identical, with the filename overlaid on both to show it is one file. | "Now the finding a product demo cannot film. There is no airport underscore fee row on that page — but the description a human wrote for it is still in the graph. Here it is, from the aspect API. DataHub never removes it, the columns tab has no row to render it into, and the Agent Context Kit deletes the aspect before an agent sees it. That pull request is open upstream. We remove the orphan — and the page afterwards is the same file. Nothing moved, because nothing was ever on screen." | 91 | 36.4s |
| 6 | 1:53–2:19 | 26s | `bench/REPLAY-REPORT.md` rendered: the Result table (41 months / 41-of-41 / 0 false alarms), then the breakdown table directly under it scrolls into frame — *quiet 1/1, caught in the month it happened 1/1, still reported every month after 39/39*. Cut to a two-pane terminal: left runs `run_orphan_bench_datahub.py --mutate-skip-rewrite` → **0/2**; right runs `run_orphan_bench.py --mutate-skip-rewrite` → **2/2**. | "Forty-one months of the taxi commission's real published schemas: forty-one correct, no false alarms. Our own report says forty of those are the same answer. So here is the number that isn't marketing — break the benchmark on purpose and the new harness goes to zero out of two. The harness we replaced still says two out of two. It was never asking DataHub anything." | 66 | 26.4s |
| 7 | 2:19–2:42 | 23s | Fast cuts, terminal: `NOT_APPROVED: no confirmation supplied; re-run with --approve a844edb7f3b94d57` → `STALE: confirmation … does not match this proposal …; the text was edited after it was confirmed` → `VERIFIED: written and confirmed by read-back`. Cut to the `curl` on DataHub's timeline, DOCUMENTATION category, showing the `MODIFY` entry with the old and new sentence. End on a four-row card: `datahub#18622`, `#18628`, `#18630`, `datahub-skills#49` — titles and **Open** legible. | "Writing back. Without a confirmation the write is refused. Confirm one wording and write another, and it's refused again — the token is a hash of the text. The confirmed write lands, and DataHub's own change log records it. Four pull requests are open upstream: three fixes to the Agent Context Kit, and the drift workflow as a DataHub skill." | 59 | 23.6s |
| 8 | 2:42–2:50 | 8s | End card: repo URL, **Apache 2.0**, and the three-line quickstart from the README (`pip install -e .` / `make datahub-up` / `make demo`). Small print underneath: `docs/L3-EVIDENCE.md` · `bench/REPLAY-REPORT.md` · `examples/`. | "The repo reproduces every frame of this — the commands are in the README. Everything shown is committed, unedited." | 18 | 7.2s |

**Totals — 170s exactly (2:50), 418 words, 167.2s spoken, 2.8s of intentional beat.**

Where the beats sit: 0.8s in shot 2 as *not correct* types in; 0.8s in shot 3 as
the scan output lands; 1.6s in shot 5 split between the `curl` output and the two
identical screenshots. Everything else is continuous read.

---

## 3. Footage provenance

Nothing below is a mock-up. Every row is either a committed file or a command
that already runs in this repo.

| Shot | Produced by |
|---|---|
| 1 | `docs/evidence/02-before-columns.png`. Regenerate: `make load-benchmark` then `python3 scripts/capture_ui.py 'urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)' out.png --tab Columns --search airport`. (`01-before-documentation.png` is the alternate framing if the Summary panel reads small at video bitrate.) |
| 2 | Quote and table: `docs/NATIVE-COMPARISON.md` §"The agent-facing surface, by its own descriptions". Origin of the quote is the `datahub-search` skill frontmatter in `datahub-project/datahub-skills` — put that repo name on the card. |
| 3 | `scripts/demo.sh` step 1 (`stilltrue scan --urn "$URN" --server "$SERVER"`), i.e. the first thing `make demo` runs. Output shape matches `docs/L3-EVIDENCE.md` §2. **Film it live — see production note (a).** |
| 4 | `datahub datapack load showcase-ecommerce` then `stilltrue scan --limit 25`. The exact output is committed at `examples/abstention/README.md`; the verdict counts are checkable in `examples/abstention/1-findings.jsonl` (29 `INSUFFICIENT_EVIDENCE`, 6 `CURRENT`, 1 `DRIFT`). The truncation line is described in that README's "The truncated read in the output above". |
| 5a | `docs/evidence/02-before-columns.png` (reuse of shot 1). |
| 5b | `curl -s -u datahub:datahub "http://localhost:8080/aspects/${URN}?aspect=editableSchemaMetadata&version=0"` — `docs/L3-EVIDENCE.md` §"The orphaned note, which the UI cannot show at all". |
| 5c | Mechanism text: `docs/L3-EVIDENCE.md`, same section, and `docs/NATIVE-COMPARISON.md` §"Documentation nothing can display". PR page: `https://github.com/datahub-project/datahub/pull/18628` — verified 2026-07-26 as **Open**, title *"fix(agent-context): merge editableSchemaMetadata into schema fields"*. |
| 5d | `scripts/demo.sh` steps 6–7. Before/after aspect values: the `['airport_fee']` → `[]` table in `docs/L3-EVIDENCE.md`. The identical frame is `docs/evidence/04-after-columns.png`, which that document already uses twice on purpose. |
| 6 | Tables: `bench/REPLAY-REPORT.md` §Result. Regenerate: `python3 bench/oracles/scan_tlc.py` then `python3 bench/oracles/replay_tlc.py --months 41`; per-month rows in `bench/tlc-replay-results.jsonl`. Mutation panes: `python3 bench/run_orphan_bench_datahub.py --mutate-skip-rewrite` and `python3 bench/run_orphan_bench.py --mutate-skip-rewrite`; the two-by-two table is in `README.md` §"The benchmark that could not fail". |
| 7 | `scripts/demo.sh` steps 2, 3, 4; the exact refusal and `VERIFIED` strings are quoted in `docs/L3-EVIDENCE.md` §3 and §4. Timeline `curl` and its output: same document, §6. PR card — all four verified **Open** on 2026-07-26: `#18622` *"feat(agent-context): expose description resolution for read paths"*, `#18628` *"fix(agent-context): merge editableSchemaMetadata into schema fields"*, `#18630` *"fix(agent-context): list_schema_fields crashes on a dataset with no schema aspect"*, `datahub-skills#49` *"feat: add datahub-context-drift skill"*. |
| 8 | `README.md` §Quickstart. |

### Production notes

**(a) Do not lift shot 3's second line from `docs/L3-EVIDENCE.md`.** That
document's §2 block is from run `94b7e03ee841`, captured before the rename rule
was tightened. The committed evidence for that run
(`docs/evidence/run-94b7e03ee841/findings.jsonl`) says
`the schema has no \`airport_fee\`, but it does have \`Airport_fee\``, and that
string no longer exists in `detectors.py`. Current code
(`src/stilltrue/detectors.py:270-274`) emits
`DataHub's change log records it leaving at v…: …; the schema now has \`Airport_fee\``.
The **headline** line is unchanged (`cli.py:165` still renders
`airport_fee -> likely renamed to \`Airport_fee\``), so frame on that and let the
detail line be whatever the live run prints. A judge who runs `make demo` must
not get different text than the video showed.

**(b) Two repo inconsistencies to fix before filming**, because the video will
put them side by side with the README:

- `README.md` describes `examples/abstention/` as *"25 real tables, 14 honest 'I
  don't know's"*. The committed output in that example says **29**, and counting
  `examples/abstention/1-findings.jsonl` gives 29 `INSUFFICIENT_EVIDENCE`. The
  video uses 29. Fix the README line.
- `docs/L3-EVIDENCE.md` §2 and `bench/REPLAY-REPORT.md` §"What the evidence looks
  like" both quote the retired `but it does have` wording. Regenerate or annotate.

**(c) Shot 5's `curl` must be run against a freshly loaded benchmark.**
`make demo` resolves the orphan at step 6, so the `['airport_fee']` state only
exists before that. Film 5b immediately after `make load-benchmark`.

**(d) Cut order under time pressure.** If the edit runs long, drop shot 6's
mutation panes before anything else (−8s, keeps the 41/41 and the honest
breakdown). Next, shot 2 becomes a 6s card with no narration (−8s). Shot 5 is
never cut; it is the reason this cut exists.

### Deliberately left out, and why

- **DataHub's positional schema differ producing a rename that never happened.**
  The live `reality` string quotes DataHub's change log claiming
  `renaming of the field 'airport_fee to cbd_congestion_fee'` — a real artifact
  of comparing schema versions by position, which StillTrue filters out with the
  current schema. It is the sharpest "I read your differ more carefully than your
  docs did" beat available, and it costs 12 seconds this cut does not have. Worse,
  on screen at speed it reads as *our* tool getting the rename wrong. It belongs
  in the written description, not the video.
- **D5, D2, D4.** Two are not implemented and one is unwired. A video that
  gestures at five drift families invites a judge to go count them.
- **The audit ledger's hash chain.** Real, but it is ten lines of JSON that look
  like every other ten lines of JSON. Shot 7 spends its seconds on the refusals
  instead, which are the visible consequence of the same machinery.

---

## 4. The case against the obvious product-demo script

The obvious cut is: drifted DataHub page → run the tool → corrected DataHub page.
It is a legitimate video. It loses on four of the five criteria, and the losses
are not close.

**Originality** — *"Submissions should clearly go beyond features DataHub already
provides out of the box. Building on top of, extending, or composing shipped
features is welcome; rebuilding them as if from scratch isn't."*

The money shot of the product cut is a description changing on a DataHub page.
That is visually indistinguishable from `datahub-enrich`, whose own frontmatter
reads *"add or update metadata in DataHub: descriptions, tags, glossary terms"*.
Nick Adams is on the panel and wrote the post naming the **Data Steward Agent**
that *"applies glossary terms and descriptions"* — a judge watching a description
get written has been handed the pattern-match. And the one finding that
provably has no DataHub surface at all, `D1_ORPHANED_DOC`, is exactly the finding
a product demo cannot show. So the obvious script systematically spends its
entire runtime on the half of this project that already looks shipped, and
0 seconds on the half that doesn't exist anywhere in DataHub open source.

**Use of DataHub** — *"The strongest submissions go beyond reading metadata and
contribute back to the graph where appropriate."* This is also the **first
tie-breaker**.

The product cut shows one `update_description` call. It never shows the timeline
read — nine change categories, documented in the skills repo's own agent-facing
CLI reference, **zero mentions across all five shipped skills and nothing in the
Kit's thirty-eight exported symbols** (`docs/NATIVE-COMPARISON.md`). It never
shows the four upstream PRs. The **Bonus: Meaningful Open-Source Contribution**
criterion gets nothing at all. Shot 7 buys back two criteria and the tie-break
for 23 seconds; the product cut spends those 23 seconds on browser page loads.

**Technical Execution** — *"whether the project actually works end-to-end. Does
the code do what the submission claims?"*

A happy path proves the claim can be true once. This project's actual claim is
41 consecutive correct decisions and a benchmark that drops to 0/2 when
deliberately broken — neither of which is a screen state, and both of which
answer the question the criterion is really asking. There is also a hard clock
argument: a live drifted→fixed loop through the DataHub UI burns roughly a third
of 170 seconds on page loads and terminal scroll, at which point nothing else
fits and the choice has been made by the edit rather than by anyone.

**Submission Quality** — *"A judge should be able to understand what the project
does, why it matters, and find clear setup instructions."*

The product cut answers "what it does" and skips "why it matters". Here, "why it
matters" is a category argument — *complete* versus *correct* — that these judges
have already published in their own words. Handing it back to them verbatim
(shot 2, 14 seconds) is the cheapest credibility available in the entire video,
and the product script has no slot for it.

**And one thing that is not a criterion but decides ranking.** 1,855 registrants
across four tracks, and the modal submission for *Agents That Do Real Work* is
"the agent reads DataHub, takes an action, writes the result back — here is the
before and after page." That is the shape the brief itself describes. Being the
two-hundredth before/after page is a positioning loss that execution quality does
not recover, and since judges may score on the video alone, whatever the video
omits may as well not have been built.

---

## 5. The strongest objection to this cut

Stated as a judge would state it, not softened:

> The rules say the video *"should include footage that shows the Project
> functioning and in action,"* and Stage One is a pass/fail viability screen. This
> cut spends its longest shot — 38 seconds, more than a fifth of the runtime — on
> a finding whose fix produces **no visible change**, and its next 26 seconds on a
> benchmark being deliberately broken. A judge watching at 1.5× with six more
> submissions queued could reach the end without a clear memory of the product
> doing anything. Meanwhile the honesty shots hand over, pre-formatted, every
> weakness a reviewer would otherwise have had to dig for: it abstains on 29 of 36
> checks, it nearly deleted a live column's description, 40 of its 41 months are
> the same answer. **Real-World Usefulness** is where that lands — "would a real
> platform team see clear value" is a harder yes after watching a tool say *I
> don't know* twenty-nine times. And a flaw the author narrates cannot be argued
> down later; a flaw the judge finds can at least be answered.

That objection is correct about the risk and I would still ship this cut. Three
reasons, in order of weight.

**The asymmetry of ceilings.** If the video shows features, the best available
reaction from this panel is *"nice — we have a skill for that."* If it shows
falsifiability, the best available reaction is *"this person found three bugs in
our Agent Context Kit and one hole in our data model, and shipped patches for all
four."* The first reaction places. The second one is what a $6,000 grand prize
from an engineering panel is actually for. The floor is similar; the ceiling is
not close.

**The functioning-and-in-action requirement is met, and met early.** Shots 3, 4,
5b, 5d and 7 are all live terminal against a real DataHub instance, and a real
write lands in DataHub's own change log by 2:42. Stage One asks whether the
project *"reasonably fits the theme and reasonably applies the required
APIs/SDKs"* — satisfied by 0:50. The risk is not failing the gate; it is a
weaker impression on a distracted viewer, and that is a trade, not a
disqualification.

**The honesty shots are framed as claims, not confessions.** 29 abstentions is
stated as the price of zero false drift verdicts, in one sentence, with the
number it bought. The truncated read is stated as a guard that fires on DataHub's
own showcase datapack — an audience running a catalog at Pinterest scale hears
"it refuses when the read was incomplete" as a feature, because they are the ones
who get paged when it isn't. The repo also holds the number that proves the point
in the other direction: the design this one replaced surfaced 9 true findings
against 87 false ones, 9.4% precision, and a platform team receiving 96 alerts of
which 87 are wrong switches the tool off.

**Where I would concede ground.** If the panel skews toward product review rather
than engineering review — and Alyssa Lee and Wenjia You are unknowns on that axis
— the product cut is the safer expected value and this one has the fatter tail. I
am choosing the fat tail on purpose, because in a field of 1,855 the safe cut's
expected value is a placement and the whole point of entering is not to place.
The hedge that costs nothing: the Devpost **text description** carries the
product narrative in full, with `docs/L3-EVIDENCE.md` linked at the top. A judge
who wants the before/after page is one click from four screenshots of it. The
video's 170 seconds go to the thing that cannot be recovered from a link — being
believed.
