# 第三方 Holdout 挖掘報告

> 執行日 2026-07-25。來源：`fivetran/dbt_shopify`（Apache-2.0，428 commits，2020-09→2026-06）。
> 挖掘器：`mine_holdout.py`。輸出：`holdout-dbt-shopify.jsonl`。

## 為什麼標籤不是我們標的

drift 由上游專案自己造成，標籤來自**上游自己補文件的那個 commit**：

- 事件 A（`c1`）：描述處於與現實脫節的狀態
- 事件 B（`c2`）：維護者修正了該描述

`c1..c2` 之間即 drift 窗口。送進受測系統時只搬 `c1` 時點的狀態，系統看不到 git。

## 結果

| 類別 | 筆數 | 判定依據 | 分層 |
|---|---:|---|---|
| `IDENTIFIER_CHANGE` | 10 | 描述中反引號包住的識別碼集合改變 | **Tier A** |
| `DEPRECATION` | 30 | `c2` 出現 deprecat* 而 `c1` 沒有 | **Tier A** |
| `SEMANTIC` | 179 | 其餘實質語意改寫 | Tier B |
| 濾除 | 112 | 純錯字、潤稿、精確化補述 | — |
| 負例（描述橫跨全歷史未變動） | 2,496 | | — |

**主 benchmark 只用 Tier A（40 筆）+ 負例（2,496 筆）。** Tier B 另行報告，不計入主要 precision/recall。

## 過濾器做了什麼（兩輪迭代，逐輪記錄）

初版把「描述被改過」一律當正例，抽驗立刻發現雜訊：

| 抽驗樣本 | 判定 |
|---|---|
| `total_discount_shop_currency_code`：「ISO å4217」→「ISO 4217」 | ❌ 純錯字，濾除 |
| `async_usage_count`：「被使用的次數」→「(DEPRECATED) 此欄位現在回傳 null」 | ✅ 真漂移 |
| `unique_key`：surrogate key 從 `order_id, name` 改為 `order_id, key` | ✅ 真漂移 |
| `name`：補上「Deprecated in favor of `key`」 | ✅ 真漂移 |

第二輪抽驗 SEMANTIC 類，發現一個大族群是**批次補上「in shop currency」**：

| 樣本 | 判定 |
|---|---|
| `subtotal_net_refunds`：「...扣除退款」→「...扣除退款 **in shop currency**」 | ❌ 精確化，濾除 |
| `avg_quantity_net`：數量欄位也被補上「(in shop currency)」 | ❌ 精確化，且補得不正確（數量無幣別） |
| `discounts.title`：「price rule 的標題，用於 admin 搜尋」→「折扣的顯示名稱」 | ✅ 真語意變更 |

第二輪加入規則：舊描述整段保留、只多一小段補充（< 40 字元）→ 視為精確化，不計漂移。濾除數 68 → 112。

## 誠實聲明（提交時寫入 README）

1. **不再繼續調整過濾器**。再往下調就變成調參到數字好看。Tier B 的 179 筆未逐筆人工驗證，其中混有精確化與真漂移，比例未知——因此不計入主要指標。
2. 主 benchmark 的分母公開：Tier A 正例 40、負例 2,496。
3. 過濾器本身是機械規則，程式碼在 `mine_holdout.py`，任何人可重跑複驗。

## 與 NYC TLC holdout 的分工

| Holdout | 測什麼 | 正例 | 標籤來源 |
|---|---|---:|---|
| `fivetran/dbt_shopify` | 文件 vs 程式碼的漂移 | 40（Tier A） | 上游自己的修正 commit |
| NYC TLC | 文件 vs 資料的漂移 | 2 | 兩個月份 parquet schema 的差集 |

兩者都不需要我方標註。
