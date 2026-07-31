#!/usr/bin/env python3
"""Continue the frozen v1 selection walk past the repository it already scored.

The rule is not re-opened here. bench/freeze.json still holds it, bench/
select_holdout.py still implements it, and both stay untouched -- the frozen
nine remain frozen. The only change is one more name in the "already seen"
set: dbt_iterable, because it was selected by the v1 walk and scored, and a
source that has been scored cannot grade the same system twice.

This file and the declaration in bench/HOLDOUT-v2-DECLARATION.md are committed
before the walk is run. That ordering is the whole point: the alphabet decides
which repository is next, not the person reading the results.

Usage:
  python3 bench/select_holdout_v2.py <workdir>
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))

# The v1 module is frozen. Import it rather than restate its thresholds, so the
# two walks cannot drift apart.
import select_holdout as v1  # noqa: E402

ALREADY_SCORED = {"dbt_iterable"}


def candidates() -> list[dict]:
    return [r for r in v1.candidates() if r["name"] not in ALREADY_SCORED]


def main() -> None:
    workdir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/holdout-search-v2")
    workdir.mkdir(parents=True, exist_ok=True)

    print(f"rule frozen at {v1.FREEZE['frozen_at']} (commit {v1.FREEZE['git_commit'][:12]})")
    print(f"order: {v1.RULE['order']}; take: {v1.RULE['take']}")
    print(f"additionally excluded (scored by the v1 walk): {sorted(ALREADY_SCORED)}\n")

    for r in candidates():
        name = r["name"]
        lic = (r.get("license") or {}).get("spdx_id") or "none"
        if lic not in v1.OK_LICENCES:
            print(f"  skip {name:34s} licence {lic}")
            continue

        dest = workdir / name
        if not dest.exists():
            subprocess.run(
                ["git", "clone", "--quiet", r["clone_url"], str(dest)],
                check=True, capture_output=True,
            )

        ok, why, stats = v1.evaluate(dest)
        if not ok:
            print(f"  skip {name:34s} {why}")
            continue

        print(f"\nselected: {name}")
        print(json.dumps(stats, indent=2))
        (ROOT / "bench" / "holdout-selection-v2.json").write_text(
            json.dumps({"repository": name, "clone_url": r["clone_url"], **stats}, indent=2) + "\n"
        )
        return

    print("\nno repository satisfied the rule")
    sys.exit(1)


if __name__ == "__main__":
    main()
