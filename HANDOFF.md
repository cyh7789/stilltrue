# StillTrue（Build with DataHub: The Agent Hackathon）— 接手紀錄

> 更新 2026-07-26（第二輪審查後）。截止 2026-08-10 17:00 EDT ＝ 台北 8/11 05:00，剩 15 天。
> 前身 Serow / Blast-Radius Guard 已封存（`cyh7789/blast-radius-guard`，archived）。
> 本作是重做，不複用舊程式碼。

## 一句話

偵測 DataHub 裡「人寫的描述」與「schema／lineage 現實」脫節之處，附證據提出修正，
經核准後寫回 graph。投賽道 Agents That Do Real Work。

對外名、套件名、CLI 命令均為 **stilltrue**（repo `cyh7789/stilltrue`，private）。

## 為什麼是這題（決策依據）

r2 三路盲跑（補上企業敘事層後）獨立收斂到同一家族，duo 與 claude 甚至取了相同題名。
關鍵斜角一句話（claude ROUTE）：**別人做「用 context 讓 agent 變可靠」，
得獎的形狀是「用 agent 讓 context 保持可信」。**

差異化錨點：官方 Learning Center 有篇文章叫
「Continuous Context: Why Your AI Documentation Is Already Lying to You」，
而開源側零工具。`/datahub-audit` 那族（5 個競爭 PR）測的是「還沒寫什麼」，
本作讀「已經寫好的」並檢查是否還成立。

## 現況

8 commit、34 測試綠。模組：adapter（唯讀 5 工具）、evidence（內容定址 id）、
detectors（D1/D3 確定性）、semantic（D5，判讀器注入式）、proposal + PolicyGate、
executor（寫前重讀／冪等／寫後回讀）、ledger（hash 鏈）、cli。

實測數字：
- NYC TLC：2/2，0 誤報（2023-02 `airport_fee`→`Airport_fee`、2025-01 新增 `cbd_congestion_fee`）
- fivetran/dbt_shopify：IDENTIFIER_CHANGE 9/10；DEPRECATION 6/30（結構上不適用，分開報）
- showcase-ecommerce 25 表：schema-break 誤報 0（收緊前 6）
- baseline：B0 無 context 0/2、B1 覆蓋率 1/2、B2 大小寫不敏感 0/2、本作 2/2
- 端到端閉環已實際執行（非 dry-run），證據在 `examples/tlc-rename/`

上游 PR（L4）：
- datahub-project/datahub **#18622** — 公開 `resolve_description()`，CI 全綠
- datahub-project/datahub-skills **#49** — `datahub-context-drift` skill

## 待辦

**已完成（2026-07-26）**：凍結 + 凍結後 holdout 單跑、Originality 證據、D2 結案。

1. ~~D2 新鮮度偵測~~ — **測定做不出來**，已結案（`docs/D2-FEASIBILITY.md`）。
   76 張表 0 筆描述宣稱更新週期、`get_entities` 不回傳時間戳、assertion 全庫 0 筆、
   `nyc-taxi` datapack 不在官方 registry。硬做等於自己寫題目自己改考卷。
2. ~~凍結 + 新 holdout~~ — **已完成**。`dbt_fivetran_log` 13/32（41%），誤報 9.59%。
   對照開發集的 90% / 4.50%：recall 腰斬、誤報翻倍。兩類失敗刻意不修。
3. ~~Originality 證據~~ — **已完成**（`docs/NATIVE-COMPARISON.md`）。

**剩下唯一一件：提交消費面**（約 4 天，效益最大，也是最弱的一條）
- 影片 2 天。素材現成：demo 的 NOT_APPROVED / STALE 兩顆鏡頭、`airport_fee` 由 DRIFT 轉 CURRENT
- README 首屏已改成 holdout 41% 打頭；還缺 L3 可見證據（URN 清單 + DataHub UI 截圖）
- repo 轉 public + About 區 Apache-2.0 檢查
- Devpost 送件。**不要勾** Feedback Survey 獎——與其他獎互斥

⚠️ **凍結已生效**。再動 `detectors.py` / `adapter.py` / `evidence.py` /
`mine_drift_labels.py` / `run_shopify_bench.py` 任一個，`bench/freeze.py --check` 就會紅，
holdout 那 41% 的可信度跟著沒了。要改就得重跑整條凍結流程換新來源。

## 四份審查（都在 repo 裡）

`docs/REVIEW-r1-{codex,duo}.md`、`docs/REVIEW-r2-{codex,duo}.md`。
第二輪讓兩路各自複核自己第一輪的發現——`captured_at` 那個誤判就是由犯錯的那一路自己撤回的。

⚠️ **派 duo 的兩個前置條件**（踩過兩次才發現）：工作目錄必須是 git repo（`git init` + 一次 commit），
且必須存在 `.claude/rules/` 目錄，否則初始化就靜默死掉，run.log 只留一行 bun 警告。

## 第二輪的關鍵判定

| 項目 | 判定 |
|---|---|
| 凍結宣告撤回 | **誠實面已關閉**（duo：「教科書等級」）；證據面仍空，需第 2 項 |
| 第三方 holdout | **仍是空的**，不是打折——揭露不會把 benchmark 變回 holdout |
| `--approve` 核准閘 | 關掉「核准後偷換內容」（質變），**沒關掉核准者身分**。已把用詞全數降級 |
| CURRENT 三態 | 補足宣稱，不是湊規格 |
| 最弱 | **Submission Quality**，仍接近零 |
| 最危險 | 從 Technical Execution 換成 **Originality**——唯一一條目前拿不出任何肯定證據的 |

Originality 危險的理由：`b2_datahub_native` 對照不存在、D5 停擺後「第五類 agent」只剩敘事。
評審席上坐著 Nick Adams（四類 agent 清單作者）與 Maggie Hays（DataHub Founding PM），
「這跟我們現成的 Quality skill 差在哪」是他們職務上必然會問的，而現在的答案是空白。

## 開發中踩過的坑（別再犯）

1. **DataHub 有兩個描述欄位**：`properties`（ingestion）與 `editableProperties`（UI／API），
   UI 顯示後者。只讀前者導致掃描回 0 findings，追三輪才發現。已抽成
   `authored_description()`，並回饋上游 PR #18622。
2. **不要把兩側都 lower() 再比對**：那會抹掉大小寫改名這個要抓的訊號。
   第一版就是這樣寫的，TLC 測試抓到。
3. **`__pycache__` 殘留**會讓修正看起來沒生效，白追三輪。
4. **benchmark 難在重建「那個時間點的世界」**：dbt_shopify 跑分連錯三次
   （schema 取 c1 而非 c2；描述掛表層而非欄位層；被刪欄位的描述遭丟棄）。
   第三次是外部診斷指出的，紀錄在 `docs/DIAGNOSIS-shopify-scoring.md`。
5. **卡關要派 duo 診斷**，不要自己硬修——我自己修兩輪都沒修到點上。
6. **set 迭代順序隨 PYTHONHASHSEED 變**：finding id 依位置編號，examples 連續三次重生
   拿到三個不同 id。同一個 process 內測不出來，回歸測試要跨子程序跑不同 seed。
7. **只報 recall 不報 precision 等於宣稱了沒寫下來的東西**：dbt_shopify 的 2,496 筆負例
   躺在標籤檔裡從沒跑過，補測是 4.5% 誤報（87/1,933），成因是描述列舉「值」而非欄位。

## 相關路徑

| 內容 | 位置 |
|---|---|
| 本專案 | `/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel` |
| 賽事情報基地 | `/Volumes/CyhSSD/Hackathon/active/datahub/` |
| BRIEF v2（含企業敘事層） | 同上 `BRIEF-v2.md` |
| 三路 r2 盲跑 ROUTE | 同上 `runs/r2-{codex,claude,duo}-ROUTE.md` |
| SPEC 定稿 | 同上 `SPEC-FINAL.md`（= 本專案 `docs/SPEC.md`） |
| 現況事實檔 | 同上 `STATUS-v2.md` |
| dbt_shopify clone | scratchpad，compact 後可能已清，需重 clone |
