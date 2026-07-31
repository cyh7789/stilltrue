#!/usr/bin/env python3
"""Break the full-catalog scan down by the platform each dataset lives on.

The headline number for that scan is "11 drifted, 12 still true, 58 declined
over 81 checks", and a reader can reasonably assume dbt produced all of it,
because the two holdouts are dbt packages. It did not. This reads the committed
run and prints where each verdict actually came from.

No new scan: the input is runs/4041b76520f1/findings.jsonl, the same file the
77-dataset figures come from.

Regenerate: python3 scripts/platform_breakdown.py
"""
import collections
import json
import re
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent.parent / "runs" / "4041b76520f1" / "findings.jsonl"
COLS = ["DRIFT", "CURRENT", "INSUFFICIENT_EVIDENCE"]


def main() -> None:
    if not RUN.exists():
        sys.exit(f"missing {RUN}")
    rows = [json.loads(l) for l in RUN.read_text().splitlines() if l.strip()]

    per = collections.defaultdict(collections.Counter)
    seen = collections.defaultdict(set)
    for r in rows:
        m = re.search(r"dataPlatform:([a-z0-9_-]+)", r["entity_urn"])
        p = m.group(1) if m else "unknown"
        per[p][r["verdict"]] += 1
        seen[p].add(r["entity_urn"])

    order = sorted(per, key=lambda k: (-per[k]["DRIFT"], -sum(per[k].values()), k))
    print("| platform | datasets with prose to check | drift | still true | declined |")
    print("|---|---|---|---|---|")
    tot = collections.Counter()
    for p in order:
        c = per[p]
        print(f"| `{p}` | {len(seen[p])} | {c['DRIFT']} | {c['CURRENT']} | {c['INSUFFICIENT_EVIDENCE']} |")
        tot.update(c)
    print(f"| **total** | **{sum(len(v) for v in seen.values())}** | "
          f"**{tot['DRIFT']}** | **{tot['CURRENT']}** | **{tot['INSUFFICIENT_EVIDENCE']}** |")
    print()
    print(f"{sum(tot[c] for c in COLS)} checks, {len(per)} platforms, "
          f"{tot['DRIFT']} drift verdicts of which dbt produced {per.get('dbt', {}).get('DRIFT', 0)}.")


if __name__ == "__main__":
    main()
