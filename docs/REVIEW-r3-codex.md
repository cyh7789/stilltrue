## 依失分風險排序

### 1. 高風險：核心聲稱「證明 token 曾是欄位」，實作卻允許無歷史證據的推測

`README` 說每個斷言都要先證明 token 曾是此資料集的欄位，來源是現行 schema 的近似欄位或 timeline 離開紀錄；表格又把 D1 的 reality 直接寫成 DataHub change log。[README.md:44](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:44)、[README.md:61](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:61)

實作不是如此：

- `_rename_candidate()` 只比較大小寫與底線位置。[src/stilltrue/detectors.py:184](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/detectors.py:184)
- 找到近似欄位後立即回報 `DRIFT`，之後才檢查 timeline 的 `gone`。[src/stilltrue/detectors.py:265](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/detectors.py:265)
- 測試明確要求沒有 change history 也必須斷言 rename。[tests/test_detectors.py:205](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/tests/test_detectors.py:205)

現行 schema 有 `deal`，描述提到非欄位概念 `DEAL`，並不能證明 `DEAL` 過去曾是欄位。這仍是受限的字串推測，不是歷史證據。

會改變我看法的條件：rename 也必須同時具備精確的 timeline 移除事件或歷史 schema，近似欄位只能用來找 successor。TLC 已有 `airport_fee` 的精確移除紀錄，不需要犧牲主案例。

### 2. 高風險：TLC 的 `41/41` 是時間穩定性測試；報告的「事件 2/2」則是實質錯誤

`expected_state()` 對固定 `DESCRIPTION` 累積 `EVENTS.removed`，再取交集。[bench/oracles/replay_tlc.py:50](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/oracles/replay_tlc.py:50) 實際結果只有：

- 2023-01：空集合。
- 2023-02 至 2026-05：全部都是 `{"airport_fee"}`。[bench/tlc-replay-results.jsonl:1](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/tlc-replay-results.jsonl:1)

所以它是「1 次安靜、1 次 onset、39 次 persistence」，不是 41 個獨立偵測案例。每月真的重新寫入與讀取 DataHub，因此它仍有 soak／回歸價值；但首頁的「41 consecutive decisions, not two」會讓證據看起來比實際多樣性更高。[README.md:195](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:195)

更嚴重的是 `Drift caught in the month it happened: 2/2`：

- 第二個事件是 2025-01 新增 `cbd_congestion_fee`，沒有 removed 欄位。[bench/oracles/tlc-drift-events.json:16](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/oracles/tlc-drift-events.json:16)
- replay 只保留 `D1_SCHEMA_BREAK`，排除了會抓新增欄位的 `D1_UNDOCUMENTED`。[bench/oracles/replay_tlc.py:123](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/oracles/replay_tlc.py:123)
- onset 分數只是檢查該月整體持續狀態仍正確，不是檢查當月事件是否被抓到。[bench/oracles/replay_tlc.py:143](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/oracles/replay_tlc.py:143)

因此 2025-01 被算成「caught」，但 replay 對該事件根本沒有評分。[bench/REPLAY-REPORT.md:28](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/REPLAY-REPORT.md:28)

更強的設計應分開報：

- schema-break onset：1/1。
- persistence：39/39。
- pre-event quiet：1/1。
- undocumented-column onset：另行評分。
- 多個描述修正、刪除、重新加入與第二次 rename，測 `CURRENT → DRIFT → CURRENT`，而不是永久維持同一答案。

這樣的事件級完整評分會改變我對 `41/41` 證據強度的判斷。

### 3. 高風險：orphan holdout 的結果由建構方式決定，不是 transfer 證據

正例 oracle 定義為「欄位離開 SQL，描述仍在 yml」；負例定義為欄位同時存在於 SQL 與 yml。[bench/oracles/mine_orphaned_docs.py:79](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/oracles/mine_orphaned_docs.py:79)

評分器把該欄位、描述與 after-schema 直接交給偵測器。[bench/run_orphan_bench.py:50](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/run_orphan_bench.py:50) 偵測器的全部判斷就是「描述非空且 field 不在 schema」。[src/stilltrue/detectors.py:370](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/detectors.py:370)

這三段是同一個 predicate。`2/2` 與 `0/199` 只能證明集合差程式沒有壞，不能證明未知資料上的 transfer，也沒有測到最可能失敗的 DataHub aspect 讀取。

原本 honesty note 只承認正例少、無法估算比率，以及選樣門檻用了舊 oracle。[bench/HOLDOUT-orphan-iterable.md:27](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/HOLDOUT-orphan-iterable.md:27)、[bench/HOLDOUT-orphan-iterable.md:35](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/HOLDOUT-orphan-iterable.md:35) `docs/VALIDATION-INTEGRITY.md` 更停留在已淘汰的前兩輪偵測器與 13/32、4/12 結果。[docs/VALIDATION-INTEGRITY.md:94](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/docs/VALIDATION-INTEGRITY.md:94)

目前未提交的 README 已正確承認真正問題。[README.md:209](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:209) 這項並行修改若保留，會大幅降低 Submission Quality 風險，但不會增加模型效度。

新出現的 `run_orphan_bench_datahub.py` 方向正確：它經 DataHub 寫入與 adapter 回讀。[bench/run_orphan_bench_datahub.py:15](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/run_orphan_bench_datahub.py:15) 但尚未執行或產生報告，而且同一 model 的 URN 會跨案例重用，先前 editable metadata 可能殘留；評分又只檢查每筆標記欄位是否出現在 `said`，沒有把其他非預期斷言算成誤報。[bench/run_orphan_bench_datahub.py:138](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/run_orphan_bench_datahub.py:138)、[bench/run_orphan_bench_datahub.py:159](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/run_orphan_bench_datahub.py:159)

會改變我看法的條件：每個案例使用隔離 URN 或清除 editable aspect，直接比較完整 `asserted == expected` 集合，並把完整 production read path 的結果納入報告。

### 4. 中高風險：freeze 是六檔完整性檢查，不是「沒有依 holdout 調整」的證明

`freeze.py --check` 目前確實通過：六個檔案自 2026-07-26 06:33:19 UTC 起未變。[bench/freeze.py:99](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/freeze.py:99)

但仍有不改六個雜湊就能改變結果的路徑：

- 凍結的 miner 與 scorer 都 import 未凍結的 `mine_drift_labels.py`。[bench/oracles/mine_orphaned_docs.py:34](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/oracles/mine_orphaned_docs.py:34)、[bench/run_orphan_bench.py:29](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/run_orphan_bench.py:29)
- `select_holdout.py` 未凍結，且選源排除名單硬寫在程式裡，不是單純執行 `freeze.json` 的規則。[bench/select_holdout.py:42](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/select_holdout.py:42)
- selector 實際呼叫舊的 `mine_drift_labels.py`，不是凍結的 orphan miner。[bench/select_holdout.py:80](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/select_holdout.py:80)
- `freeze.json` 本身沒有外部簽章；checker 只信任裡面的 expected hash，也不驗證目前 `HEAD` 或執行次數。[bench/freeze.py:103](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/freeze.py:103)

這不表示實際有調參；它表示 `--check` 不能證明 README 賦予它的完整選樣與單跑敘事。

會改變我看法的條件：凍結 selector、所有遞迴匯入、依賴鎖、來源 commit SHA、標籤與結果；用簽署 commit／tag 或外部 CI artifact 錨定 manifest。單靠 repo 內自填雜湊永遠無法證明「只跑一次」。

### 5. 中風險：L3 的 absence 論證不成立

L3 同時證明兩件事：

- direct aspect API 能取回 orphan note。[docs/L3-EVIDENCE.md:172](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/docs/L3-EVIDENCE.md:172)
- 四張特定截圖沒有它。[docs/L3-EVIDENCE.md:184](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/docs/L3-EVIDENCE.md:184)

但「沒有截到」不能證明「UI 不可能顯示」；而「every route」也過頭，因為前一段才展示 direct API route。[docs/L3-EVIDENCE.md:189](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/docs/L3-EVIDENCE.md:189)

會改變我看法的條件：

- 把主張縮成「DataHub 0.26.0 的 Columns 與 Documentation 標準頁面不渲染它」。
- 提供前端來源位置，證明 UI 以 current `schemaMetadata.fields` 為主集合，再依 `fieldPath` 合併 editable 描述。
- 加 Playwright 斷言：API 包含唯一 sentinel、current schema 不含舊欄位、標準頁面的可存取 DOM 不含 sentinel。

## B. 其他超過程式碼的主張

- 「`detectors.py` 沒有英文片語清單」可直接反證。D1 有 13 個 `NON_FIELD_QUALIFIERS`，D3 也用英文觸發片語。[README.md:49](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:49)、[src/stilltrue/detectors.py:151](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/detectors.py:151)、[src/stilltrue/detectors.py:393](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/detectors.py:393)  
  會改變我看法：改成「英文詞表不參與具證據的 D1 drift 斷言」，或移除絕對敘述。

- 「write executor 在獨立 credential 後方」不成立。CLI 建立讀取 adapter 與 executor 時都沒有傳入不同 token；兩者使用同一預設連線身分。[README.md:129](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:129)、[src/stilltrue/cli.py:192](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/cli.py:192)、[src/stilltrue/cli.py:242](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/cli.py:242)  
  會改變我看法：實作並驗證兩份權限不同的 credential，或只聲稱模組分離。

- `stilltrue apply <id>` 看似適用所有 finding，實際永遠建立 `dataset_description` proposal。[README.md:38](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:38)、[src/stilltrue/cli.py:203](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/cli.py:203) 因此 undocumented field 與 orphaned field 都沒有正確修復路徑；L3 自己也顯示 orphan finding 在寫回後仍存活。[docs/L3-EVIDENCE.md:137](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/docs/L3-EVIDENCE.md:137)

- `make bench-replay` 不會重生 README 的每個數字；它只跑 `run_bench.py`，另在本機存在 Shopify clone 時跑 Shopify benchmark。[README.md:94](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:94)、[Makefile:28](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/Makefile:28)

- Support boundary 仍說「兩個第三方來源都用於開發」，但上方表格目前列 TLC、HubSpot、Iterable 三個 corpus，下一段又說 Iterable 是 freeze 後才取得。[README.md:185](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:185)、[README.md:239](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:239)、[README.md:332](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:332)

proposal hash 這一項則已修好，舊發現明確作廢。公開文件一致把它稱為內容鎖而非授權邊界。[README.md:142](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:142)、[README.md:324](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/README.md:324)、[docs/L3-EVIDENCE.md:84](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/docs/L3-EVIDENCE.md:84) 程式也真的把 URN、aspect、subject、前後文字、verdict 與 evidence 納入 hash，並在 CLI 寫入前檢查。[src/stilltrue/proposal.py:46](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/proposal.py:46)、[src/stilltrue/cli.py:219](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/cli.py:219)

只有測試名稱還殘留 `Steward approval`／`authorises` 舊稱，屬低風險清理，不是機制缺陷。[tests/test_proposal.py:93](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/tests/test_proposal.py:93)

## C. 單一最高價值缺失

完成 orphaned-doc 的完整工作閉環：

`DataHub 讀取 → Finding → 針對欄位的 migrate／delete proposal → 內容確認 → 寫回 editableSchemaMetadata → 回讀 → 重掃消失`

這比再加一個偵測器更值分，因為它同時補 Impact、Technical Execution、Use of DataHub，以及「Agents That Do Real Work」的賽道對位。目前 `apply` 只會改 dataset description，[src/stilltrue/cli.py:203](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/cli.py:203) Policy Gate 又禁止空白刪除，[src/stilltrue/proposal.py:147](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/proposal.py:147) 所以全案最原創的 finding 目前只能被列出，不能被處理。

未追蹤的 DataHub benchmark 是正確的第一半，但仍只有偵測與報表，沒有修復。[bench/run_orphan_bench_datahub.py:175](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/bench/run_orphan_bench_datahub.py:175)

## D. 原創能力還是 curiosity？

概念上，它是全案最原創的能力；產品完成度上，目前仍偏向「已驗證的 curiosity」。

原創性來自發現 DataHub 兩個 aspect 的生命週期不一致，而不是十幾行集合差：

- editable note 能繼續存在並由 API 讀到。[src/stilltrue/adapter.py:121](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/adapter.py:121)
- 現行 schema 已沒有對應 field。[src/stilltrue/detectors.py:344](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/detectors.py:344)
- 標準欄位檢視與 Agent Context Kit 會漏掉這種狀態。[src/stilltrue/adapter.py:94](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/src/stilltrue/adapter.py:94)

它之所以尚未完全跨過 curiosity 門檻，是因為現在只能發現，不能安全地搬移或刪除孤兒描述，而且 2/2 benchmark 沒測 production read path。四支上游 PR 都已確認仍為 open，這對 Use of DataHub 與生態貢獻是實質加分，但 PR 數量不會替代產品閉環或效度證據。[HANDOFF.md:60](/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel/HANDOFF.md:60) [#18622](https://github.com/datahub-project/datahub/pull/18622)、[#18628](https://github.com/datahub-project/datahub/pull/18628)、[#18630](https://github.com/datahub-project/datahub/pull/18630)、[#49](https://github.com/datahub-project/datahub-skills/pull/49)

驗證結果：`python3 bench/freeze.py --check` 通過；`python3 -m pytest -q` 為 57/57 通過；新 DataHub benchmark 可編譯，但未在本次審查中對外部 DataHub 寫入或跑分。舊版「regex 直接決定 drift、字串相似度猜 rename、120 筆錯 103 筆」的批評已過時；目前問題是新證據閘門仍把近似名稱誤稱為歷史證明。
