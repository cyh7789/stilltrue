# 影片修正覆核

查核日期：2026-07-26（Asia/Taipei）

查核範圍：`git diff 8378707..HEAD`，共六筆提交：`b9a0ed8`、`656959b`、`bb5dac5`、`44a969a`、`cc9c2da`、`dbbd940`。

## 結論

**仍不宜直接開拍。** 原審查的多數問題確實修掉：Shot 1 與 Shot 3 已降到可朗讀速度；Shot 10、11 都有可執行的產生器與已提交 PNG；Shot 7 預設不再覆寫證據圖；Shot 9 的 normal／mutation 結果可由本輪獨立重現；`LICENSE` 與 Apache 官方原文逐位元組相同。

尚未收斂的原意見有三項旁白：Shot 2 仍把自動取得的 token 寫成與「reviewed text」相關，Shot 7 仍把證據支持的「standard dataset pages」擴大成所有 DataHub page，Shot 11 的「Every number … regenerates」則被 Shot 10 的動態 GitHub 數字推翻。這六筆提交另新增拍攝缺陷：Shot 9 文件中的 `python3` 命令在目前未啟用虛擬環境的 shell 直接失敗、Shot 10 的 `pr-49.png` 把兩句已判定不可說的舊主張帶回畫面、字數與腳本自述歷史不實、刪減段落自相矛盾，而且新 PEP 639 授權欄位與 `setuptools>=68` 的最低版本不相容。

## 一、十項旁白修正

逐項判定為七項成立、三項未成立。以下只核對原審查提出的十項，不重做整份旁白審查。

| 原 finding | 現行替代句 | 判定 | 證據 |
|---|---|---|---|
| S2 human confirmation | “wrote only against a hash of the reviewed text” | **未修好** | `scripts/demo.sh:26-32` 仍從 dry run 自動擷取 token，再由同一腳本提交，沒有人工停點或 review。`src/stilltrue/proposal.py:58-62` 又顯示 hash 涵蓋 URN、aspect、subject、before、after、verdict 與 evidence，不只是 text；`:108-114` 明說任何可執行 `apply` 的 caller 都能從 dry run 取得 token。新句刪掉 human，卻用沒有發生的 “reviewed” 取代。 |
| S3 perfect coverage | “finds the undocumented column and misses the rename” | **成立** | `bench/REPORT.md:23` 的 B1 是 1/2，Caught 為 `cbd_congestion_fee`、Missed 為 `airport_fee`；`:33-36` 明說它只找沒有 description 的欄位，present-but-wrong 的 rename 不可能被它發現。`docs/VIDEO-SCRIPT.md:93` 所引 `bench/REPORT.md:22` 差一行，正確是 `:23`。 |
| S8 written once | “The same description is re-ingested every month and never corrected” | **成立** | `bench/oracles/replay_tlc.py:88-96` 每次 `ingest()` 都建立帶 `description=DESCRIPTION` 的 `Dataset` 並 upsert，只有 column descriptions 受 `with_docs` 限制；`:115-118` 每個月都呼叫 `ingest()`。替代句正確描述實作。該檔 `:2-7` 的 docstring 仍寫 dataset description “written once”，但它不是本六筆提交新增的缺陷。 |
| S11 everything shown is in repo | “Every number here regenerates from the repo” | **未修好** | 核心 benchmark 數字確實都有 repo 內命令，但 Shot 10 又在 `docs/VIDEO-SCRIPT.md:35` 硬寫 `38 checks`；`scripts/capture_prs.py:37-45` 每次讀取可變的 GitHub live page，沒有 pin 或 assertion。今天重跑仍是 38，但只要 PR check 數改變，產生器就不會重生同一數字。這是把「素材在 repo」換成另一個全稱可重現性主張。 |
| S1 nothing failed／descriptions kept running | cut | **成立** | `docs/VIDEO-SCRIPT.md:26` 已不再聲稱 consumer 沒失敗或 description 會 running，只說同頁 schema／documentation 不一致與 docs 未跟上。 |
| S3 nobody is asking | cut | **成立** | `docs/VIDEO-SCRIPT.md:28` 已刪掉 nobody／market-wide claim，只留下 B1 可直接支持的差異。 |
| S4 no entry, no claim | “For a broken reference … no entry, no claim” | **成立** | `docs/VIDEO-SCRIPT.md:29` 已把條件限縮到 broken reference；undocumented 與 orphan findings 沒被包含在這個全稱內。 |
| S7 one DataHub cannot show | “one no DataHub page will show you” | **未修好** | `docs/L3-EVIDENCE.md:217-220` 支持的精確邊界是 standard dataset pages 不呈現、Agent Context Kit 不交付、aspect API 仍會回傳。`docs/VIDEO-SCRIPT.md:32` 的 “no DataHub page” 仍是所有頁面的全稱；原審查要求的 `standard dataset pages` 限定沒有進旁白。 |
| S7 someone documented fixture | “Document a column while `airport_fee` exists” | **成立** | 句子已改成機制描述，不再假裝 fixture 是真實使用者歷史。fixture 確實先在欄位存在時寫入 note：`bench/oracles/build_tlc_benchmark.py:76-96`。 |
| S6 same log | “the same service the detector reads” | **成立** | detector 讀 timeline service 的 TECHNICAL_SCHEMA category（`src/stilltrue/adapter.py:171-200`）；修正落在同一 timeline service 的 DOCUMENTATION category。新句不再說是同一 category／event stream。 |

## 二、兩個不可讀鏡頭與實際字數

**Shot 1 與 Shot 3 的速度問題已修好；396 字的自述沒有修好。** 我以可重現的 spoken-word 規則重算：英數／底線字、含內部 apostrophe 或 hyphen 的詞各算一個，獨立 `—` 是標點、不算朗讀詞。命令是讀取每個 narration string 後用 `re.compile(r"[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*")` 計數，再用 `actual × 60 / duration` 算 wpm。

| Shot | 秒數 | 括號宣稱 | 實際朗讀詞 | wpm | 括號是否正確 |
|---|---:|---:|---:|---:|---|
| 1 | 12 | 25 | 25 | 125.00 | 是 |
| 2 | 9 | 22 | 22 | 146.67 | 是 |
| 3 | 8 | 18 | 18 | 135.00 | 是 |
| 4 | 23 | 54 | 52 | 135.65 | **否** |
| 5 | 20 | 49 | 46 | 138.00 | **否** |
| 6 | 12 | 27 | 26 | 130.00 | **否** |
| 7 | 32 | 82 | 82 | **153.75** | 是 |
| 8 | 22 | 55 | 53 | 144.55 | **否** |
| 9 | 14 | 27 | 28 | 120.00 | **否** |
| 10 | 12 | 29 | 28 | 140.00 | **否** |
| 11 | 6 | 8 | 8 | 80.00 | 是 |

實際合計是 **388 words／170 seconds＝136.94 wpm**，不是 `docs/VIDEO-SCRIPT.md:3` 的 396 words／140 wpm；396 只是錯誤括號數的合計。最高是 Shot 7 的 153.75 wpm，因此「no shot above 154」在朗讀詞定義下成立。即使採 `str.split()`、把六個獨立 `—` 也錯算成 word，合計仍只有 394，不會得到 396；該算法會把 Shot 7 算成 155.63 wpm，也說明字數規則必須明示而不能混用。

本輪還反查 `8378707:docs/VIDEO-SCRIPT.md` 的第一版 narration strings：括號合計 440，但實際是 414 個朗讀詞；Shot 1／3 實際為 225／210 wpm，不是現行歷史敘述 `docs/VIDEO-SCRIPT.md:8` 的 275／225。原審查沿用了錯誤括號數，這次重算後該歷史句不能保留。

## 三、原 shoot blockers

### Shot 10 與 Shot 11：成立

- `git ls-files` 確認 `scripts/capture_prs.py`、`scripts/capture_card.py`、`scripts/title_card.html`、四張 `docs/evidence/prs/*.png` 與 `docs/evidence/07-title-card.png` 都已提交。
- `file` 確認四張 PR 圖都是 1440×900 PNG，片尾卡是 1920×1080 PNG，與 `docs/VIDEO-SCRIPT.md:74-78` 相符。
- 本輪把 `capture_card.py` 輸出到暫存目錄，再執行 `scripts/diff_frames.py` 與 committed PNG 比較，得到 `differing pixels: 0`、`IDENTICAL`。
- 本輪把 `capture_prs.py --out <tmp>` 跑完，四頁都印出 `Open` 並產生四張 PNG。兩張與 committed 檔逐像素相同；另兩張只有 GitHub 相對時間／頁面數字區域變化。產生器可執行，但不是固定輸出的產生器。

### Shot 7：預設安全成立，絕對不 clobber 與 `--publish` 用法不成立

`scripts/prove_invisible.sh:18-21` 預設 `OUT=runs/invisible`，因此無參數或只有 server URL 時不會覆寫已提交圖片；`runs/` 也由 `.gitignore:4` 排除。`bash -n scripts/prove_invisible.sh` 通過，本輪前後兩張 committed 圖的 SHA-256 仍分別是 `05fcbc85…` 與 `e369881e…`。

但「任何 argument path 都不能 clobber」不成立，因為下列是明確的覆寫路徑：

```text
bash scripts/prove_invisible.sh http://localhost:8080 --publish
SERVER=http://localhost:8080  OUT=docs/evidence
```

這個覆寫是設計上刻意開的 publishing path，不是意外回歸；真正的缺陷是一般直覺與 `docs/VIDEO-SCRIPT.md:49-51` 暗示的 `bash scripts/prove_invisible.sh --publish` 不能工作。`scripts/prove_invisible.sh:10` 先把 `$1` 指派給 `SERVER`，`:19-20` 才檢查 `$1`／`$2` 是否為 `--publish`，所以單獨把 flag 放 `$1` 會得到 `SERVER=--publish`、`OUT=docs/evidence`，並在第一次 DataHub 命令使用無效 server。只有有效 server 放 `$1`、flag 放 `$2` 才會真的覆寫。第三個及後續 argument 完全不參與判斷。

### Shot 9：底層流程與兩個結果成立，文件內命令不成立

`docs/VIDEO-SCRIPT.md:55-59` 已加入 clone 與兩個方向的完整參數；`cc9c2da` 的 commit message 也記錄 normal 2/2、mutated 0/2。但 commit message 只能證明有人寫下結果，不能證明歷史執行，所以本輪另做獨立重現：

```text
$ git clone --quiet https://github.com/fivetran/dbt_iterable /tmp/dbt_iterable
$ .venv/bin/python bench/run_orphan_bench_datahub.py /tmp/dbt_iterable bench/oracles/orphaned-dbt-iterable.jsonl
orphaned documentation asserted: 2/2
false alarms on correct documentation: 0/199
orphans the label file missed: 0
assertions nothing accounts for: 0

$ .venv/bin/python bench/run_orphan_bench_datahub.py /tmp/dbt_iterable bench/oracles/orphaned-dbt-iterable.jsonl --mutate-skip-rewrite
orphaned documentation asserted: 0/2
false alarms on correct documentation: 0/199
orphans the label file missed: 0
assertions nothing accounts for: 0
```

normal 約 3 分 18 秒，mutation 約 3 分 13 秒；`docs/VIDEO-SCRIPT.md:61-64` 對時程與兩個結果的主張成立。

不過，照文件原樣執行 `python3 bench/run_orphan_bench_datahub.py …`，本輪在 `bench/run_orphan_bench_datahub.py:82` 立即得到 `ModuleNotFoundError: No module named 'datahub'`。目前 shell 的依賴在 `.venv`，文件沒有 `source .venv/bin/activate`，也沒有使用 `.venv/bin/python`。因此「clone command 已補」通過，「可直接照文件拍」未通過。

## 四、刪減順序

**Shot 6 已從第三順位移除，原 finding 修好。** `docs/VIDEO-SCRIPT.md:115-122` 現在保留 Shot 6，並正確解釋 timeline entry 是 authorship 的獨立證物。

同一節仍有一個新矛盾：`:115-116` 說 Shot 3 與 Shot 9 後半是 “the only two safe cuts”，但 `:124-125` 隨即指定若要再刪，應從 Shot 7 pixel-diff tail 或 Shot 8 breakdown 取時間。文件沒有先把 “cuts” 限定為整鏡刪除，而且 Shot 9 後半本身也不是整鏡；因此不能用「前兩個是 cuts，後兩個只是 trims」化解。應改成「兩個預先排序的安全刪減」或直接列出四個允許縮短的位置與限制。

## 五、LICENSE

### 原文與 metadata：授權內容成立

- 本輪以 `curl https://www.apache.org/licenses/LICENSE-2.0.txt -o <tmp>` 後執行 `cmp -s LICENSE <tmp>`，得到 `cmp_exit=0`。兩者皆為 11,358 bytes／202 lines，SHA-256 都是 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`；根目錄 `LICENSE` 是 [Apache 官方 canonical text](https://www.apache.org/licenses/LICENSE-2.0.txt)。
- `pyproject.toml:6-7` 的 `license = "Apache-2.0"` 與 `license-files = ["LICENSE"]` 和檔案內容一致。使用目前隔離建置取得的新版 backend，`python3 -m pip wheel . --no-deps` 成功，wheel 內有 `stilltrue-0.1.0.dist-info/licenses/LICENSE`，METADATA 有 `License-Expression: Apache-2.0` 與 `License-File: LICENSE`。

### GitHub 顯示：push 到 default branch 後不需其他設定

GitHub 文件說 Licensee 會比較 repository 的 LICENSE 與已知授權，Apache 2.0 的識別字就是 `Apache-2.0`；canonical root license 已滿足辨識條件。[GitHub licensing documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#detecting-a-license)

目前 `gh repo view cyh7789/stilltrue --json visibility,licenseInfo,defaultBranchRef` 回 `visibility: PRIVATE`、`licenseInfo: null`、default branch `main`，而本機 `git status` 顯示 `main...origin/main [ahead 21]`。所以還需要把含 `LICENSE` 的提交 push 到遠端 `main`，再把 repo 設為 public；完成這兩個既定步驟後，不必另填 About 欄位，也不需要為 GitHub 辨識新增 `NOTICE`、copyright header 或其他設定。`pyproject.toml` 的授權欄位不參與 GitHub 的 repository license detection。

### 新增的 packaging 相容性缺陷

`pyproject.toml:6-7` 使用 PEP 639 的 SPDX string 與 `project.license-files`，但 `pyproject.toml:14` 只要求 `setuptools>=68`。PyPA 的 backend 支援表列出 setuptools 需 77.0.3；setuptools 官方文件也把支援列在 77 系列以後。[PyPA pyproject guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license-and-license-files)

本輪建立乾淨 venv、安裝 `setuptools==68.0.0`，再執行 `python -m pip wheel . --no-build-isolation --no-deps`，metadata generation 失敗：

```text
configuration error: `project.license` must be valid exactly by one definition
GIVEN VALUE: "Apache-2.0"
ValueError: invalid pyproject.toml config: `project.license`.
```

因此授權 metadata 的內容一致，但允許的 backend 最低版本不一致；若保留 PEP 639 格式，`build-system.requires` 應至少要求可支援它的 setuptools 版本。

## 六、這六筆提交新增的缺陷

### 1. Shot 10 把兩個已撤回主張重新放回畫面

`docs/VIDEO-SCRIPT.md:35` 指定四張 PR 頁 tiled。實際查看 committed `docs/evidence/prs/pr-49.png`，PR body 在 1440×900 frame 中清楚可讀，包含：

```text
Every description, query and dbt model that spelled it the old way kept running …
A coverage check scores that table perfectly …
```

前一句正是 S1 因 repo 沒檢查 consumer 而撤回的 claim，後一句正是 S3 被 `bench/REPORT.md:23` 的 1/2 推翻的 claim。`scripts/capture_prs.py:39-42` 說 comment thread 是 noise，但它刻意保留 PR body；Shot 10 因此在新素材中重新引入旁白剛刪掉的錯誤敘述。即使四圖 tiled 後文字變小，來源 frame 與停格仍可讀，不能當成已排除。

### 2. 新增的腳本歷史敘述不實

- `docs/VIDEO-SCRIPT.md:8-10` 說第一版是 440 words、275／225 wpm，且第二次 review 找到十個可推翻主張。第一版只有括號合計 440；實際 narration 是 414 個朗讀詞，Shot 1／3 是 225／210 wpm。原審查 `docs/REVIEW-video-final-codex.md:69-85` 的正式清單說的是 “at least eight”，而 `:92` 明確判定 Shot 6 成立，只補充同 service／不同 category；把它回寫成十個都「could be disproved」不是原審查歷史。
- `docs/VIDEO-SCRIPT.md:18-20` 說第一版「claimed only two did, and was wrong about which」。`git show 8378707:docs/VIDEO-SCRIPT.md` 的 Footage 段其實正確列出 Shot 4–5 與 Shot 9 兩個 live runs；錯誤是漏掉 Shot 7，不是列錯那兩個。
- `docs/VIDEO-SCRIPT.md:95` 在歷史欄仍用現在式說 “the title card does not exist”，但同一輪已提交 `docs/evidence/07-title-card.png` 與產生器。若要保留過去原因，應用 “did not exist at review time”。

### 3. Shot 10 的 `38 checks` 是未受約束的外部狀態

`docs/VIDEO-SCRIPT.md:35` 把 38 寫死；`scripts/capture_prs.py:37-45` 只截 live page，既不 pin commit，也不檢查 checks 數。今天 committed 與 freshly generated `pr-18628.png` 都仍顯示 38，因此當下畫面成立；但 PR 新增或重跑 checks 後，重跑產生器會讓文件與 PNG 分歧。這是本輪新增、目前尚未 stale 的硬編碼數字。

### 4. 兩支新 capture CLI 的錯誤參數沒有明確失敗介面

- `python3 scripts/capture_prs.py --out` 在 `scripts/capture_prs.py:29-31` 以未處理的 `IndexError: list index out of range` 結束。
- `python3 scripts/capture_card.py /tmp/card-a.png /tmp/card-b.png` 以 0 結束，只寫第一個檔案並靜默忽略第二個 argument；原因是 `scripts/capture_card.py:17` 只讀 `sys.argv[1]`。

這兩項不阻擋文件列出的 happy path，卻使「產生器」難以在拍攝前發現誤打參數。`capture_prs.py` 的正常路徑本輪成功，約 92 秒後產生四張圖；`capture_card.py` 正常路徑約 1.4 秒且逐像素重現 committed card。

## 最終 disposition

| 類別 | 判定 |
|---|---|
| 十項旁白 finding | **7 通過／3 未通過**：S2、S7、S11 尚未收斂。 |
| 兩個不可讀 shot | **通過**：最高 153.75 wpm；但總字數與六個逐鏡括號錯誤。 |
| Shot 10／11 素材 | **通過**：產生器與 committed PNG 都存在且可執行。 |
| Shot 7 防 clobber | **預設路徑通過；publish 介面未通過**：第二參數可刻意覆寫，第一參數 flag 會破壞 server。 |
| Shot 9 可拍性 | **結果通過；文件命令未通過**：需啟用 `.venv` 或改用 `.venv/bin/python`。 |
| Cut order | **Shot 6 修正通過；段落一致性未通過**。 |
| Apache-2.0 | **canonical text 與 GitHub 辨識前提通過；setuptools 最低版本未通過**。 |
| 是否 ready to shoot | **否**：至少先修 S2／S7／S11、Shot 9 執行器、Shot 10 的 `pr-49.png` 舊主張、字數與 cut contradiction。 |

## 本輪主要驗證命令

```text
git log --oneline 8378707..HEAD
git diff 8378707..HEAD
python3 <narration word-count script>
python3 scripts/capture_prs.py --out <tmp>
python3 scripts/capture_card.py <tmp>/card.png
python3 scripts/diff_frames.py <generated> <committed>
git clone --quiet https://github.com/fivetran/dbt_iterable /tmp/dbt_iterable
.venv/bin/python bench/run_orphan_bench_datahub.py /tmp/dbt_iterable bench/oracles/orphaned-dbt-iterable.jsonl
.venv/bin/python bench/run_orphan_bench_datahub.py /tmp/dbt_iterable bench/oracles/orphaned-dbt-iterable.jsonl --mutate-skip-rewrite
curl --fail --silent --show-error https://www.apache.org/licenses/LICENSE-2.0.txt -o <tmp>
cmp -s LICENSE <tmp>
python -m pip wheel . --no-build-isolation --no-deps  # setuptools==68.0.0 venv
python3 -m pip wheel . --no-deps                       # isolated current backend
gh repo view cyh7789/stilltrue --json visibility,licenseInfo,defaultBranchRef
```
