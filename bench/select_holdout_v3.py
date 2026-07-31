#!/usr/bin/env python3
"""Walk the v3 population, declared in bench/HOLDOUT-v3-DECLARATION.md.

The v1 module is frozen. Its `evaluate` holds the six thresholds and its
`OK_LICENCES` the licence set, so both are imported rather than restated: the
only thing this file changes is which repositories get offered to them.

Usage:
  python3 bench/select_holdout_v3.py <workdir>
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))

import select_holdout as v1  # noqa: E402

# Fixed in the declaration before any of them was cloned.
ORGS = ["brooklyn-data", "calogica", "dbt-labs", "elementary-data",
        "infinitelambda", "montreal-analytics"]


def candidates() -> list[dict]:
    out = []
    for org in ORGS:
        for page in range(1, 4):
            req = urllib.request.Request(
                f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}&type=public")
            req.add_header("Accept", "application/vnd.github+json")
            batch = json.load(urllib.request.urlopen(req))
            if not batch:
                break
            out += [r for r in batch
                    if "dbt" in r["name"].lower() and not r.get("archived")]
    out.sort(key=lambda r: (r["owner"]["login"].lower(), r["name"].lower()))
    return out


def main() -> None:
    workdir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/holdout-v3-search")
    workdir.mkdir(parents=True, exist_ok=True)

    cands = candidates()
    print(f"population: {len(cands)} repositories across {len(ORGS)} organisations")
    print("thresholds imported from the frozen bench/select_holdout.py\n")

    for r in cands:
        full = f"{r['owner']['login']}/{r['name']}"
        lic = (r.get("license") or {}).get("spdx_id") or "none"
        if lic not in v1.OK_LICENCES:
            print(f"  skip {full:44s} licence {lic}")
            continue

        dest = workdir / f"{r['owner']['login']}__{r['name']}"
        if not dest.exists():
            subprocess.run(["git", "clone", "--quiet", r["clone_url"], str(dest)], check=True)

        ok, why, stats = v1.evaluate(dest)
        if not ok:
            print(f"  skip {full:44s} {why}")
            continue

        print(f"\nSELECTED: {full}")
        print(f"  licence {lic} | commits {stats['commits']} | history {stats['months']}mo "
              f"| descriptions {stats['descriptions']}")
        print(f"  positives {stats['positives']} | negatives {stats['negatives']}")
        print(f"  clone: {dest}")
        (ROOT / "bench" / "holdout-v3-selection.json").write_text(
            json.dumps({"selected": full, "url": r["html_url"], "licence": lic, **stats,
                        "frozen_rule_commit": v1.FREEZE["git_commit"]}, indent=2) + "\n")
        return

    print("\nno candidate satisfied the frozen thresholds")
    sys.exit(1)


if __name__ == "__main__":
    main()
