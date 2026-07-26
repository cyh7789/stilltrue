#!/usr/bin/env python3
"""Render scripts/title_card.html to a PNG at video resolution.

Shot 11 needs a source file like every other shot. Making the closing frame in
an editor would leave one frame of the video that nothing in the repo produces.

Usage: python3 scripts/capture_card.py [out.png]
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "docs/evidence/07-title-card.png"


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((HERE / "title_card.html").as_uri(), wait_until="networkidle")
        page.wait_for_timeout(400)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUT))
        browser.close()
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
