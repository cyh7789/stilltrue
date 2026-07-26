#!/usr/bin/env python3
"""Replay 35 months of published NYC TLC schemas and score the detector month by month.

The setup is the real-world one. A description is written once, against the
schema as it stood in 2023-01, and never revised. The pipeline keeps ingesting:
every month's actual published parquet schema goes into DataHub in order. Nobody
goes back to update the docs.

Two things happened in those 35 months, and neither was announced:

  2023-02  airport_fee was renamed to Airport_fee
  2025-01  cbd_congestion_fee appeared

Both fall out of the published schemas -- `scan_tlc.py` derives them from the
parquet files themselves, so the labels are not ours.

What this scores is harder than a static snapshot: the detector must speak up in
the two months something changed and stay quiet in the other 33. A tool that
fires every month is useless however good its recall.

Usage:
  python3 bench/oracles/replay_tlc.py [--server URL] [--months N]
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_tlc_benchmark import COLUMN_DOCS, DESCRIPTION, remote_schema  # noqa: E402

from stilltrue.adapter import ReadOnlyDataHubAdapter, authored_description  # noqa: E402
from stilltrue.detectors import detect_schema_break, vanished_fields  # noqa: E402

NAME = "tlc_replay.yellow_tripdata"
URN = f"urn:li:dataset:(urn:li:dataPlatform:s3,{NAME},PROD)"
EVENTS = json.loads((Path(__file__).resolve().parent / "tlc-drift-events.json").read_text())
DRIFT_MONTHS = {e["month"] for e in EVENTS}


def expected_state(month: str) -> set[str]:
    """Which identifiers the description should be flagged for, as of this month.

    Drift is a state, not an event. `airport_fee` was renamed in 2023-02 and the
    description was never corrected, so it is wrong in 2023-02 and every month
    after -- reporting it once and then falling silent would be the failure.
    Scoring the asserted set against this exactly is a harder test than counting
    events: the detector has to be right 35 times, not twice.
    """
    referenced = set(re_ids(DESCRIPTION))
    gone: set[str] = set()
    for e in EVENTS:
        if e["month"] <= month:
            gone |= set(e["removed"])
    return gone & referenced


def re_ids(text: str) -> set[str]:
    from stilltrue.detectors import identifier_mentions
    return {m.value for m in identifier_mentions(text) if m.kind == "identifier"}


def months(start: str = "2023-01", count: int = 35) -> list[str]:
    y, m = int(start[:4]), int(start[5:7])
    out = []
    for _ in range(count):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def ingest(month: str, server: str, with_docs: bool) -> None:
    from datahub.sdk import DataHubClient, Dataset

    client = DataHubClient(server=server, token=None)
    cols = remote_schema(month)
    ds = Dataset(platform="s3", name=NAME, env="PROD",
                 schema=[(n, t) for n, t in cols], description=DESCRIPTION)
    if with_docs:
        # Column documentation is written once, in the first month, exactly as
        # the TLC data dictionary described the 2023-01 schema. Never revised.
        for n, _ in cols:
            if n in COLUMN_DOCS:
                ds[n].set_description(COLUMN_DOCS[n])
    client.entities.upsert(ds)


def scan(server: str) -> list:
    with ReadOnlyDataHubAdapter(server=server) as adapter:
        entity, ev_e = adapter.get_entity(URN)
        schema, ev_s = adapter.list_schema_fields(URN)
        fields = schema.get("fields", [])
        events, ev_t = adapter.schema_changes(URN)
        gone = vanished_fields(events, {f.get("fieldPath", "") for f in fields})
        return detect_schema_break(URN, authored_description(entity), fields,
                                   [ev_e, ev_s, ev_t], vanished=gone)


def main() -> None:
    server = sys.argv[sys.argv.index("--server") + 1] if "--server" in sys.argv else "http://localhost:8080"
    count = int(sys.argv[sys.argv.index("--months") + 1]) if "--months" in sys.argv else 35

    rows, missing = [], []
    for i, month in enumerate(months(count=count)):
        try:
            ingest(month, server, with_docs=(i == 0))
        except FileNotFoundError:
            missing.append(month)
            continue
        time.sleep(2)                       # let the diff settle
        found = scan(server)
        drift = [f for f in found if f.verdict == "DRIFT" and f.category == "D1_SCHEMA_BREAK"]
        asserted = {f.subject for f in drift}
        expected = expected_state(month)
        rows.append({
            "month": month,
            "expected": sorted(expected),
            "asserted": sorted(asserted),
            "correct": asserted == expected,
            "event_month": month in DRIFT_MONTHS,
            "reality": [f.reality for f in drift],
        })
        mark = "OK " if asserted == expected else "!! "
        flag = "*" if month in DRIFT_MONTHS else " "
        print(f"{mark}{flag} {month}  expected {sorted(expected) or '-'}  asserted {sorted(asserted) or '-'}")

    out = ROOT / "bench" / "tlc-replay-results.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    correct = [r for r in rows if r["correct"]]
    wrong = [r for r in rows if not r["correct"]]
    onset = [r for r in rows if r["event_month"]]
    clean = [r for r in rows if not r["expected"]]

    print(f"\nmonths replayed:          {len(rows)}" + (f"  (not yet published: {missing})" if missing else ""))
    print(f"months scored exactly right: {len(correct)}/{len(rows)}")
    print(f"  of which nothing to report: {len([r for r in clean if r['correct']])}/{len(clean)}")
    print(f"drift detected in the month it happened: "
          f"{len([r for r in onset if r['correct']])}/{len(onset)}")
    if wrong:
        print("  wrong months:")
        for r in wrong:
            print(f"    {r['month']}: expected {r['expected']} asserted {r['asserted']}")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
