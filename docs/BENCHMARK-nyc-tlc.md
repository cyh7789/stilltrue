# 第三方 Benchmark 設計 — NYC TLC Trip Records

> ⚠️ 本文原題為「第三方 Holdout 設計」。開發過程中系統程式碼依此來源的跑分結果修改過，
> 因此它是**第三方 benchmark，不是 holdout**。§6 的凍結宣告已撤回。
> 事實時序：[`VALIDATION-INTEGRITY.md`](VALIDATION-INTEGRITY.md)。

> 驗證日 2026-07-25，由主 session 執行（盲跑 agent 無網路，三路 SPEC 均把此項標為情報缺口或改用主辦提供的 datapack 代替）。
> 對應 SKILL.md Grand 級三件套第 1 件：「找一個你沒碰過的未改動外部系統／公開資料集／學術基準當驗證集 — 自建情境集只到 $1K-3K 級」。

## 1. 為什麼需要它

三路盲延伸的 SPEC 對 holdout 的處理：

| 路 | 選用的 holdout | 問題 |
|---|---|---|
| codex | `showcase-ecommerce` datapack（1,049 entities） | 主辦提供，非第三方；且該 SPEC 自承「BRIEF 沒提供既有 drift gold labels，人工 gold 的一致性是情報缺口」，需單一 steward 手工標註 100 筆 |
| duo | `healthcare` datapack（planted quality issues） | 主辦提供；planted 的是資料品質問題，不是「文件與現實脫節」 |
| claude | 待補 | — |

兩路都退回主辦提供的資產，因為盲跑禁止檢索。兩者都不滿足「未改動的外部系統」，且都需要人工建立 ground truth。

## 2. 來源與可及性（已實測）

| 資產 | URL | 驗證結果 |
|---|---|---|
| TLC 官方 data dictionary（Yellow） | `https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf` | HTTP 200 |
| 實際資料檔（月度 parquet） | `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_<YYYY-MM>.parquet` | HTTP 200 |

兩者由紐約市政府與 TLC 發布，公開下載，不需認證。DataHub 官方 `nyc-taxi` datapack 使用的即是這份資料來源（BRIEF §8.5：「NYC Yellow Taxi Trip Records（約 500k trips）」），因此評審對資料集本身有既有認識，但本 benchmark 使用的是**原始來源**，不是主辦包裝過的 datapack。

## 3. 已驗證的真實漂移（實測，非推論）

以 `pyarrow.parquet.read_schema` 讀取三個月份的實際檔案：

| 月份 | 欄位數 | airport 相關欄位 | 新增欄位 |
|---|---|---|---|
| 2023-01 | 19 | `airport_fee`（小寫 a） | — |
| 2024-06 | 19 | `Airport_fee`（**大寫 A**） | — |
| 2025-01 | 20 | `Airport_fee` | `cbd_congestion_fee` |

兩類漂移同時存在：

1. **靜默改名**：同一語意欄位在 2023→2024 之間把 `airport_fee` 改成 `Airport_fee`。任何寫死小寫欄位名的文件、查詢、transformation 都會在不報錯的情況下失效——這正是主辦品類論述所述「Context problems don't announce themselves as context problems」的字面實例。
2. **未文件化的新增**：2025-01 出現 `cbd_congestion_fee`（曼哈頓擁擠費，2025-01-05 上路），既有描述與 glossary 不會提到它。

## 4. 相對於前述兩個 datapack 的三個優勢

1. **真第三方、未改動**：漂移由 TLC 自己造成，發生在本專案存在之前，不可能被我們的偵測邏輯反向設計。
   ⚠️ 但這只擋掉一半的循環驗證：**事件本身**沒被反向設計，**偵測規則**卻是對著這份結果調的
   （見 §6 與 [`VALIDATION-INTEGRITY.md`](VALIDATION-INTEGRITY.md)）。要完全擋掉需要凍結程序。
2. **ground truth 機械可驗證，不需人工標註**：期望答案由兩個月份的 parquet schema 差集直接算出，不依賴單一 steward 的主觀判斷。codex SPEC 中「人工 gold 一致性」的情報缺口在此不存在。
3. **評審可一鍵重現**：兩個 URL 加一段 `read_schema` 即可獨立複驗，不需要跑我們的系統。

## 5. 使用方式

- **開發集**：官方 `nyc-taxi`、`healthcare`、`showcase-ecommerce` datapack（BRIEF §8.5 明示 safe for Apache 2.0 submissions），用於功能開發與五類漂移的 recall 調校。
- **第三方 benchmark**：TLC 原始來源。原訂「系統全部凍結後才第一次載入」，實際未照此執行——
  見 §6。

建置步驟：

1. 以 **2023-01** 的實際 schema + TLC 官方 dictionary 當時的敘述，在 DataHub 建立「人寫的 context」（dataset description、欄位描述、glossary term）。
2. 以 **2025-01** 的實際檔案當「資料現實」載入，並保留 2024-06 作為中間點。
3. 期望輸出（由 schema 差集機械導出，先凍結後執行）：
   - `airport_fee` → `Airport_fee`：既有描述指向已不存在的欄位名
   - `cbd_congestion_fee`：現實中存在、context 中缺席
   - 其餘 18 個欄位：無漂移（陰性對照，用於量測誤報率）
4. 分母公開：20 個欄位中 2 個應偵測、18 個應保持沉默。誤報率與召回率同時可算。

## 6. 凍結宣告——已撤回

這一節原本放著一段準備原文貼進提交物的宣告，內容是「系統程式碼、prompt、policy、
分類定義在取得 TLC 來源前已全部凍結」與「holdout 結果未用於修改已凍結的系統」。

**那段陳述不成立，已刪除而非改寫。** `authored_description()` 就是因為 TLC 掃描回
0 findings 才加的（commit `457b190`），同一個 commit 的 D1 收緊規則也拿 TLC 的 2/2
當驗收條件。完整時序與 commit 證據見 [`VALIDATION-INTEGRITY.md`](VALIDATION-INTEGRITY.md)。

可保留的只有標籤來源這半句：

> Expected labels were derived mechanically from the published parquet schemas of
> 2023-01 and 2025-01, not authored by the project team.

這句仍為真——任何人跑 `bench/oracles/scan_tlc.py` 都會得到同樣兩個事件，不需要跑本專案。
但它證明的是「標籤不是我們編的」，不是「系統沒看過答案」。後者需要凍結程序，本專案尚未做。

## 7. 完整漂移事件清單（2023-01 至 2025-11 全掃描，已完成）

以 HTTP range read 讀取每月 parquet footer 的 schema（不需下載完整檔案；`fsspec` + `pyarrow.parquet.read_schema`），逐月比對前一月欄位集合。掃描腳本與輸出：`tlc-drift-events.json`。

35 個月中僅兩次 schema 變動：

| # | 月份 | 事件 | 型態 |
|---|---|---|---|
| 1 | **2023-02** | `airport_fee` → `Airport_fee` | 大小寫靜默改名（欄位總數不變，19→19） |
| 2 | **2025-01** | 新增 `cbd_congestion_fee` | 未文件化的新欄位（19→20） |

2025-12 於掃描日尚未發布（FileNotFoundError），屬正常發布延遲。

**這份清單即 benchmark 的分母**：

- 正例 2 筆（應偵測）
- 陰性對照 33 個月無事件（測誤報率）；欄位層級：20 個欄位中 18 個橫跨三年未變
- 兩個正例分屬不同漂移型態（改名 vs 新增），可分別計分

事件 1 的價值特別高：改名只差一個字母大小寫，TLC 未發布公告，任何寫死 `airport_fee` 的文件、查詢或 transformation 都會在不報錯的情況下失效。這是「Context problems don't announce themselves as context problems」的字面實例，也是本題偵測器最該抓到的一類。

## 8. 尚待確認

TLC data dictionary PDF 的**歷史版本**是否可取得（用以佐證「文件當時怎麼寫」）。目前只驗證了現行版本可下載。若取不到歷史版，則以 2023-01 的實際 schema 作為 context 基準寫入 DataHub，並在報告中揭露此替代方式——不影響上述兩個事件的機械可驗證性。
