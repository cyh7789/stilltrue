#!/usr/bin/env python3
"""Compare two screenshots pixel by pixel and say where they differ.

Written for one claim: that resolving an orphaned description changes nothing a
reader sees. Showing the same image file twice does not establish that -- it
establishes that a file was reused. Two independent captures and a count do.

Usage: python3 scripts/diff_frames.py before.png after.png
"""
from __future__ import annotations

import sys

from PIL import Image


def main() -> None:
    a = Image.open(sys.argv[1]).convert("RGB")
    b = Image.open(sys.argv[2]).convert("RGB")
    if a.size != b.size:
        print(f"  different sizes: {a.size} vs {b.size}")
        sys.exit(1)

    w, h = a.size
    pa, pb = a.load(), b.load()
    boxes: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if pa[x, y] != pb[x, y]:
                boxes.append((x, y))

    print(f"  {w}x{h}, {w * h} pixels")
    print(f"  differing pixels: {len(boxes)}  ({len(boxes) / (w * h) * 100:.4f}%)")
    if not boxes:
        print("  IDENTICAL")
        return
    xs = [x for x, _ in boxes]
    ys = [y for _, y in boxes]
    print(f"  all differences inside x {min(xs)}-{max(xs)}, y {min(ys)}-{max(ys)}")


if __name__ == "__main__":
    main()
