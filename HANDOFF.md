# StillTrue（Build with DataHub: The Agent Hackathon）— 接手紀錄

> 更新 2026-07-26。截止 2026-08-10 17:00 EDT ＝ 台北 8/11 05:00，剩 15 天。
> 前身 Serow / Blast-Radius Guard 已封存（`cyh7789/blast-radius-guard`，archived）。
> 本作是重做，不複用舊程式碼。

## 一句話

偵測 DataHub 裡「人寫的描述」與「schema／lineage 現實」脫節之處，附證據提出修正，
經核准後寫回 graph。投賽道 Agents That Do Real Work。

對外名 **StillTrue**（repo `cyh7789/stilltrue`，private）。
⚠️ 程式碼內套件名與 CLI 仍是 `sentinel`，提交前要統一。

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

## 待辦（順序已與阿毛確認）

1. **修 holdout 的說法**（約 1h，誠信問題）
   codex review 指出：兩份第三方資料都在開發過程被反覆執行，其中一輪還改到
   `detectors.py`，因此**不構成凍結 holdout**。要改稱 benchmark，並揭露修正歷程。
   涉及 README.md、bench/REPORT.md、bench/SHOPIFY-REPORT.md、docs/HOLDOUT-nyc-tlc.md。

2. **D5 接真 LLM 判讀器 + 真查詢資料**
   硬前提：showcase-ecommerce 的 `get_dataset_queries` 回傳 total 為 0，沒有輸入。
   **設 8 小時停損**：取不到真實查詢資料就砍 D5，範圍縮成 D1/D3，
   同時移除 Pinterest 語意衝突那段敘事，不留宣稱。
   不做的代價（codex 原話）：容易被評為「規則式 schema／lineage linter」。

3. **補一份真正凍結的第三方 benchmark**（前兩項完成、系統穩定後才凍結）
   先產出 `freeze.json`（code／規則／prompt／分類定義 hash），再取新來源，只跑一次，
   不因結果改碼。找不到合格來源就刪掉「holdout」與凍結宣告，不換詞掩飾。

4. **L3 可見證據**：DataHub UI 截圖／錄影 + URN 清單，逐筆可對。
   ROUTE 對 L3 的驗收不是「有寫回」而是「UI 上看得到」。

5. **影片、轉 public、Devpost 送件**（最後三天）
   提交時**不要勾** Feedback Survey 獎——與其他獎互斥。

## 待收

duo 的對照 review（`/private/tmp/dh-review/duo/REVIEW.md`）。第一次靜默死掉已重派。
codex 那份在 `/private/tmp/dh-review/codex/REVIEW.md`，結論摘要見下。

## codex review 的關鍵判定

| 項目 | 判定 |
|---|---|
| 題目／賽道 | 沒有偏離 ROUTE |
| 可證明的審計 | **已兌現** |
| 第三方 holdout | **未兌現**（見待辦 1、3） |
| 斜角複核 | 只兌現一半——D5 不能跑，最強敘事沒有 demo |
| 最弱評分項 | **Submission Quality**：現在還不是可評審的提交物 |

一句要記住的：**「資源投入明顯偏向程式與 benchmark，judge-facing 證據落後。」**
這與當初盲批對 Serow 的批評同構——同一個坑踩了兩次。

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
