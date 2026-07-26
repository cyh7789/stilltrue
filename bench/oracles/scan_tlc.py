#!/usr/bin/env python3
"""Derive the TLC drift labels by diffing consecutive published parquet schemas.

Nobody labels anything here: a column is in one month's file and not the next,
or it is not. The output feeds `replay_tlc.py`, which scores the detector
against these events.

Two things this must not do, both of which it used to. It must not treat an
unreachable month as a gap and then diff across it -- that invents an event
where two real months were simply not compared. And it must not read the CDN's
403 as "the TLC never published this": the same code covers a rate limit and a
missing object, so `is_published` separates them with a sentinel month.

Usage:
  python3 bench/oracles/scan_tlc.py [--start 2023-01] [--out tlc-drift-events.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_tlc_benchmark import remote_schema  # noqa: E402

HERE = Path(__file__).resolve().parent


def months_from(start: str, count: int = 60) -> list[str]:
    y, m = int(start[:4]), int(start[5:7])
    out = []
    for _ in range(count):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def main() -> None:
    def opt(name: str, default: str) -> str:
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

    start = opt("--start", "2023-01")
    out_path = HERE / opt("--out", "tlc-drift-events.json")

    rows, prev, prev_month, published = [], None, None, []
    for month in months_from(start):
        try:
            names = [n for n, _ in remote_schema(month)]
        except FileNotFoundError:
            break                      # publication runs out; nothing beyond this
        published.append(month)

        if prev is not None:
            added = [n for n in names if n not in prev]
            removed = [n for n in prev if n not in names]
            renamed = [(r, a) for r in removed for a in added if r.lower() == a.lower()]
            if added or removed:
                rows.append({"month": month, "prev_month": prev_month,
                             "added": added, "removed": removed,
                             "case_rename": [f"{r}->{a}" for r, a in renamed]})
                print(f"{month}: +{added} -{removed} "
                      f"case_rename={[f'{r}->{a}' for r, a in renamed]}")
        prev, prev_month = names, month

    print(f"\npublished months: {len(published)} ({published[0]} -> {published[-1]})")
    print(f"drift events: {len(rows)}")
    out_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
