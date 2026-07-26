#!/usr/bin/env python3
"""Mine a dbt repo for documentation left behind by a schema change.

The label this produces is the thing the detector actually decides: a column that
the model's SQL stopped producing, whose description is still sitting in the yml
afterwards. Nobody has to judge intent -- the column is either in the SQL or it
is not, and the description is either still there or it is not.

Why not the previous oracle. That one paired commits: one that changed a model's
SQL without touching its description, and a later one where a human fixed the
wording. It labelled "descriptions that were eventually edited", which is a much
broader thing. Checking dbt_shopify's ten identifier-change positives against the
model's own columns showed nine referenced tokens that were never columns of that
model at either end of the window -- they were enumerated values like
`fixed_amount` and upstream model names. A detector could only "catch" those by
firing on prose, and a label-based oracle credits that as a hit.

Positives here: (model, column) where the column left the SQL at some commit and
its yml description outlived it.
Negatives: (model, column) present in both the SQL and the yml at the same
commit -- documentation that is correct and must not be flagged.

Usage:
  python3 bench/oracles/mine_orphaned_docs.py <repo> [--out labels.jsonl]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mine_drift_labels import sql_columns_at, yml_columns_at  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout


def yml_files(repo: Path) -> list[str]:
    out = git(repo, "ls-files", "models/**/*.yml", "models/*.yml").split()
    return [p for p in out if p.endswith(".yml")]


def mine(repo: Path, max_commits: int = 400) -> tuple[list[dict], list[dict]]:
    positives: list[dict] = []
    negatives: list[dict] = []

    # Every lookup shells out to `git show`, and the same (commit, model) pair
    # recurs across yml files and commit windows. Without this the walk is
    # dominated by process spawns.
    sql_cache: dict[tuple[str, str], frozenset] = {}
    yml_cache: dict[tuple[str, str], dict] = {}

    def sql_at(commit: str, model: str) -> frozenset:
        key = (commit, model)
        if key not in sql_cache:
            sql_cache[key] = frozenset(sql_columns_at(repo, commit, model) or ())
        return sql_cache[key]

    def yml_at(commit: str, path: str) -> dict:
        key = (commit, path)
        if key not in yml_cache:
            yml_cache[key] = yml_columns_at(repo, commit, path)
        return yml_cache[key]

    for path in yml_files(repo):
        commits = git(repo, "log", "--format=%H", f"-{max_commits}", "--", path).split()
        commits.reverse()                      # oldest first
        if len(commits) < 2:
            continue

        for older, newer in zip(commits, commits[1:]):
            documented_before = yml_at(older, path)
            documented_after = yml_at(newer, path)

            for (model, column), description in documented_after.items():
                if (model, column) not in documented_before:
                    continue                    # newly documented, nothing to outlive
                before = sql_at(older, model)
                after = sql_at(newer, model)
                if not before or not after:
                    continue                    # SQL not reconstructable at one end
                if column in before and column not in after:
                    positives.append({
                        "model": model, "column": column,
                        "c1": older, "c2": newer,
                        "description": description,
                        "label": "orphaned",
                        "why": "column left the SQL; its description stayed in the yml",
                    })
                elif column in before and column in after:
                    negatives.append({
                        "model": model, "column": column,
                        "commit": newer, "description": description,
                        "label": "current",
                    })
    return positives, negatives


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    repo = Path(sys.argv[1])
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("orphaned.jsonl")

    positives, negatives = mine(repo)
    # One row per (model, column): a column can be dropped once but appear in
    # many commit pairs as still-documented, which would inflate the negatives.
    seen: set[tuple[str, str]] = set()
    rows = []
    for r in positives + negatives:
        key = (r["model"], r["column"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)

    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    pos = [r for r in rows if r["label"] == "orphaned"]
    print(f"repo: {repo.name}")
    print(f"  orphaned documentation (positives): {len(pos)}")
    print(f"  documentation matching the SQL (negatives): {len(rows) - len(pos)}")
    for r in pos[:5]:
        print(f"    {r['model']}.{r['column']}: {r['description'][:70]}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
