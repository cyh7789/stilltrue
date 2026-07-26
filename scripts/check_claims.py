#!/usr/bin/env python3
"""Check the numbers in the documents against the files they come from.

Every figure verified here was wrong in this repository at least once, and none
of them was caught by reading. They were caught by an outside reviewer, after
being committed. The pattern was always the same: a number gets written at the
moment it is needed, from memory or expectation, and then later work builds on
it as though it had been established.

So the checks live here instead of in an intention to be careful. Run before
committing anything that quotes a figure:

    python3 scripts/check_claims.py

Exit 1 on any mismatch, naming the document, the claim and the source.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile(r"[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*")

# Shot durations, seconds. The script's own table is the source for everything
# else; these are the only numbers not derivable from it.
SHOT_SECONDS = {1: 12, 2: 9, 3: 8, 4: 23, 5: 20, 6: 12, 7: 32, 8: 22, 9: 14,
                10: 12, 11: 6}
WPM_CEILING = 160          # above this a line stops being readable aloud

failures: list[str] = []


def fail(where: str, claimed: object, actual: object, why: str) -> None:
    failures.append(f"{where}\n    claims {claimed!r}, source says {actual!r}\n    {why}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def check_video_script() -> None:
    """Per-shot word counts, the total, and the readability ceiling."""
    doc = "docs/VIDEO-SCRIPT.md"
    text = read(doc)

    total = 0
    fastest = (0, 0.0)
    for line in text.splitlines():
        m = re.match(r'\| (\d+) \| \d:\d\d–\d:\d\d \|.*?\| "(.*)" \((\d+)w\) \|$', line)
        if not m:
            continue
        shot, narration, claimed = int(m.group(1)), m.group(2), int(m.group(3))
        actual = len(WORD.findall(narration))
        total += actual
        if actual != claimed:
            fail(f"{doc} shot {shot}", claimed, actual, "per-shot word count")
        seconds = SHOT_SECONDS[shot]
        wpm = actual * 60 / seconds
        if wpm > WPM_CEILING:
            fail(f"{doc} shot {shot}", f"{seconds}s", f"{wpm:.0f} wpm",
                 f"above the {WPM_CEILING} wpm ceiling; shorten it or lengthen the slot")
        if wpm > fastest[1]:
            fastest = (shot, wpm)

    if not total:
        fail(doc, "a narration table", "no rows matched", "the table format changed")
        return

    m = re.search(r"\*\*2:50 total\. (\d+) words of narration — (\d+) wpm overall, "
                  r"nothing above (\d+)\.\*\*", text)
    if not m:
        fail(doc, "a header stating words/wpm/ceiling", "no match", "header format changed")
        return

    stated_total, stated_wpm, stated_max = (int(g) for g in m.groups())
    if stated_total != total:
        fail(f"{doc} header", stated_total, total, "total narration words")
    if stated_wpm != round(total * 60 / 170):
        fail(f"{doc} header", stated_wpm, round(total * 60 / 170), "overall wpm")
    if stated_max < round(fastest[1]):
        fail(f"{doc} header", f"nothing above {stated_max}",
             f"shot {fastest[0]} at {fastest[1]:.0f}", "stated ceiling is too low")


def check_retraction_table() -> None:
    """The "Now" column of the retraction table must quote the live narration.

    That table exists so a retracted sentence cannot come back. It went stale
    twice while the narration moved on, which points the one artefact meant to
    prevent regressions at the wrong target -- someone restoring "the fixed
    version" would restore a sentence that was itself rejected.
    """
    doc = "docs/VIDEO-SCRIPT.md"
    text = read(doc)
    narration = " ".join(re.findall(r'\| "(.*?)" \(\d+w\) \|', text))
    if not narration:
        fail(doc, "a narration table", "no rows matched", "table format changed")
        return

    body = text.split("**Now fixed in the text above:**")
    if len(body) < 2:
        fail(doc, "a retraction table", "no match", "section heading changed")
        return

    lowered = narration.lower()
    for row in body[1].splitlines():
        cells = [c.strip() for c in row.split("|")]
        if len(cells) < 5 or cells[1].startswith(("---", "Was")):
            continue

        # Take only the quoted span: a cell may carry prose after it ("… — the
        # mechanism, not a person"), and a cell with no quote at all is "cut" or
        # a pointer elsewhere. A trailing ellipsis marks an abbreviated citation,
        # so the quote is matched as a prefix rather than in full -- these are
        # citations of the narration, not copies of it.
        m = re.match(r'"(.+?)"', cells[3])
        if not m:
            continue
        quoted = m.group(1).rstrip("…").rstrip()
        if quoted.lower() not in lowered:
            fail(f"{doc} retraction table", quoted[:60],
                 "not present in any narration cell",
                 f"the Now column for {cells[1][:40]} quotes a line the script no longer says")


def check_replay() -> None:
    """41/41 and the 1 + 1 + 39 breakdown against the per-month results."""
    rows = [json.loads(l) for l in read("bench/tlc-replay-results.jsonl").splitlines() if l.strip()]
    months, correct = len(rows), sum(1 for r in rows if r["correct"])
    quiet = sum(1 for r in rows if not r["expected"])

    # An onset is a month where the expected set *changes*, not merely a month
    # DataHub recorded an event in: 2025-01 added a column, which this detector
    # does not score, so its expected set is the one carried over from 2023-02.
    # Counting event months instead made this check disagree with a correct
    # report -- and the report was right.
    onset, previous = 0, set()
    for r in rows:
        current = set(r["expected"])
        if current != previous:
            onset += 1 if current else 0
            previous = current
    holds = months - onset - quiet

    report = read("bench/REPLAY-REPORT.md")
    for pattern, actual, what in [
        (r"\| Months replayed \| \*\*(\d+)\*\*", months, "months replayed"),
        (r"\| Months scored exactly right \| \*\*(\d+)/(\d+)\*\*", (correct, months), "score"),
        (r"\| Still reported every month after, never withdrawn \| (\d+)/", holds, "holds"),
    ]:
        m = re.search(pattern, report)
        if not m:
            fail("bench/REPLAY-REPORT.md", what, "no match", "report format changed")
            continue
        claimed = tuple(int(g) for g in m.groups()) if len(m.groups()) > 1 else int(m.group(1))
        if claimed != actual:
            fail("bench/REPLAY-REPORT.md", claimed, actual, what)

    # `\**` because the figure is bolded in prose -- "**41/41** months exactly
    # right". Without it this loop matched nothing and reported success while
    # being blind to the number it exists to check; a mutation test caught that,
    # reading it did not.
    score = re.compile(r"(\d+)/(\d+)\**\s*(?:months exactly right|月精確)")
    for doc in ("README.md", "docs/STATUS.md", "HANDOFF.md"):
        seen = 0
        for m in score.finditer(read(doc)):
            seen += 1
            if (int(m.group(1)), int(m.group(2))) != (correct, months):
                fail(doc, m.group(0), f"{correct}/{months}", "TLC replay score")
        if not seen:
            fail(doc, "a TLC replay score", "no match",
                 "the phrasing changed; this check is no longer reading anything")


def check_orphan_corpora() -> None:
    """The orphaned-doc denominators against the label files."""
    for name, report in [("iterable", "bench/HOLDOUT-orphan-iterable-datahub.md"),
                         ("hubspot", "bench/HOLDOUT-orphan-hubspot-datahub.md")]:
        labels = [json.loads(l) for l in
                  read(f"bench/oracles/orphaned-dbt-{name}.jsonl").splitlines() if l.strip()]
        pos = sum(1 for r in labels if r["label"] == "orphaned")
        neg = len(labels) - pos
        text = read(report)
        m = re.search(r"\| Orphaned documentation asserted \| \*\*(\d+)/(\d+)\*\* \|", text)
        if m and int(m.group(2)) != pos:
            fail(report, f"denominator {m.group(2)}", pos, "positives in the label file")
        m = re.search(r"\| False alarms on correct documentation \| \*\*(\d+)/(\d+)\*\* \|", text)
        if m and int(m.group(2)) != neg:
            fail(report, f"denominator {m.group(2)}", neg, "negatives in the label file")


def check_abstention_example() -> None:
    """The abstention count quoted in README against the committed findings."""
    rows = [json.loads(l) for l in
            read("examples/abstention/1-findings.jsonl").splitlines() if l.strip()]
    abstained = sum(1 for r in rows if r["verdict"] == "INSUFFICIENT_EVIDENCE")
    m = re.search(r"25 real tables, (\d+) honest", read("README.md"))
    if m and int(m.group(1)) != abstained:
        fail("README.md", int(m.group(1)), abstained, "abstentions in examples/abstention")


def check_freeze_count() -> None:
    """How many files the documents say are frozen, against freeze.json."""
    frozen = len(json.loads(read("bench/freeze.json"))["files"])
    for doc, pattern in [("HANDOFF.md", r"\*\*(\S+)個檔案\*\*（第五輪）"),
                         ("README.md", r"(\w+) files are hashed")]:
        m = re.search(pattern, read(doc))
        if not m:
            continue
        words = {"nine": 9, "eight": 8, "ten": 10, "九": 9, "八": 8, "十": 10}
        claimed = words.get(m.group(1), None)
        if claimed is None:
            claimed = int(m.group(1)) if m.group(1).isdigit() else None
        if claimed is not None and claimed != frozen:
            fail(doc, claimed, frozen, "number of frozen files")


def check_test_count() -> None:
    """Test counts quoted in prose, against a real run."""
    out = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    m = re.search(r"(\d+) passed", out)
    if not m:
        fail("pytest", "a passing run", out.strip().splitlines()[-1:], "suite did not report")
        return
    passed = int(m.group(1))
    for doc, pattern in [("HANDOFF.md", r"(\d+) 測試綠"),
                         ("docs/STATUS.md", r"(\d+) 個測試通過")]:
        for m2 in re.finditer(pattern, read(doc)):
            if int(m2.group(1)) != passed:
                fail(doc, int(m2.group(1)), passed, "tests passing")


def main() -> None:
    for check in (check_video_script, check_retraction_table, check_replay, check_orphan_corpora,
                  check_abstention_example, check_freeze_count, check_test_count):
        try:
            check()
        except FileNotFoundError as exc:
            failures.append(f"{check.__name__}: missing file {exc.filename}")

    if failures:
        print(f"{len(failures)} claim(s) do not match their source:\n")
        for f in failures:
            print(f"  {f}\n")
        sys.exit(1)
    print("every checked claim matches its source")


if __name__ == "__main__":
    main()
