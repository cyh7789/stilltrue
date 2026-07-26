#!/usr/bin/env python3
"""Freeze the graded system, or check a freeze is still intact.

The point of a freeze is to make one claim checkable: that the numbers reported
against a source acquired afterwards were produced by *this* code, and that the
code did not move once the numbers were seen. A prose promise cannot be checked;
a hash can.

What is frozen: the detector, the description resolver it depends on, the label
miner (which defines the categories), and the scoring script. Also frozen is the
source-selection rule -- written before any candidate was looked at, so the
choice of benchmark cannot be an outcome of preferring one.

Usage:
  python3 bench/freeze.py            # write freeze.json
  python3 bench/freeze.py --check    # exit 1 if any frozen file changed
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FREEZE_FILE = ROOT / "bench" / "freeze.json"

FROZEN_FILES = [
    "src/stilltrue/detectors.py",             # the rules themselves
    "src/stilltrue/adapter.py",               # which text gets judged, and the change-log read
    "src/stilltrue/evidence.py",              # what counts as a citation
    "bench/oracles/replay_tlc.py",            # how a replay is scored
    "bench/oracles/mine_orphaned_docs.py",    # what counts as orphaned documentation
    "bench/oracles/mine_drift_labels.py",     # how a model's columns are read out of git
    "bench/run_orphan_bench.py",              # superseded; kept so its result stays checkable
    "bench/run_orphan_bench_datahub.py",      # how orphan labels are scored now
    "bench/select_holdout.py",                # which source gets graded
]

# Written before any candidate repository was inspected. Mechanical on purpose:
# with a rule this specific there is no room to prefer a source that scores well.
SELECTION_RULE = {
    "population": "public repositories under github.com/fivetran whose name starts with 'dbt_'",
    "exclude": [
        "dbt_shopify and any dbt_shopify_* variant -- already used as a development benchmark",
        "dbt_ad_reporting -- mined during the v1 selection walk, so its contents were seen",
        "dbt_amplitude, dbt_asana, dbt_facebook_ads -- same, mined during the v1 walk",
        "dbt_fivetran_log, dbt_hubspot -- scored under earlier designs and mined since",
        "repositories archived at selection time",
    ],
    "order": "alphabetical by repository name",
    "take": "the first repository satisfying every threshold below",
    "thresholds": {
        "license": "Apache-2.0, MIT or BSD",
        "commits": ">= 200",
        "history_months": ">= 12",
        "column_descriptions": ">= 50",
        "mined_positives": ">= 30",
        "mined_negatives": ">= 100",
    },
    "runs_allowed": 1,
    "on_result": "published as measured; the frozen files are not modified in response",
    "round": 6,
    "history": (
        "Rounds 1-3 graded detectors and oracles that have since been replaced. The old "
        "oracle labelled 'descriptions that were later edited', which measures doc-editing "
        "behaviour rather than what this system decides -- in 9 of dbt_shopify's 10 "
        "identifier-change positives the referenced token was never a column of that model "
        "at either end of the window. The current oracle labels a column that left the "
        "model's SQL whose description outlived it, which git records without anyone "
        "judging intent. Sources touched under any earlier round are excluded above."
    ),
    "round_5_scope": (
        "Round 5 widened coverage and fixed a rule; it does not re-bless anything. Two "
        "changes to what is frozen: mine_drift_labels.py is now included, because both the "
        "round-4 miner and scorer imported it while it sat outside the hashes, and "
        "select_holdout.py is included, because it decides which source gets graded. Two "
        "additions reflect the scoring move to run_orphan_bench_datahub.py, which replays "
        "into DataHub and reads back through the adapter -- the round-4 scorer handed the "
        "detector the labelled column, the labelled description and the after-schema, "
        "which is its own decision rule restated, and could not have returned anything "
        "else. detectors.py changed too: a lookalike column in the current schema no "
        "longer asserts a rename on its own, because resemblance is not evidence the "
        "token was ever a field here; the change log has to record the departure first. "
        "The TLC replay is 41/41 before and after that change. NOTHING here restores "
        "blindness: dbt_iterable was a blind holdout for the round-4 harness, and the "
        "harness that scores it now was written after its result was known. What supports "
        "the current numbers is the mutation (--mutate-skip-rewrite scores 0/2), not the "
        "order of operations."
    ),
    "round_6_scope": (
        "One graded file changed: run_orphan_bench_datahub.py. Its report generator "
        "emitted two literals it had never measured -- a '0/2' mutation row and the "
        "sentence 'the old harness returns the same 2/2'. The first is impossible on a "
        "corpus with four positives, and the second describes an argument the old "
        "harness silently ignores, since it has no such flag. A submission whose case "
        "is that its numbers are measured cannot ship a constant inside a generated "
        "report. Each report now states only the run that produced it. Scores are "
        "unchanged, because the change is to what gets written down, not to what gets "
        "counted; the other eight hashes are byte-identical."
    ),
}


def file_hash(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def build() -> dict:
    return {
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_head(),
        "files": {rel: file_hash(rel) for rel in FROZEN_FILES},
        "selection_rule": SELECTION_RULE,
        "note": (
            "The NYC TLC replay is a development benchmark and is NOT covered by this "
            "freeze -- that data shaped this detector. See docs/VALIDATION-INTEGRITY.md."
        ),
    }


def check() -> int:
    if not FREEZE_FILE.exists():
        print("no freeze.json -- nothing frozen yet")
        return 1
    frozen = json.loads(FREEZE_FILE.read_text())
    drift = [
        (rel, expected, file_hash(rel))
        for rel, expected in frozen["files"].items()
        if file_hash(rel) != expected
    ]
    if drift:
        print(f"FREEZE BROKEN: {len(drift)} file(s) changed since {frozen['frozen_at']}")
        for rel, exp, got in drift:
            print(f"  {rel}\n    frozen {exp[:16]}\n    now    {got[:16]}")
        return 1
    print(f"freeze intact: {len(frozen['files'])} files unchanged since {frozen['frozen_at']}")
    print(f"  git commit at freeze: {frozen['git_commit']}")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    FREEZE_FILE.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"-> {FREEZE_FILE}")
    for rel, h in build()["files"].items():
        print(f"  {h[:16]}  {rel}")
