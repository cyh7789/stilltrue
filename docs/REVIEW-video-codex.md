# Demo 影片腳本評決

查核日期：2026-07-26（Asia/Taipei）

## 結論

**選 A，不混剪 B 的敘事順序；但拍攝前必須修掉 A 的素材誤判。**

A 在 0:00–0:21 先讓觀眾看見同一個 DataHub 頁面自相矛盾，再看見內容被修正。這直接支付 **Submission Quality** 的「觀眾能否理解做什麼、為何重要」、**Real-World Usefulness** 的問題與價值，以及 **Use of DataHub** 的寫回結果。競賽簡章把五項標準列為等權，並明說最強作品會「contribute back to the graph」；評審又可以只看提交材料而不執行專案（`/Volumes/CyhSSD/Hackathon/active/datahub/BRIEF-v2.md:56`、`:69`、`:71`、`:80`）。A 隨後仍有拒寫、內容雜湊、read-back、DataHub timeline、孤兒描述、41 個月重播與上游 PR，並非只剩產品畫面（`docs/VIDEO-SCRIPT-a.md:29`、`:33`、`:36`、`:37`、`:38`、`:40`）。

B 對 **Technical Execution** 與 **Originality** 提出的兩項素材——可降到 0/2 的突變測試、標準頁面與 Agent Context Kit 都看不到的孤兒描述——值得留在書面提交，但 B 的前 1:15 沒有任何寫回，第一次 graph write 又埋在一段以「頁面完全不變」為主旨的 38 秒鏡頭內（`docs/VIDEO-SCRIPT-b.md:43`）。接著還有 26 秒在拆掉自己的基準。Shots 4–6 合計 89 秒，把超過半支影片押在可信度辯護，犧牲 **Submission Quality** 與 **Real-World Usefulness**；較容易辨認的 description write 與 timeline 更到 2:19 才開始（`docs/VIDEO-SCRIPT-b.md:45`）。

## 查核範圍與限制

我沒有執行 `make demo`、`replay_tlc.py` 或新的 DataHub 孤兒基準，因為三者都會寫入本機 DataHub，`replay_tlc.py` 還會重寫結果檔；這是審查任務，不應改變被審查狀態（`Makefile:20`、`:25`；`bench/oracles/replay_tlc.py:83`、`:138`；`bench/run_orphan_bench_datahub.py:186`、`:190`）。我改查目前實作、已提交的逐筆結果、可驗證 ledger、圖片本身、Git 歷史與上游 GitHub 狀態。

本輪實際執行的主要查核如下：

- `python3 -m pytest -q`：**67 passed**。
- `python3 bench/freeze.py --check`：**9 files unchanged**。
- 對兩份 `1-findings.jsonl` 執行 `jq -s` 計數：TLC 為 3 DRIFT、5 CURRENT；showcase 為 1 DRIFT、6 CURRENT、29 INSUFFICIENT_EVIDENCE。
- 對 `bench/tlc-replay-results.jsonl` 執行 `jq -s`：41 筆、41 筆 `correct=true`、0 筆錯誤。
- 以 `PYTHONPATH=src` 呼叫 `AuditLedger(...).verify()`：`chain valid (10 records)`。
- `tesseract docs/evidence/03-after-documentation.png stdout`：主區與 Summary 都辨識為 `Airport_fee applies to LGA and JFK pickups only.`。
- `python3 bench/run_orphan_bench_datahub.py --mutate-skip-rewrite` 與舊 runner 的同形命令：兩者都只印 Usage 並以 1 結束，因為缺少必要的 `<repo-clone> <labels.jsonl>`。
- `gh pr view ... --json number,title,state,author,url`：`datahub#18622`、`#18628`、`#18630` 與 `datahub-skills#49` 均為 **OPEN**，標題與兩份腳本一致。
- `gh api .../datahub-enrich/SKILL.md` 與 `.../datahub-search/SKILL.md`：確認 `datahub-enrich` 的確涵蓋 description update，`datahub-search` 也的確把 systematic audit 舉例為「how complete is our metadata」。

## A：哪些成立，哪些不成立

| 主張／鏡頭 | 判定 | 查核結果 |
|---|---|---|
| S1–S2 的同頁矛盾與修正畫面 | **成立** | `02-before-columns.png` 顯示欄位 `Airport_fee`、Summary 顯示 `airport_fee`；`04-after-columns.png` 兩處都是 `Airport_fee`，版本籤由 2.0.0 變成 4.0.0。腳本來源在 `docs/VIDEO-SCRIPT-a.md:29`、`:30`；`tesseract` 也確認 after 圖的文字。 |
| S3 的 2023-02 大小寫改名與 2025-01 新欄位 | **成立** | 兩個事件直接列於 `bench/oracles/tlc-drift-events.json:3` 與 `:16`；產生器以連續月份 schema 集合差異推導 added／removed／case rename（`bench/oracles/scan_tlc.py:56`）。 |
| S4 的 `3 drift, 5 verified current` 與三類 finding | **成立（依提交產物，未重跑 DataHub）** | `jq` 計數目前 `examples/tlc-rename/1-findings.jsonl` 得 8 checks＝3 DRIFT＋5 CURRENT，三類依序為 `D1_SCHEMA_BREAK`、`D1_UNDOCUMENTED`、`D1_ORPHANED_DOC`。CLI 的 tally 輸出由 `src/stilltrue/cli.py:143` 產生。五個 Kit 讀取工具也確實列在 `src/stilltrue/adapter.py:42`。 |
| S5–S7 的 NOT_APPROVED、STALE、VERIFIED 與 read-back | **成立** | 內容雜湊涵蓋 before、after、URN、aspect、verdict、evidence（`src/stilltrue/proposal.py:56`）；無 token 與不符 token 分別回 NOT_APPROVED／STALE（`:116`、`:122`）；CLI 會印差異（`src/stilltrue/cli.py:324`）；只有寫後讀回相同才回 VERIFIED（`src/stilltrue/executor.py:149`）。67 個測試全過。 |
| S8 的 DataHub timeline 記錄寫回 | **成立（有提交證據，未重跑 live curl）** | 命令與 old/new Documentation event 在 `docs/L3-EVIDENCE.md:162`、`:168`、`:173`。這是 graph contribution 的直接證據，比單看 after 截圖更有力。 |
| S9 的孤兒描述存在、標準 Columns 頁不呈現、Kit 丟掉 aspect、移除後 aspect 為空 | **機制成立；所稱 UI 前後證據不成立** | 分離讀取 `editableSchemaMetadata` 正是 detector 能看見孤兒的原因（`src/stilltrue/adapter.py:127`）；移除前會再確認欄位確實不在完整 schema，寫後再讀回（`src/stilltrue/executor.py:112`、`:149`、`:180`）。但 `docs/L3-EVIDENCE.md:228` 明確重用四節前的同一個 `04-after-columns.png`，不是移除前後兩次擷取；同一檔案不能證明寫入後畫面沒變。 |
| S10 的 41/41、1＋1＋39 拆解 | **成立但證據多樣性低** | `jq` 查得 41/41、0 錯誤；報告也主動揭露 1 個安靜月份、1 個事件月份、39 個持續同一狀態（`bench/REPLAY-REPORT.md:22`、`:30`）。它證明 41 次狀態判定一致，不是 41 個不同事件。 |
| S10 的 29 abstentions | **數字成立** | `jq` 查得 29 INSUFFICIENT_EVIDENCE、6 CURRENT、1 DRIFT；不完整 schema 的 guard 位於 `src/stilltrue/cli.py:108`，實際 showcase 輸出則在 `examples/abstention/README.md:6`。 |
| S11 的 10-record chain | **成立** | 本輪對已提交 ledger 執行 `AuditLedger.verify()` 得 `chain valid (10 records)`；驗證邏輯會重算 entry hash 並檢查 prev hash（`src/stilltrue/ledger.py:66`）。 |
| S12 的四個上游 PR | **成立且目前皆 OPEN** | 本輪四次 `gh pr view` 的編號、標題、狀態均與 `docs/VIDEO-SCRIPT-a.md:72` 一致。這同時支付 Bonus 與 Originality，但影片口白不應說它們已合併。 |

A 有三個必須在拍攝前刪改的事實錯誤：

1. `03-after-documentation.png` 的右側 Summary **不是**小寫。A 的 production note 說右側仍是 `airport_fee`（`docs/VIDEO-SCRIPT-a.md:170`），但直接開圖與 OCR 都顯示主區、右側皆為 `Airport_fee`。不需要為此裁切。
2. S9 dry run **不再需要獨立拍攝**。A 說 `scripts/demo.sh:45` 把輸出吃掉（`docs/VIDEO-SCRIPT-a.md:181`），目前腳本已用 `tee /dev/stderr` 顯示整段 proposal，再從同一段輸出取 token（`scripts/demo.sh:45`、`:49`、`:50`）。`git show a823599 -- scripts/demo.sh` 也確認這項修正已進 HEAD。
3. 「移除孤兒前後是同一張圖」不是證據，而是重複素材。若成片要聲稱 UI 確實沒有變，必須在修正 dataset description 之後、移除 orphan 之前擷取一次，再在移除之後以相同 viewport 擷取第二次，最後做 pixel diff。repo 目前只有 `04-after-columns.png` 這一張對應狀態；要使用此主張，這兩份新素材尚待製作。

因此 A 開頭 `nothing here needs footage that does not exist`（`docs/VIDEO-SCRIPT-a.md:3`）不成立。

## B：哪些成立，哪些不成立

| 主張／鏡頭 | 判定 | 查核結果 |
|---|---|---|
| Shot 1 的矛盾頁 | **成立** | 與 A S1 同一張已查核圖片。 |
| Shot 2 的 `complete, not correct` 原文 | **引文成立；結論超出引文** | 本輪 `gh api` 取得的 `datahub-search/SKILL.md` frontmatter 的確寫「For systematic audits (\"how complete is our metadata\"), use /datahub-audit.」；`datahub-enrich` 也確實支援 description update。但「Every catalog audit asks whether a description exists」是 B 的概括，不是該引文所證明的普遍事實。 |
| Shot 3 的 3／5／0 與 change-log gate | **成立（依提交產物）** | finding 計數如上；目前 detector 先找近似 successor（`src/stilltrue/detectors.py:267`），但只有 change log 的 `gone` 記錄存在才會斷言 DRIFT（`:268`、`:272`）；僅有近似名稱則 abstain（`:275`、`:283`）。生成的 reality 可見 `examples/tlc-rename/1-findings.jsonl:1`。 |
| Shot 4 的 29 abstentions 與 incomplete-read guard | **成立** | 計數、目前 guard 與 `examples/abstention/README.md:54` 相符；`git show ce8d835` 也記錄修正前 120 欄只讀 100 欄、把 live description 判成 orphan 的重現。 |
| Shot 5 的孤兒機制 | **窄版成立，廣版不成立** | 「標準 dataset page 不呈現、Kit 不交付、aspect API 能取回」是 repo 自己給出的精確邊界（`docs/L3-EVIDENCE.md:209`、`:217`）。B 在論證段說它「has no DataHub surface at all」（`docs/VIDEO-SCRIPT-b.md:143`）則是錯的：aspect API 就是 DataHub surface，B 的 Shot 5b 也正在拍它。 |
| Shot 5 的 identical before/after | **素材不存在** | B 說把同一檔案放兩次證明相同（`docs/VIDEO-SCRIPT-b.md:43`、`:70`）。這只能證明剪輯軟體重用了同一張圖，不能證明 DataHub 在兩次獨立讀取間沒有畫面差異。所需補拍與 pixel diff 同 A 第 3 點。 |
| Shot 6 的 41/41 | **成立** | 目前 JSONL 為 41/41，報告也揭露 1＋1＋39。 |
| Shot 6 的新 harness 0/2、舊 harness 仍 2/2 | **核心機制成立；腳本寫的拍攝命令不能執行** | 新 runner 的 mutation 會略過第二次 schema ingestion（`bench/run_orphan_bench_datahub.py:190`）；舊 runner 不解析此旗標（`bench/run_orphan_bench.py:34`）。但兩者都要求 clone 與 labels（`bench/run_orphan_bench_datahub.py:35`；`bench/run_orphan_bench.py:14`）。本輪照 B 寫法執行只得到 Usage。若要拍這一幕，必須先準備 `fivetran/dbt_iterable` clone，帶入 `bench/oracles/orphaned-dbt-iterable.jsonl`，啟動 DataHub，然後用完整命令各跑一次；repo 目前沒有這段終端機 footage。 |
| Shot 7 的拒寫、寫回、timeline、四 PR | **行為與 PR 狀態成立；固定 hash 不保證 live 重現** | proposal hash 包含 evidence ids（`src/stilltrue/proposal.py:56`），evidence id 又包含讀回 payload（`src/stilltrue/evidence.py:57`）；反覆 load 會累積 timeline 版本，所以 live run 不應硬套 `a844edb7f3b94d57`。若用 live footage，整段必須維持同一 run；若用提交證據，應明說是 committed run。 |
| 「nine change categories documented in skills repo」 | **目前不成立** | 本輪從 upstream 讀取 `skills/shared-references/datahub-cli-reference.md`，列出的 categories 是 `tag`、`glossary_term`、`technical_schema`、`documentation`、`owner` 五項，不是 B 所說九項（`docs/VIDEO-SCRIPT-b.md:152`）。這不影響 timeline 本身有價值，但不能拿九項作旁白或字幕。 |
| Production note 的兩個「拍前要修」 | **兩個都已過期** | README 已是 29（`README.md:120`），L3 與 replay report 也已換成現行 change-log wording（`docs/L3-EVIDENCE.md:54`；`bench/REPLAY-REPORT.md:66`）。B 仍說兩者待修（`docs/VIDEO-SCRIPT-b.md:90`）。 |
| Shot 8 的「Everything shown is committed, unedited」 | **不成立** | PR 頁、live terminal、加框、標題卡與尚未用完整命令產生的 mutation panes 都不是已提交的原始 footage。repo 提交的是來源與文字證據，不是 B 所描述的每一幀。 |

## 對兩份腳本最強論點的反駁

### A：前 21 秒問題→結果，是否是唯一能活過提早離場的結構？

不是唯一，而且 A 把「看見 after 圖」說成「看見工具完成寫回」。0:00–0:21 的兩張靜態圖片證明頁面前後不同，卻不單獨證明變化由 StillTrue 產生；能把因果鏈釘死的是後面的 NOT_APPROVED／STALE／VERIFIED 與 DataHub timeline（`docs/VIDEO-SCRIPT-a.md:33`、`:36`）。若評審真的在 21 秒離場，**Technical Execution** 的 end-to-end 要求仍未獲證明（`/Volumes/CyhSSD/Hackathon/active/datahub/BRIEF-v2.md:72`）。

但這只推翻「唯一」，不推翻 A 的結構優勢。對可能提早離場的評審，先交付可理解的問題與可見結果，仍比 B 把第一次寫回埋在 1:15–1:53 的「頁面不變」鏡頭內，更符合 **Submission Quality** 與 **Real-World Usefulness**。因此我的結論不是刪掉 A 的開場，而是不要把兩張圖當作完整證明；後續 timeline 必須保留。

### B：因為 Nick Adams 在評審席且 `datahub-enrich` 能寫描述，產品畫面是否會直接輸掉 Originality？

事實部分成立：Nick Adams 是七位名列評審之一，且是 Agent Context Kit 文章作者（`/Volumes/CyhSSD/Hackathon/active/datahub/BRIEF-v2.md:84`、`:92`）；`datahub-enrich` 也確實能更新 descriptions。**但 Nick 不是這個推論的承重點。**

第一，Originality 條文本身明說延伸或組合既有能力是允許的，禁止的是把現成功能假裝從零重做（`/Volumes/CyhSSD/Hackathon/active/datahub/BRIEF-v2.md:73`）。StillTrue 的區別不是「能不能寫 description」，而是以 timeline 判斷描述是否仍正確、將批准綁到確切內容、寫後讀回、處理 UI／Kit 都漏掉的 orphan，並把修正送回 graph。第二，Nick 只是七席之一，主辦還保留更換名單與混合評審方法的權利（`/Volumes/CyhSSD/Hackathon/active/datahub/BRIEF-v2.md:82`）。第三，B 攻擊的是不存在的 A：它說產品版「spends its entire runtime」在原生寫入外觀（`docs/VIDEO-SCRIPT-b.md:137`），但 A 的 DataHub 頁面 before/after 只有前 21 秒，其餘 128 秒正是在展示非原生機制與證據。

所以 B 找到的是一個真實的**辨識風險**：若影片只留下 description change，確實容易被歸類成 enrich。把它升格成「因為 Nick 在，所以產品示範必輸」則是好聽的故事，不是評分規則或評審結構推出的結論。解法是讓 timeline-based detection 與安全寫回在畫面上清楚可見，不是放棄產品示範。

## 一個新增、一個刪除

### 新增：0:21–0:29，接在 A S2 後

加入 `bench/REPORT.md:20` 的四列 baseline 表，只停在兩列：coverage-only 1/2、StillTrue 2/2。字幕必須寫 **coverage-only baseline**，不要寫成 DataHub 原生功能逐行重現，因為 repo 自己只主張它近似 completeness surface（`docs/NATIVE-COMPARISON.md:153`）。

這份來源素材已存在；repo 尚無這八秒的影片檔，製作時要錄下 rendered markdown，但不需另造數字或圖表。它用八秒回答 B 最有價值的問題：現成 DataHub 能看「有沒有」，StillTrue 多抓到「有但錯」的 rename。主要支付 **Originality**，同時讓 A 的開場不會只像 `datahub-enrich`。

### 刪除：兩份腳本的 29-abstention 段落

- A：刪 S10 最後約 8 秒，約 2:07–2:15；A 自己的超時刪除順序也把這句列為 −8 秒（`docs/VIDEO-SCRIPT-a.md:49`）。
- B：刪 Shot 4 全段 0:50–1:15（`docs/VIDEO-SCRIPT-b.md:42`）。

29 abstentions 與 partial-read guard 是好工程，但在 170 秒內，它要求觀眾先理解分母、verdict 類型與曾經的刪除風險，卻沒有讓產品價值更清楚。它主要是 repo／README 的審查材料。影片應把省下的時間留給 graph write、timeline 與上面的 baseline 差異；這對 **Submission Quality**、**Real-World Usefulness** 與 **Originality** 都更直接。
