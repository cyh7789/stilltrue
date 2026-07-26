# 影片腳本收斂覆核

查核日期：2026-07-26（Asia/Taipei）

查核範圍：`git show 9982848`，以及目前的 `docs/VIDEO-SCRIPT.md`、`scripts/prove_invisible.sh`、`pyproject.toml`。前兩輪審查與 `docs/REVIEW-video-fixes-codex.md` 只用來核對本輪明列的歷史與既有 finding，沒有向外重做整份專案審查。

## 一、提交是否修好所稱問題，是否造成破壞

### 結論

**核心修正成立，正常拍攝路徑沒有被破壞。** `pip install -e .` 在乾淨 Python 3.11 與 3.13 環境通過；`setuptools>=77` 是能接受目前 PEP 639 欄位的正確最低系列；`--publish` 的正常位置、預設輸出、逐鏡字數、三句旁白、PR #49 本文與截圖都通過。

這筆提交仍沒有做到字面上的「全部乾淨」：腳本的自述歷史還有兩個數字錯誤，三個「Now」欄位仍引用已撤回句子；`prove_invisible.sh` 對兩個伺服器、`--` 與空字串沒有嚴格介面；第三輪提過的兩支擷取 CLI 錯誤參數介面也不在本提交差異中。這些都是文件或無效輸入的邊角，不影響目前分鏡、旁白真實性或文件列出的拍攝命令。

### 1. `pip install -e .` 與 `setuptools` 下限

**通過。** `pyproject.toml:6-8` 的 SPDX 授權表示式、授權檔與相依套件彼此一致；`:13-18` 把建置後端下限改成 `setuptools>=77`，而套件搜尋仍在 `:20-21` 指向 `src`。

我把 `9982848` 用 `git archive` 展開到暫存目錄，在乾淨 Python 3.11 venv 原樣執行：

```text
python -m pip install -e <temp-repo>
Successfully built stilltrue
Successfully installed ... stilltrue-0.1.0

python -m pip check
No broken requirements found.

stilltrue --help
exit 0
```

同一個原樣安裝與 `pip check` 在 Python 3.13 也通過。獨立建置出的 wheel 含 `stilltrue-0.1.0.dist-info/licenses/LICENSE`，METADATA 有 `License-Expression: Apache-2.0`、`License-File: LICENSE`、`Requires-Python: >=3.11` 與四個 `Requires-Dist`，命令列進入點仍是 `stilltrue = stilltrue.cli:app`。沒有發現本提交造成的其他中繼資料不一致。

下限不是只靠文件推斷；我在同一個 Python 3.11 venv 逐版安裝建置後端，再跑 `python -m pip wheel --no-build-isolation --no-deps <temp-repo>`：

| `setuptools` | 結果 |
|---:|---|
| 68.0.0 | 失敗：`project.license` 同時符合兩個舊 schema 定義 |
| 76.1.0 | 同樣失敗 |
| 77.0.1 | 通過 |
| 77.0.3 | 通過 |

`pip index versions setuptools` 顯示 77 系列最早可安裝的版本是 77.0.1，沒有 77.0.0；因此 `>=77` 的實際最低候選就是已實測通過的 77.0.1。舊 `>=68` 確實允許會拒絕 PEP 639 欄位的建置後端，本次下限修正正確。

有一個不歸因於本提交的相容性邊角：本機未啟用 venv 的 `python3` 是 `3.14.0a7`，其完整安裝在 `pydantic-core 2.33.2` 的 PyO3 建置失敗，訊息是該 PyO3 最高支援 Python 3.13。StillTrue 的可編輯 wheel 在此前已成功建成；失敗來自遞移相依套件。若 `requires-python = ">=3.11"` 被解讀成也保證所有未來或預發行直譯器，這個範圍過寬；對本專案實際使用的 Python 3.11 與另測的穩定版 3.13，安裝成立。這不是 `9982848` 新增的回歸，也不是影片拍攝阻擋項。

### 2. `prove_invisible.sh` 參數

**正常用法通過，無效輸入有三個邊角。** 目前解析器在 `scripts/prove_invisible.sh:21-29` 先設定 `SERVER=http://localhost:8080`、`OUT=runs/invisible`，再逐一處理所有引數；只有完全相等的 `--publish` 會把 `OUT` 改成 `docs/evidence`。`mkdir` 與狀態輸出在 `:30-31`，後續命令都使用這兩個解析結果。`bash -n scripts/prove_invisible.sh` 通過。

我直接抽取並執行 `:21-29` 的現行解析區塊，避免真的改寫 DataHub，結果如下：

| 引數 | 結束碼 | `SERVER` | `OUT` | 判定 |
|---|---:|---|---|---|
| 無 | 0 | `http://localhost:8080` | `runs/invisible` | 預設成立 |
| `http://one:8080` | 0 | `http://one:8080` | `runs/invisible` | 不發布 |
| `--publish` | 0 | 預設伺服器 | `docs/evidence` | 旗標沒進 SERVER |
| 伺服器後接 `--publish` | 0 | 該伺服器 | `docs/evidence` | 成立 |
| `--publish` 後接伺服器 | 0 | 該伺服器 | `docs/evidence` | 成立 |
| `--publish --publish` | 0 | 預設伺服器 | `docs/evidence` | 重複旗標為冪等 |
| `--publish server1 server2` | 0 | `server2` | `docs/evidence` | 最後一個伺服器靜默勝出 |
| `server1 --publish server2` | 0 | `server2` | `docs/evidence` | 最後一個伺服器靜默勝出 |
| `-- server` | 2 | 未完成 | 未完成 | `unknown option: --` |
| 空字串 | 0 | 空字串 | `runs/invisible` | 不會回到預設伺服器 |
| `--publish` 加空字串 | 0 | 空字串 | `docs/evidence` | 發布仍只由旗標觸發 |
| `--wat` | 2 | 未完成 | 未完成 | 未知 option 明確失敗 |

所以提交主張的三件事都成立：`--publish` 在正常引數序列的任何位置都不會成為伺服器；無旗標仍預設寫 `runs/invisible`；只有出現 `--publish` 才選 `docs/evidence`。兩個伺服器最後一個勝出、標準 `--` 分隔符不受支援、空字串可覆蓋預設伺服器，則是缺少引數驗證的邊界情況。它們不會讓未帶 `--publish` 的命令覆寫已提交證據，也不影響 `docs/VIDEO-SCRIPT.md:55-59` 所列的無參數與 `--publish` 用法。

### 3. 逐鏡字數、總數與上限

**全部通過。** 我沒有採用文件中的括號數，而是從每一列旁白字串重新擷取文字，再以 `docs/VIDEO-SCRIPT.md:3-7` 明訂的 `[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*` 計數：

| Shot | 文件字數 | 重算字數 | 秒數 | wpm |
|---|---:|---:|---:|---:|
| 1 | 25 | 25 | 12 | 125.000 |
| 2 | 23 | 23 | 9 | 153.333 |
| 3 | 18 | 18 | 8 | 135.000 |
| 4 | 52 | 52 | 23 | 135.652 |
| 5 | 46 | 46 | 20 | 138.000 |
| 6 | 26 | 26 | 12 | 130.000 |
| 7 | 83 | 83 | 32 | 155.625 |
| 8 | 53 | 53 | 22 | 144.545 |
| 9 | 28 | 28 | 14 | 120.000 |
| 10 | 28 | 28 | 12 | 140.000 |
| 11 | 9 | 9 | 6 | 90.000 |

命令輸出為 `rows=11 total=391 duration=170 overall_wpm=138.000`。十一個括號都和旁白字串相符；391 與 `docs/VIDEO-SCRIPT.md:3` 一致；最高是 Shot 7 的 155.625 wpm，沒有鏡頭超過文件所稱的 156。

### 4. 三句旁白替代文是否真的成立

**三句都成立，不只是變模糊。**

1. **Shot 2：成立。** 現行句子是「could not write until it was handed the hash of that exact proposal」（`docs/VIDEO-SCRIPT.md:35`）。第三輪已定位的機制顯示示範腳本沒有人工審閱，proposal hash 涵蓋 URN、aspect、subject、before、after、verdict 與 evidence，apply 又要求相符 token（`docs/REVIEW-video-fixes-codex.md:19`）。新句不再虛構 reviewed text 或人類確認，並準確說明「必須拿到該 exact proposal 的 hash 才能寫」。
2. **Shot 7：成立。** 現行句子明確限縮為「no standard dataset page」（`docs/VIDEO-SCRIPT.md:40`）。既有證據邊界正是 standard dataset pages 不呈現、Agent Context Kit 不交付、aspect API 仍可回傳（`docs/REVIEW-video-fixes-codex.md:26`）；後一句也保留 aspect API 例外，因此不再自我反駁。
3. **Shot 11：成立。** 現行句子是「Every benchmark number here regenerates from the repo」（`docs/VIDEO-SCRIPT.md:44`）。第三輪已確認核心 benchmark 數字都有 repo 內命令，當時唯一反例是 Shot 10 寫死的 GitHub 即時 `38 checks`（`docs/REVIEW-video-fixes-codex.md:22`）。本提交把 Shot 10 改成不宣稱固定檢查數，並要求 PR 狀態改變時重拍（`docs/VIDEO-SCRIPT.md:43`）；PR 編號、年份等畫面文字不是 benchmark number。新限定與實際再生邊界一致。

旁白雖已修正，`docs/VIDEO-SCRIPT.md:96-109` 的歷史表沒有同步：`:100` 的 Now 仍寫 `reviewed text`，`:103` 仍寫 `every number`，`:107` 仍寫 `no DataHub page`。表頭又說「Now fixed in the text above」。這三格不是要朗讀的旁白，但它們把已撤回的替代句留在一個防止舊句復發的表中，是本提交留下的文件一致性錯誤。

### 5. 自述歷史

使用同一計數規則處理 `git show 8378707:docs/VIDEO-SCRIPT.md`，命令得到 `actual_total=414`，Shot 1 為 45 words／12 秒＝225 wpm，Shot 3 為 28 words／8 秒＝210 wpm。`docs/VIDEO-SCRIPT.md:14-16` 的 **414、225、210 都正確**。

其餘兩個指定歷史主張也正確：

- 第二輪審查在 `docs/REVIEW-video-final-codex.md:69-85` 寫「至少八項」，並正式編號 1–8；目前 `docs/VIDEO-SCRIPT.md:17` 的「listed eight formally」沒有把第三輪拆成十項的分類倒灌回第二輪。
- `8378707:docs/VIDEO-SCRIPT.md:34-48` 的 Footage 段確實列出 Shot 4–5 與 Shot 9，卻把 `prove_invisible.sh` 放進「Everything else」，沒有把 Shot 7 標成 live footage。因此目前 `docs/VIDEO-SCRIPT.md:26-28` 說它「missed shot 7」是正確歷史，不是說原本列錯另外兩個。

但同一段還有兩個未被指定三項涵蓋的錯誤：

- `docs/VIDEO-SCRIPT.md:13-14` 說第一版十一列只有六列錯。獨立重算 `8378707` 得十一列的括號數全都不符旁白字串，輸出是 `wrong_rows=11`。
- `docs/VIDEO-SCRIPT.md:14` 說第一版「stated total of 440」。`8378707:docs/VIDEO-SCRIPT.md:3` 的標頭寫的是 **428**；440 是十一個錯誤括號數的合計，不是文件陳述的總數。正確說法應區分「標頭寫 428」與「逐鏡標示合計 440」。

這兩點使自述歷史段落仍非全真，但不改變旁白、時間或任何拍攝素材。

### 6. datahub-skills#49 本文與截圖

**通過。** 本輪執行：

```text
gh pr view 49 -R datahub-project/datahub-skills --json body,updatedAt,url
```

目前 PR 本文不含「Every description, query and dbt model that spelled it the old way kept running」或「A coverage check scores that table perfectly」。它改成可支持的兩段：舊拼法的 descriptions「stopped matching the schema」，coverage-only 找到 2025 新增但未文件化的欄位、漏掉 rename，分數是二取一。PR 的 `updatedAt` 是 `2026-07-26T14:35:54Z`。

`docs/evidence/prs/pr-49.png` 也確實是修正文後的頁面：

- `git rev-parse` 顯示父提交的 blob 是 `877aaae…`，`9982848` 內是不同的 `2e826d33…`；提交時間為 `2026-07-26T22:44:46+08:00`，晚於 PR 更新約九分鐘。
- 直接查看 1440×900 PNG，可讀到 `stopped matching the schema` 與 coverage-only `misses the rename entirely -- one of the two`。
- 對 PNG 執行 OCR、把換行正規化後，兩句新文都存在，`kept running` 與 `scores that table perfectly` 都不存在。

因此不是只改遠端 PR 本文而忘記素材；已追蹤截圖隨本提交換成修正頁。

### 7. 是否破壞其他東西

在指定範圍內，**沒有正常路徑回歸**：安裝、命令列進入點、授權中繼資料、預設不覆寫、明示發布、字數上限、拍攝句子與 PR 素材都成立。發現的殘項分類如下：

| 殘項 | 分類 | 是否阻擋拍攝 |
|---|---|---|
| 自述歷史的「六列」與「stated 440」 | 文件錯誤 | 否 |
| Claims 表的三個 stale Now 欄 | 文件錯誤 | 否 |
| 兩個伺服器採最後值、拒絕 `--`、接受空伺服器 | 無效輸入邊界情況 | 否 |
| Python 3.14.0a7 遞移相依套件建置失敗 | 預發行相容性邊界情況；非本提交造成 | 否 |
| 第三輪 `docs/REVIEW-video-fixes-codex.md:153-158` 的兩支擷取 CLI 錯誤參數介面 | 既有邊界情況；`git show 9982848 --stat` 沒有修改那兩支檔案 | 否 |

最後一項只按本輪允許的 `git show` 判定「未被此提交處理」，沒有越界重跑或重審擷取腳本。它也從未使第三輪正常路徑失敗（同一審查 `:158`）。所以「第三輪所有阻擋開拍的項目已處理」成立；「第三輪記錄的每個邊界情況都已修改」不成立。

## 二、是否已經收斂

**已收斂。不要再跑一輪與前三輪同範圍的完整覆核。**

理由不是輪數或嚴重度趨勢，而是本輪狀態：前次三句旁白都已變成可證明的句子；字數與速度全部重算一致；安裝與 PEP 639 建置後端下限通過實測；Shot 7 的正常解析路徑不會誤覆寫；Shot 9 已使用 venv 直譯器（`docs/VIDEO-SCRIPT.md:61-67`）；刪減段落已成單一有序清單（`:121-135`）；PR #49 的錯誤畫面也已更換。沒有剩下會改變旁白真實性、素材能否取得、拍攝順序或影片時間的結構缺陷。

剩餘 finding 是兩組自述文件錯誤與幾個異常輸入／預發行相容性邊界情況。依第三輪自己的證據，未改的擷取 CLI 問題也不擋正常路徑。可做一次小型文件與 CLI 清理，但那是直接修這些已定位項目，不需要再開第四輪全片審查；清理後只需針對改動行做字數與解析器回歸檢查。

最終判定：**影片審查已收斂，可依目前旁白與正常拍攝命令進入拍攝。**
