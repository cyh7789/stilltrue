#!/usr/bin/env python3
"""Screenshot the upstream pull requests, so shot 10 is not a live browser take.

The four patches are the part of this project that lives in someone else's
repository, which makes them the one piece of evidence a viewer cannot check by
cloning ours. Capturing them by script from the PR numbers means the frames are
reproducible and the state they show is dated.

Public pages, no login. Usage:
  python3 scripts/capture_prs.py [--out docs/evidence/prs]
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PRS = [
    ("datahub-project/datahub", 18622, "dataset-level description resolution"),
    ("datahub-project/datahub", 18628, "field-level editable descriptions are dropped"),
    ("datahub-project/datahub", 18630, "list_schema_fields crashes with no schema aspect"),
    ("datahub-project/datahub-skills", 49, "the context-drift skill"),
]


def main() -> None:
    args = sys.argv[1:]
    if "--out" in args and args.index("--out") + 1 >= len(args):
        print("  --out needs a directory")
        sys.exit(2)
    unknown = [a for a in args if a.startswith("-") and a != "--out"]
    if unknown:
        print(f"  unknown option: {unknown[0]}")
        sys.exit(2)
    out = Path(args[args.index("--out") + 1] if "--out" in args else "docs/evidence/prs")
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for repo, number, what in PRS:
            page.goto(f"https://github.com/{repo}/pull/{number}", wait_until="networkidle")
            page.wait_for_timeout(2500)
            # The title, state pill and the diffstat are what the shot needs;
            # the comment thread below is noise at this size.
            path = out / f"pr-{number}.png"
            page.screenshot(path=str(path))
            state = page.locator('[class*="State"]').first
            label = state.inner_text().strip() if state.count() else "?"
            print(f"  #{number:<6} {label:<8} {what}\n           -> {path}")
        browser.close()


if __name__ == "__main__":
    main()
