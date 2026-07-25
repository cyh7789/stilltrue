# STATUS v2 — 實作現況

> 事實描述，查核日 2026-07-26。距提交截止 2026-08-10 17:00 EDT 剩 15 天。
> repo：`context-drift-sentinel`，8 個 commit，34 個測試通過。

## 1. 題目與賽道

Context Drift Sentinel：偵測 DataHub 裡「人寫的描述」與「schema／lineage 現實」脫節之處，附證據提出修正，經核准後寫回 graph。

投賽道 Agents That Do Real Work。

## 2. 已實作模組

| 模組 | 內容 |
|---|---|
| `src/sentinel/adapter.py` | 唯讀 adapter，只包 Agent Context Kit 的 5 個讀取工具（get_entities、list_schema_fields、get_lineage、get_dataset_queries、grep_documents）。寫入工具未 import。含 `authored_description()`：editableProperties 優先、fallback properties |
| `src/sentinel/evidence.py` | 證據紀錄，id 由內容決定（不含時間戳）；`EvidenceStore` 支援跨命令 hydrate |
| `src/sentinel/detectors.py` | D1 schema 斷鏈、D1 未文件化欄位、D3 lineage 漂移。全確定性，無 LLM。三態 verdict |
| `src/sentinel/semantic.py` | D5 語意漂移。確定性預篩 → 注入式判讀器 → 引文閘。模組本身不發網路請求 |
| `src/sentinel/proposal.py` | Proposal + PolicyGate。擋六類：白名單外 aspect、非 DRIFT verdict、無證據、引用不存在證據、前後相同、清空內容 |
| `src/sentinel/executor.py` | 寫前重讀（TOCTOU）、冪等鍵、寫後回讀。VERIFY_FAILED 不自動重試 |
| `src/sentinel/ledger.py` | append-only JSONL，hash 鏈。verify 可抓內容竄改、刪除、順序調換 |
| `src/sentinel/cli.py` | `sentinel scan / findings / apply / verify` |

## 3. 實測數字

### 第三方 holdout A：NYC TLC

- 來源：TLC 官方公開 parquet，35 個月全掃描（`bench/oracles/scan_tlc.py`）
- 標籤：兩份已發布 schema 的差集，非人工標註
- 事件：2023-02 `airport_fee` → `Airport_fee`；2025-01 新增 `cbd_congestion_fee`
- 結果：**2/2 偵測，0 誤報**

### 第三方 holdout B：fivetran/dbt_shopify

- 來源：428 commits 的 git 歷史（`bench/oracles/mine_holdout.py`）
- 標籤：上游自己修文件的 commit 對
- Tier A 40 筆（IDENTIFIER_CHANGE 10 + DEPRECATION 30），負例 2,496
- 結果：**IDENTIFIER_CHANGE 9/10**；DEPRECATION 6/30，分開報告（30 筆中 17 筆的描述不含任何識別碼，該偵測器結構上不適用）
- 已知失真：mart 模型用 `select *`，欄位無法從 SQL 原文重建

### Baseline 對照（同一 holdout、同一輸入）

| Baseline | Recall | 誤報 |
|---|---|---|
| B0 無 context（只有描述文字） | 0/2 | 0 |
| B1 只看覆蓋率（DataHub 現成能力） | 1/2 | 0 |
| B2 描述 vs schema，大小寫不敏感 | 0/2 | 0 |
| Context Drift Sentinel | 2/2 | 0 |

### 真實表誤報

`showcase-ecommerce` 25 張表：schema-break 誤報 0（收緊規則前為 6），剩 3 筆 D1_UNDOCUMENTED 彙總。

## 4. 端到端閉環（已實際執行，非 dry-run）

scan → 2 findings → apply → Gate passed → 寫回 DataHub → read-back VERIFIED → 重掃該筆消失 → `verify` 鏈有效（3 筆）。

未編輯的輸出存於 `examples/tlc-rename/`。

## 5. 上游貢獻

| PR | repo | 狀態 |
|---|---|---|
| #18622 `feat(agent-context): expose description resolution for read paths` | datahub-project/datahub | open，CI 全綠 |
| #49 `feat: add datahub-context-drift skill` | datahub-project/datahub-skills | open |

## 6. 未完成

1. D5 未接真實 LLM 判讀器，也未接進 CLI（README 已標明）
2. demo 影片未錄
3. repo 為 private，未轉 public
4. Devpost 表單未提交
5. `mine_holdout.py` 對 mart 模型的 schema 重建不完整
6. D5 需要真實查詢紀錄才有輸入；showcase-ecommerce 的 `get_dataset_queries` 回傳 total 為 0

## 7. 開發過程中修正的判斷

- 描述來源：原僅讀 `properties.description`，導致 holdout 掃描回 0 findings。改為 editableProperties 優先後修正
- D1 誤報：原本所有無法解析的識別碼都報 DRIFT，25 張表產生 6 個誤判。改為需有改名候選才斷言，其餘棄權
- dbt_shopify 跑分經三次修正（schema 取 c1 → 取 c2；描述掛表層 → 掛欄位層；被刪欄位的描述遭丟棄 → 補回），第三次由外部診斷指出
