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
| `src/stilltrue/adapter.py` | 唯讀 adapter，包 Agent Context Kit 的 5 個讀取工具（get_entities、list_schema_fields、get_lineage、get_dataset_queries、grep_documents）。**Kit 另有 `search`、`search_documents` 未包**——掃描範圍由 URN 清單或 `--limit` 決定，偵測路徑不需要搜尋。寫入工具未 import。含 `authored_description()`：editableProperties 優先、fallback properties |
| `src/stilltrue/evidence.py` | 證據紀錄。欄位：`entity_urn`、`source_function`、`captured_at`、`payload_hash`、`payload`。**`evidence_id` 由「URN + function + payload」內容決定，不含 `captured_at`**——重跑同一觀測產生同一 id，既有引用不會失效；但擷取時間本身有存在紀錄裡（`evidence.py:47` 與 `to_dict()`）。`EvidenceStore` 支援跨命令 hydrate |
| `src/stilltrue/detectors.py` | D1 schema 斷鏈、D1 未文件化欄位、D3 lineage 漂移。全確定性，無 LLM。三態 verdict **皆會產出**：引用解析成功記 CURRENT、有改名候選記 DRIFT、無候選且來自表描述記 INSUFFICIENT_EVIDENCE |
| `src/stilltrue/semantic.py` | D5 語意漂移。確定性預篩 → 注入式判讀器 → 引文閘。模組本身不發網路請求。**未接真實 LLM，未接進 CLI** |
| `src/stilltrue/proposal.py` | Proposal + PolicyGate + `check_approval()`。Gate 擋六類：白名單外 aspect、非 DRIFT verdict、無證據、引用不存在證據、前後相同、清空內容。確認另有一關：`--approve <proposal_hash>`。hash 的 canonical payload 為 `{urn, aspect, subject, before, after, verdict, evidence}` 七項全覆蓋，改任一項即 STALE。**這是內容鎖，不是授權邊界**：不帶身分、不帶簽章，能跑 `apply` 的人自己 dry-run 就拿得到 token |
| `src/stilltrue/executor.py` | 寫前重讀（TOCTOU）、冪等鍵、寫後回讀。VERIFY_FAILED 不自動重試 |
| `src/stilltrue/ledger.py` | append-only JSONL，hash 鏈。verify 可抓內容竄改、刪除、順序調換。**被拒絕的嘗試也入鏈**（NOT_APPROVED / STALE） |
| `src/stilltrue/cli.py` | `stilltrue scan / findings / apply / verify` |
| `Makefile` + `scripts/demo.sh` | `make demo`（全閉環含兩次自動拒寫，可重跑）、`make bench-replay`、`make datahub-up`、`make test` |

## 3. 實測數字

> ⚠️ 兩份第三方資料都是**開發期使用的 benchmark，不是 holdout**。
> 完整時序、哪個 commit 因跑分改了什麼、撤回了哪句宣告：[`VALIDATION-INTEGRITY.md`](VALIDATION-INTEGRITY.md)。

### 第三方 benchmark A：NYC TLC

- 來源：TLC 官方公開 parquet，35 個月全掃描（`bench/oracles/scan_tlc.py`）
- 標籤：兩份已發布 schema 的差集，非人工標註
- 事件：2023-02 `airport_fee` → `Airport_fee`；2025-01 新增 `cbd_congestion_fee`
- 結果：**2/2 偵測，0 誤報**（同一次掃描另記 5 筆 CURRENT）
- 誠信註記：`authored_description()` 因這條掃描回 0 findings 才加（commit `457b190`）

### 第三方 benchmark B：fivetran/dbt_shopify

- 來源：428 commits 的 git 歷史（`bench/oracles/mine_drift_labels.py`）
- 標籤：上游自己修文件的 commit 對
- Tier A 40 筆（IDENTIFIER_CHANGE 10 + DEPRECATION 30），負例 2,496
- 結果：**IDENTIFIER_CHANGE 9/10**；DEPRECATION 6/30，分開報告（30 筆中 17 筆的描述不含任何識別碼，該偵測器結構上不適用）
- **誤報：1,933 筆可跑分負例中 87 筆誤判 DRIFT（4.50%）**。成因單一：描述列舉「值」而非欄位（`in_transit`、`fixed_amount`、反引號括的 `AND`/`OR`），落在欄位描述那條 medium-confidence 分支。此數字原本未量測，第二輪審查指出「只報 recall 不報 precision 等於宣稱了沒寫下來的東西」後補上
- 已知失真：mart 模型用 `select *`，欄位無法從 SQL 原文重建
- 誠信註記：`detectors.py` 的 field-description 分支條件是對著這份跑分結果調的（commit `0757ee3`，理由寫在原始碼註解裡）

### Baseline 對照（同一 benchmark、同一輸入）

| Baseline | Recall | 誤報 |
|---|---|---|
| B0 無 context（只有描述文字） | 0/2 | 0 |
| B1 只看覆蓋率（DataHub 現成能力） | 1/2 | 0 |
| B2 描述 vs schema，大小寫不敏感 | 0/2 | 0 |
| 本作 | 2/2 | 0 |

⚠️ 與 SPEC 3.4 的偏離：SPEC 定的是 `b0_nocontext` / `b1_rules` / `b2_datahub_native`，
其中 b2 才是「DataHub 現成 Quality skill 能做到的部分」。實作把 DataHub 現成能力放在 B1，
B2 換成「大小寫不敏感比對」。B2 對事件 1 依構造必然漏掉——但它不是造來輸的稻草人：
那正是本專案第一版自己犯的 bug，回歸測試還留在 `tests/test_detectors.py`。
**Originality 條款想要的 `b2_datahub_native` 對照目前沒有。**
另：baseline 只跑在分母 2 的 TLC 上，dbt_shopify 的 40 正例／2,496 負例沒有 baseline 對照。

### 真實表誤報

`showcase-ecommerce` 25 張表：schema-break 誤報 0（收緊規則前為 6），14 筆棄權，3 筆 D1_UNDOCUMENTED。
未編輯輸出：`examples/abstention/`。

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

1. **D2 新鮮度漂移** — 無程式碼。官方 `nyc-taxi` datapack 自帶 planted freshness issues 可當開發集，未使用
2. **D4 ownership 漂移** — 無程式碼
3. **D5 未接真實 LLM 判讀器，也未接進 CLI**。硬前提：`showcase-ecommerce` 的 `get_dataset_queries` 回傳 total 為 0，沒有輸入資料
4. **內部 holdout（SPEC 三層資料的 B 層）** — 不存在。開發集只用了 `showcase-ecommerce`，`nyc-taxi` 與 `healthcare` 未使用
5. **凍結程序與 `freeze.json`** — 不存在。SPEC 3.5 的凍結宣告已作廢
6. **`b2_datahub_native` baseline** — 見 §3
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
