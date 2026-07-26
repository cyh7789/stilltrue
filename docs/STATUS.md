# STATUS v3 — 實作現況

> 事實描述，查核日 2026-07-26。距提交截止 2026-08-10 17:00 EDT 剩 15 天。
> repo：`cyh7789/stilltrue`（private），11 個 commit，42 個測試通過。
> ⚠️ 對外名 **StillTrue**，但**程式碼內套件名與 CLI 仍是 `stilltrue`**，尚未統一。

## 1. 題目與賽道

偵測 DataHub 裡「人寫的描述」與「schema／lineage 現實」脫節之處，附證據提出修正，
操作者在 CLI 明示確認 proposal hash 後寫回 graph。投賽道 Agents That Do Real Work。
⚠️ **尚未驗證確認者是否為獨立 steward**——無身分、無簽章、無權限分離，見 §2 與 §6.9b。

**範圍已縮**：SPEC §0 原寫「description、glossary term、ownership、文件」四面，
實作只涵蓋 description × (schema / lineage)。ownership 與文件面未做（見 §6）。

## 2. 已實作模組

| 模組 | 內容 |
|---|---|
| `adapter.py` | 唯讀 adapter。Kit 的 5 個讀取工具 + 兩個 Kit 拿不到的：`schema_changes()` 讀 DataHub timeline（Kit 無此工具）、`authored_field_descriptions()` 讀 editable 欄位描述（Kit 會丟掉，見上游 PR #18628）。寫入工具未 import |
| `evidence.py` | 證據紀錄，內容定址 id，含 `captured_at` |
| `detectors.py` | **全部改為證據閘門，零英文詞組清單**。`vanished_fields()` 讀 DataHub 變更帳本並用現況 schema 過濾掉位置比對造成的假改名；`detect_schema_break()` 只在有改名候選或帳本記錄離開時斷言；`detect_orphaned_docs()` 比對 editable 描述與現況 schema；`detect_lineage_drift()` |
| `semantic.py` | D5，未接真實 LLM 也未接 CLI（`get_dataset_queries` 全庫回 0） |
| `proposal.py` | Proposal + PolicyGate + `check_approval()`（內容鎖，非授權邊界） |
| `executor.py` | 寫前重讀、冪等鍵、寫後回讀 |
| `ledger.py` | hash 鏈，拒絕事件也入鏈 |
| `cli.py` | `stilltrue scan / findings / apply / verify` |

## 3. 實測數字

| 偵測器 | 語料 | 結果 | 身分 |
|---|---|---|---|
| schema break | NYC TLC 41 個月真實發布歷史 | **41/41** 月精確正確、0 誤報 | 開發 benchmark |
| orphaned doc | dbt_hubspot | **4/4**、432 負例 0 誤報 | 開發驗證 |
| orphaned doc | **dbt_iterable** | **2/2**、199 負例 0 誤報 | **凍結 holdout，單跑** |

凍結流程：選源規則先 commit → 受評 6 檔先 hash → 16 個候選機械淘汰 → 只跑一次。
`python3 bench/freeze.py --check` 可驗。

⚠️ **兩個誠實註記**：holdout 只有 2 個正例，證明機制可轉移不證明比率；
選源門檻仍用舊 oracle 評估（算文件編輯數），規則凍結在前所以照套，分母只有 2 就是這個不一致的顯影。

**舊的三個 dbt 語料數字已撤下**：標籤量的是「描述後來被編輯」，
`dbt_shopify` 10 筆正例裡 9 筆的被引用 token 在漂移窗兩端都不是該 model 的欄位。

## 4. 端到端閉環（已實際執行，非 dry-run）

`make demo` 全流程：scan（2 drift、5 current）→ 無 token 寫入遭**自動拒寫**（NOT_APPROVED）→
拿 A 文字的 token 改寫 B 文字遭**自動拒寫**（STALE）→ 正當確認 → 寫回 DataHub →
read-back VERIFIED → 重掃該筆消失（`airport_fee` 由 DRIFT 轉 CURRENT）→
`verify` 鏈有效（10 筆，含兩次拒寫）。

⚠️ 兩次都是**系統依規則自動拒絕**，不是人主動 reject。**steward 主動否決的路徑沒有端到端實測**，
`CONFLICT`、重複套用回原收據、`VERIFY_FAILED` 三條失敗路徑也沒有（見 §6.18）。

未編輯輸出：`examples/tlc-rename/`。

## 5. 上游貢獻

| PR | repo | 狀態 |
|---|---|---|
| #18622 `feat(agent-context): expose description resolution for read paths` | datahub-project/datahub | open，CI 全綠 |
| #49 `feat: add datahub-context-drift skill` | datahub-project/datahub-skills | open |

## 6. 未完成／未實作（完整清單）

**規格定了但沒做：**

1. **D2 新鮮度漂移** — 無程式碼，且**已測定在可得資料上做不出來**（`D2-FEASIBILITY.md`）：
   76 張表中 0 筆描述宣稱更新週期；`get_entities` 不回傳任何時間戳；
   `get_dataset_assertions(FRESHNESS)` 全庫 0 筆；`datasetProperties.lastModified` 有 26 筆但那是
   datapack 建置時間。**BRIEF §8.5 記的 `nyc-taxi` datapack 不在官方 registry**——
   `datahub datapack load nyc-taxi` 回 `Unknown data pack`，registry.json 只有 bootstrap 與 showcase-ecommerce
2. **D4 ownership 漂移** — 無程式碼
3. **D5 未接真實 LLM 判讀器，也未接進 CLI**。硬前提：`showcase-ecommerce` 的 `get_dataset_queries` 回傳 total 為 0，沒有輸入資料
4. **內部 holdout（SPEC 三層資料的 B 層）** — 不存在。開發集只用了 `showcase-ecommerce`，`nyc-taxi` 與 `healthcare` 未使用
5. ~~**凍結程序與 `freeze.json`**~~ — **已完成**，見 §3。SPEC 3.5 的舊凍結宣告仍作廢（它宣稱的是兩份開發 benchmark）
6. **`b2_datahub_native` baseline** — 已測定開源版無對應能力可對照，改以 `NATIVE-COMPARISON.md` 舉證，見 §3
7. **SQLite State Store、排程器** — 不存在。現況是單發 CLI，不是「持續」執行
8. **Steward Review UI** — 不存在。核准是 CLI 的 `--approve <hash>`，非圖形介面
9. **程序級讀寫憑證分離未證實** — adapter 沒 import 寫入工具、executor 是獨立模組，但**沒有兩個程序、兩份憑證的實作**。SPEC §1 採 codex 架構的核心理由（唯一做到程序層級隔離）目前不成立
9b. **核准的授權邊界未做** — `--approve` 只證明呼叫者持有該內容的 token，不證明是誰確認、何時確認、確認權是否與寫入權分離。要成立需要「executor 可驗證但不可簽發」的核准收據（綁完整 canonical payload + 確認者身分 + 時間），並在 ledger 分別記錄 proposer／approver／executor
10. **完整指標面** — 只報 recall／誤報／verify 鏈。citation validity、unsupported-claim rate、abstention rate、gate escape、duplicate mutation 等無數字

**提交物：**

11. demo 影片未錄
12. repo 為 private，未轉 public
13. Devpost 表單未提交
14. L3 可見證據未產出：DataHub UI 截圖／錄影 + 受影響 URN 清單
15. README 首屏無 20 秒動圖（SPEC §5.2 要求）

**已知失真：**

16. `mine_drift_labels.py` 對 mart 模型的 schema 重建不完整
17. 審計鏈末筆無外部錨點——同時改末筆並重算其 hash 的攻擊，`verify` 抓不到。是 tamper-evident，不是 tamper-proof
18. 失敗路徑缺端到端實測：steward 主動 reject、`CONFLICT`（寫前重讀發現值已變）、重複套用回傳原收據、`VERIFY_FAILED`。四條都有程式碼，都沒有實跑紀錄

## 7. 開發過程中修正的判斷

- 描述來源：原僅讀 `properties.description`，導致 TLC benchmark 掃描回 0 findings。改為 editableProperties 優先後修正，並回饋上游 PR #18622
- D1 誤報：原本所有無法解析的識別碼都報 DRIFT，25 張表產生 6 個誤判。改為需有改名候選才斷言，其餘棄權
- dbt_shopify 跑分經三次修正（schema 取 c1 → 取 c2；描述掛表層 → 掛欄位層；被刪欄位的描述遭丟棄 → 補回），第三次由外部診斷指出
- 凍結宣告：原訂原文放進提交物，經兩份外部審查指出不成立後撤回（非改寫），並補 `VALIDATION-INTEGRITY.md` 記錄時序
- 核准機制：原本 `proposal_hash` 的 docstring 寫「核准綁定此值」但無任何程式碼執行它，人類核准實際只等於「有人去敲 apply」。已補 `check_approval()`
- 三態：D1／D3 原本靜默略過解析成功的引用，CURRENT 只有未接線的 D5 會產生。已改為記錄
- 用詞降級：`--approve` 原稱 steward approval，經第二輪審查指出它只是內容鎖無授權邊界，全數改為 confirmation，並在 README 加 Support boundary 節
- finding id 不可重現：`referenced_identifiers` 回傳 set，id 依位置編號，set 迭代順序隨 `PYTHONHASHSEED` 每個 process 變動。同一輸入連續三次重生 examples 得到三個不同 id。已在兩處迭代點加 `sorted()`，回歸測試跨五個 hash seed 的子程序驗證
