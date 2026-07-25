#!/usr/bin/env python3
"""
Third-party drift-label miner -- extracts natural "documentation drift" labels from a public dbt project's git history.

Principle: the drift is not planted by us, and the labels are not annotated by us.
  Event A (c1): a commit changes the model's SQL columns but not the matching column description in the yml
  Event B (c2): a later commit finally fixes that description
  → between c1..c2 the description is in a drift state; the category is determined mechanically from the diff shape

Only the state at c1 is fed to the system under test (description from c1's yml, schema from c1's SQL);
the system never sees git -- git is only where the oracle comes from.

Usage:
  python3 mine_drift_labels.py <repo_path> [--out drift-labels.jsonl] [--report]
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    ).stdout


def commits_touching(repo: Path, pattern: str) -> list[str]:
    """Return commits touching the given path pattern (oldest → newest)."""
    out = git(repo, "log", "--reverse", "--format=%H", "--", pattern)
    return [c for c in out.splitlines() if c]


def yml_columns_at(repo: Path, commit: str, path: str) -> dict[tuple[str, str], str]:
    """Get (model, column) → description from a given yml at a given commit."""
    blob = git(repo, "show", f"{commit}:{path}")
    if not blob.strip():
        return {}
    try:
        doc = yaml.safe_load(blob)
    except yaml.YAMLError:
        return {}
    if not isinstance(doc, dict):
        return {}
    result: dict[tuple[str, str], str] = {}
    for model in doc.get("models") or []:
        if not isinstance(model, dict):
            continue
        mname = model.get("name")
        if not mname:
            continue
        for col in model.get("columns") or []:
            if isinstance(col, dict) and col.get("name"):
                result[(mname, col["name"])] = (col.get("description") or "").strip()
    return result


def sql_columns_at(repo: Path, commit: str, model: str) -> set[str]:
    """Roughly extract the selected column aliases from the model's SQL. Used to classify rename/add/remove."""
    files = [f for f in git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
             if f.endswith(f"/{model}.sql") or f == f"models/{model}.sql"]
    if not files:
        return set()
    sql = git(repo, "show", f"{commit}:{files[0]}")
    # dbt staging model convention: `col as alias` or bare column names
    aliases = set(re.findall(r"\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, flags=re.I))
    bare = set(re.findall(r"^\s{4,}([a-z_][a-z0-9_]*)\s*,\s*$", sql, flags=re.M))
    return {a.lower() for a in aliases | bare}


def _normalize(text: str) -> str:
    """Erase differences that don't change meaning: case, punctuation, whitespace, non-ASCII noise."""
    t = re.sub(r"[^\x00-\x7f]", "", text.lower())
    t = re.sub(r"[^a-z0-9`_]+", " ", t)
    return " ".join(t.split())


def _identifiers(text: str) -> set[str]:
    """Backtick-quoted identifiers -- the field/table names the description refers to."""
    return {m.lower() for m in re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", text)}


def classify(before: str, after: str) -> str | None:
    """Return the drift category; None when judged non-drift (pure typo/formatting)."""
    nb, na = _normalize(before), _normalize(after)
    if nb == na:
        return None  # differs only in punctuation, case, or encoding noise
    import difflib
    ratio = difflib.SequenceMatcher(None, nb, na).ratio()
    ids_b, ids_a = _identifiers(before), _identifiers(after)

    if "deprecat" in na and "deprecat" not in nb:
        return "DEPRECATION"
    if ids_b != ids_a:
        return "IDENTIFIER_CHANGE"
    if nb and nb in na and len(na) - len(nb) < 40:
        # the old description survives intact with only a small addition (typical: batch-adding "in shop currency")
        # that's making an incomplete description precise, not docs diverging from reality -- not counted as drift
        return None
    if re.search(r"\b(source|derived from|upstream|joined)\b", na + nb):
        return "LINEAGE"
    if ratio > 0.95 and len(na) - len(nb) < 15:
        return None  # highly similar with no substantial addition -- treated as copy-editing
    return "SEMANTIC"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    repo = Path(sys.argv[1])
    out_path = Path("drift-labels.jsonl")
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])

    yml_files = [f for f in git(repo, "ls-files", "models").splitlines() if f.endswith(".yml")]
    print(f"{len(yml_files)} yml files")

    # (model, column) → [(commit, description), ...] in chronological order
    history: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for path in yml_files:
        commits = commits_touching(repo, path)
        print(f"  {path}: {len(commits)} commits", flush=True)
        prev: dict[tuple[str, str], str] = {}
        for c in commits:
            cur = yml_columns_at(repo, c, path)
            for key, desc in cur.items():
                if key not in prev or prev[key] != desc:
                    history[key].append((c, desc))
            prev = cur

    positives, negatives, rejected = [], [], 0
    for (model, column), seq in history.items():
        if len(seq) >= 2:
            # the description was edited → every edit is a "human fixing the docs" event; the previous state is the drift endpoint
            for i in range(1, len(seq)):
                c1, desc_before = seq[i - 1]
                c2, desc_after = seq[i]
                if not desc_before or desc_before == desc_after:
                    continue
                category = classify(desc_before, desc_after)
                if category is None:
                    rejected += 1  # pure typo or copy-editing, not drift
                    continue
                positives.append({
                    "model": model, "column": column,
                    "c1": c1, "c2": c2,
                    "description_at_c1": desc_before,
                    "description_at_c2": desc_after,
                    "category": category,
                    "label": "drift",
                })
        elif len(seq) == 1 and seq[0][1]:
            negatives.append({
                "model": model, "column": column,
                "commit": seq[0][0], "description": seq[0][1],
                "label": "stable",
            })

    with out_path.open("w") as f:
        for row in positives + negatives:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    from collections import Counter
    by_cat = Counter(p["category"] for p in positives)

    print(f"\nPositives (real drift): {len(positives)}")
    for cat, n in by_cat.most_common():
        print(f"    {cat}: {n}")
    print(f"Filtered out (pure typos/copy-editing): {rejected}")
    print(f"Negatives (description never changed): {len(negatives)}")
    print(f"→ {out_path}")
    print("\nSPEC threshold: positives >= 30, negatives >= 100 →",
          "pass" if len(positives) >= 30 and len(negatives) >= 100 else "fail, pick another candidate repo")


if __name__ == "__main__":
    main()
