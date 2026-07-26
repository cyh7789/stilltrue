#!/usr/bin/env python3
"""Apply the frozen selection rule and stop at the first repository that passes.

The rule lives in bench/freeze.json and was committed before any candidate was
inspected. This script only executes it. Every rejection is printed with the
threshold it missed, so the walk down the alphabet is auditable -- a source that
was skipped can be checked against the reason given.

Usage:
  python3 bench/select_holdout.py <workdir>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))

FREEZE = json.loads((ROOT / "bench" / "freeze.json").read_text())
RULE = FREEZE["selection_rule"]
TH = RULE["thresholds"]
OK_LICENCES = {"Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause"}


def candidates() -> list[dict]:
    repos = []
    for page in range(1, 6):
        req = urllib.request.Request(
            f"https://api.github.com/orgs/fivetran/repos?per_page=100&page={page}&type=public"
        )
        req.add_header("Accept", "application/vnd.github+json")
        batch = json.load(urllib.request.urlopen(req))
        if not batch:
            break
        repos += batch
    # Excluded by name because the v1 walk mined them, so their contents were
    # seen. A source this code has looked at cannot grade it.
    seen = {"dbt_ad_reporting", "dbt_amplitude", "dbt_asana", "dbt_facebook_ads",
            "dbt_fivetran_log", "dbt_github", "dbt_google_ads", "dbt_greenhouse",
            "dbt_hubspot"}
    out = [
        r for r in repos
        if r["name"].startswith("dbt_")
        and not r["name"].startswith("dbt_shopify")
        and r["name"] not in seen
        and not r.get("archived")
    ]
    out.sort(key=lambda r: r["name"])
    return out


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout


def evaluate(repo: Path) -> tuple[bool, str, dict]:
    commits = int(git(repo, "rev-list", "--count", "HEAD").strip() or 0)
    if commits < 200:
        return False, f"commits {commits} < 200", {}

    first = git(repo, "log", "--reverse", "--format=%ad", "--date=format:%Y-%m").strip().split("\n")[0]
    last = git(repo, "log", "-1", "--format=%ad", "--date=format:%Y-%m").strip()
    months = (int(last[:4]) - int(first[:4])) * 12 + (int(last[5:7]) - int(first[5:7]))
    if months < 12:
        return False, f"history {months}mo < 12", {}

    # Column descriptions live in the models' yml files.
    descs = 0
    for y in list(repo.glob("models/**/*.yml")) + list(repo.glob("models/*.yml")):
        descs += len(re.findall(r"^\s*description:", y.read_text(encoding="utf-8", errors="ignore"), re.M))
    if descs < 50:
        return False, f"descriptions {descs} < 50", {}

    # The last two thresholds can only be answered by mining. The miner is a
    # frozen file, so it is invoked as a subprocess and runs exactly as frozen
    # rather than being refactored into something importable.
    out = ROOT / "bench" / "oracles" / f"drift-labels-{repo.name.replace('_', '-')}.jsonl"
    subprocess.run(
        [sys.executable, str(ROOT / "bench" / "oracles" / "mine_drift_labels.py"),
         str(repo), "--out", str(out)],
        capture_output=True, text=True, check=True,
    )
    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    pos = sum(1 for r in rows if r.get("label") == "drift")
    neg = sum(1 for r in rows if r.get("label") == "stable")
    if pos < 30:
        out.unlink(missing_ok=True)
        return False, f"mined positives {pos} < 30", {}
    if neg < 100:
        out.unlink(missing_ok=True)
        return False, f"mined negatives {neg} < 100", {}

    return True, "", {
        "commits": commits, "months": months, "descriptions": descs,
        "positives": pos, "negatives": neg, "labels_file": out.name,
    }


def main() -> None:
    workdir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/holdout-search")
    workdir.mkdir(parents=True, exist_ok=True)

    print(f"rule frozen at {FREEZE['frozen_at']} (commit {FREEZE['git_commit'][:12]})")
    print(f"order: {RULE['order']}; take: {RULE['take']}\n")

    for r in candidates():
        name = r["name"]
        lic = (r.get("license") or {}).get("spdx_id") or "none"
        if lic not in OK_LICENCES:
            print(f"  skip {name:34s} licence {lic}")
            continue

        dest = workdir / name
        if not dest.exists():
            subprocess.run(["git", "clone", "--quiet", r["clone_url"], str(dest)], check=True)

        ok, why, stats = evaluate(dest)
        if not ok:
            print(f"  skip {name:34s} {why}")
            continue

        print(f"\nSELECTED: {name}")
        print(f"  licence {lic} | commits {stats['commits']} | history {stats['months']}mo "
              f"| descriptions {stats['descriptions']}")
        print(f"  clone: {dest}")
        (ROOT / "bench" / "holdout-selection.json").write_text(
            json.dumps({
                "selected": name,
                "url": r["html_url"],
                "licence": lic,
                **stats,
                "frozen_rule_commit": FREEZE["git_commit"],
            }, indent=2) + "\n", encoding="utf-8")
        return

    print("no candidate satisfied the rule")
    sys.exit(1)


if __name__ == "__main__":
    main()
