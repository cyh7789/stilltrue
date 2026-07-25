#!/usr/bin/env python3
"""
第三方 holdout 挖掘器 — 從公開 dbt 專案的 git 歷史抽出「文件漂移」的自然標籤。

原理：drift 不是我們植入的，標籤也不是我們標的。
  事件 A（c1）：commit 改了 model 的 SQL 欄位，但沒改 yml 裡對應的欄位描述
  事件 B（c2）：之後某個 commit 才補上那段描述
  → c1..c2 之間，該描述處於 drift 狀態，類別由 diff 型態機械判定

送進受測系統時只搬 c1 時點的狀態（描述取 c1 的 yml，schema 取 c1 的 SQL），
系統看不到 git —— git 只是 oracle 的產地。

用法：
  python3 mine_holdout.py <repo_path> [--out holdout.jsonl] [--report]
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
    """回傳影響指定路徑樣式的 commit（舊→新）。"""
    out = git(repo, "log", "--reverse", "--format=%H", "--", pattern)
    return [c for c in out.splitlines() if c]


def yml_columns_at(repo: Path, commit: str, path: str) -> dict[tuple[str, str], str]:
    """取某 commit 的某個 yml 裡 (model, column) → description。"""
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
    """從 model 的 SQL 粗抽 select 出來的欄位別名。用於判定改名/新增/移除。"""
    files = [f for f in git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
             if f.endswith(f"/{model}.sql") or f == f"models/{model}.sql"]
    if not files:
        return set()
    sql = git(repo, "show", f"{commit}:{files[0]}")
    # dbt 的 staging model 慣例：`col as alias` 或直接列欄位名
    aliases = set(re.findall(r"\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, flags=re.I))
    bare = set(re.findall(r"^\s{4,}([a-z_][a-z0-9_]*)\s*,\s*$", sql, flags=re.M))
    return {a.lower() for a in aliases | bare}


def _normalize(text: str) -> str:
    """抹掉不改變語意的差異：大小寫、標點、空白、非 ASCII 雜訊。"""
    t = re.sub(r"[^\x00-\x7f]", "", text.lower())
    t = re.sub(r"[^a-z0-9`_]+", " ", t)
    return " ".join(t.split())


def _identifiers(text: str) -> set[str]:
    """反引號包起來的識別碼 —— 描述裡指涉的欄位/表名。"""
    return {m.lower() for m in re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", text)}


def classify(before: str, after: str) -> str | None:
    """回傳漂移類別；判定為非漂移（純錯字/格式）時回 None。"""
    nb, na = _normalize(before), _normalize(after)
    if nb == na:
        return None  # 只差標點、大小寫或編碼雜訊
    import difflib
    ratio = difflib.SequenceMatcher(None, nb, na).ratio()
    ids_b, ids_a = _identifiers(before), _identifiers(after)

    if "deprecat" in na and "deprecat" not in nb:
        return "DEPRECATION"
    if ids_b != ids_a:
        return "IDENTIFIER_CHANGE"
    if nb and nb in na and len(na) - len(nb) < 40:
        # 舊描述整段保留、只多了一小段補充（典型：批次補上 "in shop currency"）
        # 這是把不完整的描述講精確，不是文件與現實脫節 —— 不計入漂移
        return None
    if re.search(r"\b(source|derived from|upstream|joined)\b", na + nb):
        return "LINEAGE"
    if ratio > 0.95 and len(na) - len(nb) < 15:
        return None  # 高度相似且沒有實質新增 —— 視為潤稿
    return "SEMANTIC"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    repo = Path(sys.argv[1])
    out_path = Path("holdout.jsonl")
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])

    yml_files = [f for f in git(repo, "ls-files", "models").splitlines() if f.endswith(".yml")]
    print(f"yml 檔 {len(yml_files)} 個")

    # (model, column) → [(commit, description), ...] 依時序
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
            # 描述被改過 → 每一次修改都是「人類補文件」的行為，前一個狀態即 drift 端點
            for i in range(1, len(seq)):
                c1, desc_before = seq[i - 1]
                c2, desc_after = seq[i]
                if not desc_before or desc_before == desc_after:
                    continue
                category = classify(desc_before, desc_after)
                if category is None:
                    rejected += 1  # 純錯字或潤稿，不是漂移
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

    print(f"\n正例（實質漂移）：{len(positives)}")
    for cat, n in by_cat.most_common():
        print(f"    {cat}: {n}")
    print(f"濾除（純錯字／潤稿）：{rejected}")
    print(f"負例（描述從未變動）：{len(negatives)}")
    print(f"→ {out_path}")
    print("\nSPEC 門檻：正例 >= 30、負例 >= 100 →",
          "通過" if len(positives) >= 30 and len(negatives) >= 100 else "不通過，換候選 repo")


if __name__ == "__main__":
    main()
