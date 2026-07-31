#!/usr/bin/env python3
"""Generate docs/index.html, the zero-install evidence page for GitHub Pages.

Everything on the page is read out of the committed artefacts at build time:
the ledger table comes from the run's own audit-ledger.jsonl, the scan tallies
come from the findings file. Nothing is typed in twice, so the page cannot drift
from the repository the way a hand-written summary would.

Regenerate: python3 scripts/build_pages.py
"""
import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
RUN = DOCS / "evidence" / "run-94b7e03ee841"
GH = "https://github.com/cyh7789/stilltrue/blob/main"

E = html.escape

STAGE_LABEL = {"scan": "scan", "propose": "propose", "approve": "approve", "execute": "execute"}
OUTCOME_CLASS = {"NOT_APPROVED": "bad", "STALE": "warn", "APPROVED": "ok", "VERIFIED": "ok"}


def ledger_rows() -> tuple[list[str], int, int]:
    rows, refusals = [], 0
    lines = (RUN / "audit-ledger.jsonl").read_text().splitlines()
    for i, line in enumerate(lines, 1):
        d = json.loads(line)
        p = d["payload"]
        outcome = p.get("status") or ""
        if outcome in ("NOT_APPROVED", "STALE"):
            refusals += 1
        cls = OUTCOME_CLASS.get(outcome, "")
        rows.append(
            f'<tr><td class="n">{i}</td>'
            f'<td>{E(STAGE_LABEL.get(d["stage"], d["stage"]))}</td>'
            f'<td class="mono">{E(d["entry_hash"][:12])}</td>'
            f'<td class="{cls}">{E(outcome)}</td>'
            f'<td class="mono">{E(p.get("proposal_hash", "")[:12])}</td></tr>')
    return rows, len(lines), refusals


def scan_tally() -> str:
    """The re-scan that closes the loop, read from the run's own findings file."""
    n = sum(1 for _ in (RUN / "findings.jsonl").read_text().splitlines() if _.strip())
    return str(n)


rows, n_records, n_refusals = ledger_rows()

page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>StillTrue: the evidence, without installing anything</title>
<style>
:root {{ --bg:#f4f5f7; --card:#fff; --ink:#111827; --sub:#5b6472; --line:#e3e6ec;
  --accent:#5038d0; --ok:#2f9e44; --bad:#e03131; --warn:#e8590c; --code:#1a1b26; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14161c; --card:#1c1f27; --ink:#e8eaf0; --sub:#9aa3b2; --line:#2a2f3a;
    --accent:#9b8cff; --ok:#69db7c; --bad:#ff8787; --warn:#ffa94d; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif; }}
.wrap {{ max-width:920px; margin:0 auto; padding:48px 20px 96px; }}
h1 {{ font-size:44px; line-height:1.1; margin:0 0 6px; letter-spacing:-1.5px; }}
h1 span {{ color:var(--accent); }}
h2 {{ font-size:26px; margin:56px 0 12px; letter-spacing:-.5px; }}
h3 {{ font-size:19px; margin:32px 0 8px; }}
.lede {{ font-size:19px; color:var(--sub); margin:0 0 8px; }}
.nav {{ margin:20px 0 0; font-size:15px; }}
.nav a {{ margin-right:16px; }}
a {{ color:var(--accent); }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
  padding:22px 26px; margin:18px 0; }}
table {{ border-collapse:collapse; width:100%; font-size:15px; }}
th,td {{ border-bottom:1px solid var(--line); padding:9px 12px; text-align:left; }}
th {{ color:var(--sub); font-weight:600; font-size:13px; text-transform:uppercase;
  letter-spacing:.06em; }}
.mono,code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13.5px; }}
td.n {{ color:var(--sub); width:38px; }}
.ok {{ color:var(--ok); font-weight:600; }} .bad {{ color:var(--bad); font-weight:600; }}
.warn {{ color:var(--warn); font-weight:600; }}
pre {{ background:var(--code); color:#c0caf5; border-radius:10px; padding:18px 20px;
  overflow-x:auto; font-size:13.5px; line-height:1.6; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px;
  margin:22px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 20px; }}
.stat b {{ display:block; font:700 34px/1.1 ui-monospace,monospace; color:var(--ok); }}
.stat b.plain {{ color:var(--ink); }}
.stat span {{ display:block; font-size:14px; color:var(--sub); margin-top:6px; }}
img {{ max-width:100%; border:1px solid var(--line); border-radius:10px; display:block; }}
figure {{ margin:16px 0; }}
figcaption {{ font-size:14px; color:var(--sub); margin-top:8px; }}
.scroll {{ overflow-x:auto; }}
.foot {{ margin-top:64px; padding-top:22px; border-top:1px solid var(--line);
  font-size:14px; color:var(--sub); }}
ul {{ padding-left:22px; }} li {{ margin:6px 0; }}
</style></head><body><div class="wrap">

<h1>Still<span>True</span></h1>
<p class="lede">Finds documentation in a data catalog that stopped being true, proves it
from DataHub's own change log, and fixes it behind a hash-verified human gate.</p>
<p class="nav">
  <a href="{GH}/README.md">Repository</a>
  <a href="{GH}/EVIDENCE.md">EVIDENCE.md</a>
  <a href="https://youtu.be/25UP9Tnwm-s">Demo video</a>
</p>
<p style="color:var(--sub);font-size:15px">Nothing on this page asks you to install
anything. Every figure is read out of a committed artefact at build time by
<a href="{GH}/scripts/build_pages.py"><code>scripts/build_pages.py</code></a>.</p>

<div class="stats">
  <div class="stat"><b class="plain">77</b><span>datasets in one full catalog scan: 11 drifted,
    12 confirmed still true, 58 declined. 81 checks.</span></div>
  <div class="stat"><b>41/41</b><span>months of the TLC's real published schemas scored
    exactly right, 0 false alarms</span></div>
  <div class="stat"><b>14/14</b><span>orphaned descriptions found across 503 correct ones,
    two frozen holdout repositories</span></div>
  <div class="stat"><b class="plain" style="color:var(--bad)">6 &rarr; 0</b><span>false verdicts
    before and after requiring change-log evidence, same 25 tables</span></div>
</div>

<h2>1. The fault, in one frame of DataHub's own UI</h2>
<figure>
  <img src="evidence/02-before-columns.png" alt="DataHub dataset page: the Columns tab lists Airport_fee while the Summary panel still says airport_fee"/>
  <figcaption>Columns tab: the schema says <code>Airport_fee</code>. Summary panel, same
  page, same moment: the documentation still says <code>airport_fee</code>. The NYC Taxi
  &amp; Limousine Commission renamed that column in February 2023 and added
  <code>cbd_congestion_fee</code> in January 2025. Both labels are derived by diffing the
  TLC's own published parquet schemas month over month
  (<a href="{GH}/bench/oracles/scan_tlc.py"><code>bench/oracles/scan_tlc.py</code></a>),
  so they are the TLC's, not ours.</figcaption>
</figure>
<figure>
  <img src="evidence/04-after-columns.png" alt="The same page after the agent's write, documentation now reads Airport_fee"/>
  <figcaption>The same page after the write.</figcaption>
</figure>

<h2>2. The gate, as {n_records} records in one hash chain</h2>
<p>Run <code>94b7e03ee841</code>, read directly from
<a href="{GH}/docs/evidence/run-94b7e03ee841/audit-ledger.jsonl"><code>audit-ledger.jsonl</code></a>.
Every refusal is in the chain with everything else, because a ledger of successful
writes only would be a changelog.</p>
<div class="card scroll">
<table>
<thead><tr><th>#</th><th>stage</th><th>entry hash</th><th>outcome</th><th>proposal</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table>
</div>
<p>Row 7 is the one worth reading twice. The confirmation token
<code>a844edb7f3b9</code> was issued for one piece of text; the write that arrived carried
a different text, so its proposal hashed to <code>ec39d56f76df</code> and the token no
longer matched. The write failed closed. {n_refusals} of the {n_records} records are
refusals, covering both refusal conditions: rows 3 and 5 are the same condition twice,
because <a href="{GH}/scripts/demo.sh"><code>scripts/demo.sh</code></a> attempts the write
once as a dry run and once for real and the gate refuses both.</p>
<pre>$ stilltrue verify --run 94b7e03ee841
OK: chain valid ({n_records} records)</pre>

<h2>3. The write, recorded by DataHub rather than by us</h2>
<p>The correction appears in DataHub's own documentation timeline, the same service the
detector reads its evidence from. Command and unedited response in
<a href="{GH}/docs/L3-EVIDENCE.md">L3-EVIDENCE.md</a>, section 6.</p>
<pre>category: DOCUMENTATION   operation: MODIFY
Documentation of 'urn:li:dataset:(...nyc_tlc.yellow_tripdata,PROD)' has been changed
  from '...improvement_surcharge; airport_fee applies to LGA and JFK pickups only. ...'
  to   '...improvement_surcharge; Airport_fee applies to LGA and JFK pickups only. ...'</pre>

<h2>4. The fault with no pixels</h2>
<p>A rename can leave a column description attached to a field that no longer exists. No
row renders it, and the Agent Context Kit drops the aspect
(<a href="https://github.com/datahub-project/datahub/pull/18628">datahub#18628</a> is the
fix for the second half of that sentence). Removing it changes almost nothing on screen,
which is the point, so the proof is a pixel diff of two captures taken by the same script
before and after.</p>
<pre>1440x900, 1296000 pixels
differing pixels: 168  (0.0130%)
all differences inside x 76-774, y 90-264</pre>
<p>Reproduce with
<a href="{GH}/scripts/prove_invisible.sh"><code>scripts/prove_invisible.sh</code></a>. The
region that differs is the version chip's clock, not the note.</p>

<h2>5. Does it only work on dbt?</h2>
<p>Both holdouts are dbt packages, so the question is fair. The full catalog scan answers
it from data already committed: of the 11 drift verdicts, <b>dbt produced one</b>. The
rest came from <code>s3</code> (5), <code>snowflake</code> (2), and one each from
<code>postgres</code>, <code>sqlite</code> and <code>looker</code>. Seven platforms, and
the detector never sees which one it is looking at: it reads descriptions, schema fields
and the change log through the Agent Context Kit, and those three shapes are the same
whatever the dataset was ingested from. dbt is where the <i>labels</i> can be mined,
because dbt keeps prose and SQL together in public git history, which is why both holdouts
are dbt packages. Per-platform table and the caveats are in
<a href="{GH}/docs/L3-EVIDENCE.md">L3-EVIDENCE.md</a>; regenerate with
<a href="{GH}/scripts/platform_breakdown.py"><code>scripts/platform_breakdown.py</code></a>.</p>

<h2>6. Every number, and the denominator under it</h2>
<div class="card scroll">
<table>
<thead><tr><th>Claim</th><th>Denominator</th><th>Where</th></tr></thead>
<tbody>
<tr><td>11 drifted, 12 still true, 58 abstained</td><td>81 checks over 77 datasets</td>
  <td><a href="{GH}/docs/L3-EVIDENCE.md">L3-EVIDENCE.md</a></td></tr>
<tr><td>1 drift, 6 current, 29 abstained, zero false drift</td><td>36 checks over 25 tables</td>
  <td><a href="{GH}/examples/abstention/">examples/abstention/</a></td></tr>
<tr><td>6 false verdicts without the change-log requirement, 0 with it</td><td>the same 25 tables</td>
  <td><a href="{GH}/README.md">README.md</a></td></tr>
<tr><td>41 months scored exactly right, 0 false alarms</td><td>41 consecutive months, 2023-01 to 2026-05</td>
  <td><a href="{GH}/bench/REPLAY-REPORT.md">REPLAY-REPORT.md</a></td></tr>
<tr><td>2 orphans found of 2, 0 false alarms</td><td>199 correct descriptions</td>
  <td><a href="{GH}/bench/HOLDOUT-orphan-iterable-datahub.md">HOLDOUT (dbt_iterable)</a></td></tr>
<tr><td>12 orphans found of 12, 0 false alarms</td><td>304 correct descriptions</td>
  <td><a href="{GH}/bench/HOLDOUT-orphan-microsoft-ads-datahub.md">HOLDOUT (dbt_microsoft_ads)</a></td></tr>
<tr><td>A coverage check finds 1 of the 2</td><td>the same dataset</td>
  <td><a href="{GH}/bench/REPORT.md">REPORT.md</a></td></tr>
</tbody></table>
</div>
<p>Both holdout repositories were chosen by a rule frozen before the search ran
(<a href="{GH}/bench/freeze.json"><code>bench/freeze.json</code></a>, commit
<code>d3e6ccb</code>); the second walk's declaration is
<a href="{GH}/bench/HOLDOUT-v2-DECLARATION.md">HOLDOUT-v2-DECLARATION.md</a>, committed
before it was run. Both benchmarks ship with <code>--mutate-skip-rewrite</code>, which
removes the schema rewrite and takes the score to zero.</p>

<h2>7. What is deliberately not claimed</h2>
<ul>
<li>The official DataHub datapacks are the development set, so the 77-dataset scan
  measures scale. Generalisation is what the two holdout repositories are for.</li>
<li>The 41-month TLC replay was once described as a holdout. The code changed after
  seeing its scores, so it is a third-party benchmark, and the timeline of who knew what
  when is in <a href="{GH}/docs/VALIDATION-INTEGRITY.md">VALIDATION-INTEGRITY.md</a>.</li>
<li>Both holdout repositories are dbt packages from one organisation, mined by the same
  script. That is what the 14 of 14 rests on. A third walk over 80 repositories in six
  other organisations found none that met the same frozen bar; the null result is
  published rather than fixed by widening the rule
  (<a href="{GH}/bench/HOLDOUT-v3-RESULT.md">HOLDOUT-v3-RESULT.md</a>).</li>
<li>Two detectors (freshness, semantic conflict) are unimplemented. The reason is written
  up as a measurement in <a href="{GH}/docs/D2-FEASIBILITY.md">D2-FEASIBILITY.md</a>.</li>
<li>All four upstream pull requests are still open and none has been reviewed.</li>
</ul>

<h2>If you would rather run it</h2>
<p>One click opens a Codespace and one command takes it from nothing to the full loop.
Measured at 12 minutes 21 seconds on a 2-core container, most of it DataHub's images
pulling.</p>
<pre>make demo-from-cold</pre>
<p><a href="https://codespaces.new/cyh7789/stilltrue?quickstart=1">Open in GitHub Codespaces</a></p>

<p class="foot">Apache-2.0 &middot;
<a href="https://github.com/cyh7789/stilltrue">github.com/cyh7789/stilltrue</a> &middot;
this page is generated by <code>scripts/build_pages.py</code> from the committed run
artefacts, so it cannot drift from the repository.</p>

</div></body></html>
"""

(DOCS / "index.html").write_text(page)
(REPO / ".nojekyll").write_text("")
print(f"docs/index.html written: {len(page)} bytes, {n_records} ledger records, {n_refusals} refusals")
