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
    "src/stilltrue/detectors.py",          # the rules themselves
    "src/stilltrue/adapter.py",            # which text gets judged, and the change-log read
    "src/stilltrue/evidence.py",           # what counts as a citation
    "bench/oracles/replay_tlc.py",         # how a replay is scored
    "bench/oracles/mine_orphaned_docs.py", # what counts as orphaned documentation
    "bench/run_orphan_bench.py",           # how orphan labels are scored
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
    "round": 4,
    "history": (
        "Rounds 1-3 graded detectors and oracles that have since been replaced. The old "
        "oracle labelled 'descriptions that were later edited', which measures doc-editing "
        "behaviour rather than what this system decides -- in 9 of dbt_shopify's 10 "
        "identifier-change positives the referenced token was never a column of that model "
        "at either end of the window. The current oracle labels a column that left the "
        "model's SQL whose description outlived it, which git records without anyone "
        "judging intent. Sources touched under any earlier round are excluded above."
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
