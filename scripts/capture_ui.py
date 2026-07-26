#!/usr/bin/env python3
"""Screenshot a DataHub entity page, so the write-back can be checked by eye.

The claim this supports is the one that matters for tool binding: what StillTrue
writes is not a file in this repo, it is content on the DataHub page a data
consumer already reads. That is only checkable by looking at the page, so this
takes the picture -- and takes it by script, from the URN, so anyone can rerun
it against their own DataHub and get the same frame.

Usage:
  python3 scripts/capture_ui.py <urn> <out.png> [--tab Documentation]
                                [--search airport] [--full]
                                [--frontend http://localhost:9002]
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

USER, PASSWORD = "datahub", "datahub"


def capture(urn: str, out: Path, frontend: str, tab: str, full: bool, search: str) -> None:
    url = f"{frontend}/dataset/{urllib.parse.quote(urn, safe='')}"
    if tab:
        url += f"/{tab}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(f"{frontend}/login", wait_until="networkidle")
        page.fill("#username", USER)
        page.fill("#password", PASSWORD)
        page.get_by_role("button", name="Login", exact=True).click()
        page.wait_for_url(lambda u: "/login" not in u, timeout=30_000)

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(4000)          # the entity page fetches its aspects after load

        # DataHub greets a fresh profile with a product tour that sits on top of
        # the documentation panel -- the one thing this screenshot is for.
        tour_close = page.locator(".reactour__close")
        if tour_close.count():
            tour_close.first.click()
            page.wait_for_timeout(1000)

        if search:
            # The column list scrolls inside its own container, so a full-page
            # shot still cuts it off. Filtering is how a person would find the
            # column anyway.
            page.get_by_placeholder("Search").first.fill(search)
            page.wait_for_timeout(1500)

        out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out), full_page=full)
        browser.close()

    print(f"{urn}\n  -> {out}")


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    def opt(name: str, default: str) -> str:
        return args[args.index(name) + 1] if name in args else default

    capture(
        urn=args[0],
        out=Path(args[1]),
        frontend=opt("--frontend", "http://localhost:9002"),
        tab=opt("--tab", "Documentation"),
        full="--full" in args,
        search=opt("--search", ""),
    )


if __name__ == "__main__":
    main()
