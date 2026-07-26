---

## StillTrue — 評審報告（第三輪，全部重讀）

> 所有前兩輪的發現均已作廢，不重複。以下完全基於現有程式碼。

---

### A. 攻擊證據

#### A1. 41/41 TLC — 這是 41 個決策，還是 1 個決策穿著 41 件衣服？

**結論：這個批評有實質，但 README 的說法基本上站得住腳——只是說法不夠精確。**

讀 `bench/oracles/replay_tlc.py` 的 `expected_state()`（第 55–62 行）：

```python
def expected_state(month: str) -> set[str]:
    referenced = set(re_ids(DESCRIPTION))
    gone: set[str] = set()
    for e in EVENTS:
        if e["month"] <= month:
            gone |= set(e["removed"])
    return gone & referenced
```

`DESCRIPTION` 是一個常數字串。`EVENTS` 是一個靜態 JSON 檔。`expected_state` 對每個月份的計算結果是：

- 2023-01：`{}` （空集合）
- 2023-02 到 2026-05：`{'airport_fee'}` （固定集合）

所以 41 個月的「正確答案」只有兩種值：空集合或 `{'airport_fee'}`。這確實是 **2 個不同的決策類型**，重複 39 次。

**但這個批評的力道有限，原因如下：**

1. 每個月都要對 DataHub 做真實的 API 呼叫（`scan()` 函式，第 73–80 行），讀取真實的 schema 和 timeline。如果 DataHub 的 timeline API 在某個月回傳雜訊（例如 `vanished_fields()` 的 positional-diff 誤報問題，`detectors.py` 第 88–103 行有詳細說明），detector 就會在那個月出錯。41/41 代表 41 次真實 API 呼叫都沒有被雜訊污染。
2. `cbd_congestion_fee` 在 2025-01 出現，但它不在 `DESCRIPTION` 裡，所以它不進入 `expected_state`——這是正確的，因為 `detect_schema_break` 只檢查「描述裡提到但 schema 沒有的欄位」，而不是「schema 有但描述沒提到的欄位」（那是 `D1_UNDOCUMENTED`）。這個邊界是正確的，但 REPLAY-REPORT.md 說「兩件事發生了」，卻只有一件事進入 `expected_state`——這個不一致沒有在報告裡說清楚。

**什麼會改變我的看法：** 如果 `expected_state` 在 2025-01 之後也包含 `cbd_congestion_fee` 的某種斷言，那 41/41 就真的是 41 個不同的決策。現在它不包含，所以 39 個月的答案是同一個集合。

**扣分風險：中等。** 評審如果仔細讀 `expected_state` 就會發現這點。README 說「41 consecutive decisions, not two」是技術上正確的（每次都要呼叫 API、每次都可能出錯），但「not two」這個說法會讓人以為有 41 種不同的正確答案，實際上只有 2 種。**建議修正說法**：「41 次連續的 API 呼叫，每次都必須正確——其中 39 次的正確答案是同一個集合，2 次是空集合。」

---

#### A2. 2/2 凍結 holdout — `VALIDATION-INTEGRITY.md` 承認的是不是真正的問題？

**結論：`VALIDATION-INTEGRITY.md` 承認了一個較小的問題，但真正的問題在 `HOLDOUT-orphan-iterable.md` 裡有誠實記錄，只是沒有在 README 的 Evidence 表格裡充分呈現。**

`HOLDOUT-orphan-iterable.md` 第 26–30 行：

> **One inconsistency, recorded rather than smoothed over.** The selection rule's `mined_positives >= 30` threshold is evaluated by `select_holdout.py` using the *previous* oracle, which counts documentation edits rather than orphaned documentation. The rule was frozen before this round and applied mechanically, so it stands as written; but it means the threshold that admitted `dbt_iterable` measured something other than what was then scored. The consequence is visible in the denominator: 2 positives, not 30.

這才是評審真正會質疑的點：**選擇 `dbt_iterable` 的門檻（`mined_positives >= 30`）是用舊 oracle 算的，而舊 oracle 量的是「描述被編輯過」，不是「欄位消失後描述還在」。** 所以「這個 repo 有 30 個正例」這個前提是假的——它只有 2 個真正的正例。

`VALIDATION-INTEGRITY.md` 主要在討論 TLC 和 dbt_shopify 的問題，對 holdout 的說明只有最後一段，而且那段說的是「freeze 機制本身是好的」，沒有正面說明「選擇標準用了錯誤的 oracle」這件事。

**什麼會改變我的看法：** 如果 README 的 Evidence 表格在 `2/2` 旁邊加一句「選擇門檻用舊 oracle 評估，實際正例數為 2 而非 30」，這個問題就被充分揭露了。

**扣分風險：高。** 評審看到 `2/2, 0 false alarms on 199` 會以為這是一個有 30+ 正例的 holdout，實際上只有 2 個。這是最容易被質疑的數字。

---

#### A3. Freeze 機制 — 雜湊六個檔案是否真的防止了 tuning-on-holdout？

**結論：有一條路徑可以繞過 freeze，但它需要主動作弊，而且 `VALIDATION-INTEGRITY.md` 已經承認了更嚴重的問題。**

`bench/freeze.py` 凍結的六個檔案（第 35–42 行）：

```python
FROZEN_FILES = [
    "src/stilltrue/detectors.py",
    "src/stilltrue/adapter.py",
    "src/stilltrue/evidence.py",
    "bench/oracles/replay_tlc.py",
    "bench/oracles/mine_orphaned_docs.py",
    "bench/run_orphan_bench.py",
]
```

**沒有被凍結的檔案：**
- `bench/oracles/mine_drift_labels.py`（被 `mine_orphaned_docs.py` import）
- `bench/oracles/build_tlc_benchmark.py`（定義 `DESCRIPTION` 和 `COLUMN_DOCS`）
- `bench/oracles/scan_tlc.py`（定義哪些月份算 drift event）
- `bench/freeze.json` 本身（可以被覆寫後重新 freeze）

理論上的繞過路徑：修改 `mine_drift_labels.py` 的 `sql_columns_at` 或 `yml_columns_at` 來改變什麼算正例，然後重新跑 `bench/freeze.py` 更新 freeze.json——六個被凍結的檔案都沒動，但 oracle 的行為變了。

**但這個攻擊的實際威力有限：**
1. `mine_orphaned_docs.py` 是被凍結的，它 import `mine_drift_labels.py`，但 `mine_drift_labels.py` 的邏輯（`sql_columns_at`、`yml_columns_at`）是純 git 操作，很難在不讓人看出來的情況下作弊。
2. `VALIDATION-INTEGRITY.md` 已經承認了比這更嚴重的問題：TLC 結果直接改變了程式碼。

**什麼會改變我的看法：** 把 `mine_drift_labels.py` 也加入 `FROZEN_FILES`。

**扣分風險：低。** 這是理論漏洞，不是實際問題。

---

#### A4. `docs/L3-EVIDENCE.md` — 「UI 看不到」用缺席作為證明，這個論證站得住腳嗎？

**結論：論證本身是合理的，但需要一個可重現的步驟才能讓評審自己驗證。**

`docs/L3-EVIDENCE.md` 的論證結構（第 97–110 行）：

> The note is in the graph: [curl 指令] ... And it is on none of the four screenshots above ... because the UI renders descriptions per *current* field, and a field that is gone has nothing to render into.

這個論證是：
1. API 可以讀到這個 note（有 curl 指令）
2. 四張截圖都看不到它
3. 因此 UI 無法顯示它

**問題：** 「四張截圖都看不到它」是必要條件，不是充分條件。截圖可能只是沒有滾動到正確位置，或者 filter 設定遮住了它。論證需要一個正面的機制說明，而不只是缺席。

**但 `detectors.py` 的 docstring 提供了機制說明**（第 218–228 行）：

> DataHub does not clean it up, and the UI cannot show it -- there is no column left to render it on. It is still in the graph, so every agent reading the catalog is handed documentation for a field that does not exist. Verified end to end on a quickstart: document two columns, drop one, and its description is still there afterwards.

這個說明是正確的：DataHub UI 的 Columns tab 是按 `schemaMetadata.fields` 渲染的，`editableSchemaMetadata` 裡的孤兒描述沒有對應的 schema field 可以掛載，所以不會出現。這是 DataHub 的架構決定，不是 bug。

**什麼會改變我的看法：** 在 `L3-EVIDENCE.md` 加一個步驟：「在 quickstart 上重現：`curl` 讀到 note → 截圖 Columns tab → 確認看不到 → 這就是機制」。現在這個步驟在 `make demo` 裡，但沒有在 L3 文件裡明確連結。

**扣分風險：低。** 評審如果跑 `make demo` 就能自己驗證。

---

### B. 聲明超出程式碼的地方

逐行讀 `README.md` 和 `docs/L3-EVIDENCE.md`，找到以下問題：

#### B1. `proposal_hash` 的說法是否一致？

`README.md` 第 113–116 行（Design 段落）：

> *This is a content lock, not an authorisation boundary.* It proves the write matches a text that was displayed and confirmed; it does not prove a separate reviewer did the confirming, and anyone who can run `apply` can read the token off a dry run.

`docs/L3-EVIDENCE.md` 第 57–60 行：

> This is content binding, not an authorisation boundary — it establishes *what* was approved, not *who* approved it. See the support boundary in `README.md`.

`README.md` Support Boundary 段落（第 175–179 行）：

> **The confirmation token is a content lock, not an authorisation boundary.** `--approve <hash>` proves the write matches a text that was displayed and confirmed. It carries no identity, no signature and no privilege separation: whoever can run `apply` can obtain the token from a dry run.

**這三個地方說法一致，沒有矛盾。** 沒有任何地方暗示「steward 批准」的概念。這個問題在前兩輪可能存在，現在已經修正。**前兩輪的這個發現已作廢。**

#### B2. D5 的說法

`README.md` 第 37–39 行：

> D1 and D3 run in `stilltrue scan`. **D5 is implemented but not yet wired into the CLI**: its judge is injected rather than built in, so the module itself makes no network calls and can be tested against a fake.

這個說法是準確的。`src/stilltrue/semantic.py` 存在但沒有被 CLI 呼叫。沒有問題。

#### B3. Evidence 表格裡的 `4/4` dbt_hubspot

`README.md` Evidence 表格：

> | **orphaned doc** | `fivetran/dbt_hubspot` | **4/4**, 0 false alarms on 432 | development |

這個數字沒有對應的 `bench/HOLDOUT-REPORT.md` 或類似文件可以讓評審驗證。`VALIDATION-INTEGRITY.md` 提到 dbt_hubspot 是 holdout v2，但那是針對 schema break detector，不是 orphaned doc detector。**這個 4/4 的來源不清楚。**

**什麼會改變我的看法：** 一個 `bench/HOLDOUT-orphan-hubspot.md` 或類似文件，說明 4/4 是怎麼算出來的。

**扣分風險：中等。** 評審可能會問「這個 4/4 在哪裡可以驗證？」

---

### C. 最高價值的缺失項目

**最高價值的缺失：orphaned doc detector 在 DataHub 上的端對端展示。**

目前的情況：
- `detect_orphaned_docs` 在 dbt git repo 上有 benchmark（`bench/run_orphan_bench.py`），用 git history 作為 oracle
- `docs/L3-EVIDENCE.md` 展示了 DataHub quickstart 上的 orphaned doc 案例
- 但這兩件事沒有連在一起：**沒有一個端對端的展示，從 DataHub 讀到 `editableSchemaMetadata` 孤兒描述，跑 `detect_orphaned_docs`，產生 Finding，然後寫回修正**

`adapter.py` 的 `authored_field_descriptions()` 方法（第 82–86 行）確實讀取 `editableSchemaMetadata`，而且 `detect_orphaned_docs` 確實被呼叫（在 `L3-EVIDENCE.md` 的 scan output 裡可以看到 `D1_ORPHANED_DOC airport_fee`）。但 `examples/` 目錄裡沒有一個完整的 orphaned doc 修復流程範例，對應 `examples/tlc-rename/` 的完整度。

這個缺失的影響：評審看到 `D1_ORPHANED_DOC` 的 Finding，但看不到「修復孤兒描述」的完整流程——是刪除那個描述？還是更新它？`apply` 指令對 orphaned doc 的行為是什麼？

---

### D. `detect_orphaned_docs` — 最原創的東西，還是好奇心？

**結論：這是最原創的東西，而且有具體的技術基礎。**

理由：

1. **DataHub 的架構造成了這個問題，而且沒有任何介面能顯示它。** `schemaMetadata` 和 `editableSchemaMetadata` 是兩個獨立的 aspect，pipeline 只更新前者，UI 只渲染後者裡有對應 schema field 的描述。這不是 bug，是設計——但設計的副作用是孤兒描述永遠不會被任何人看到。

2. **Agent Context Kit 讓問題更嚴重。** `adapter.py` 第 68–80 行的 docstring 說明：Kit 的 `list_schema_fields` 只讀 `schemaMetadata.fields`，不讀 `editableSchemaMetadata`，所以一個用 Kit 建的 agent 連孤兒描述的存在都不知道。`detect_orphaned_docs` 是唯一能找到它的路徑。

3. **這不是「好奇心」的原因：** 孤兒描述會被 `authored_description()` 讀到（如果它在 dataset 層級），或者被任何直接讀 `editableSchemaMetadata` 的工具讀到——包括 LLM agent。一個 agent 讀到「`airport_fee`: Only charged on LGA and JFK pickups」，然後去查 schema，發現沒有這個欄位，就會產生幻覺或錯誤的推論。這是一個真實的 agent 安全問題，不只是文件整潔問題。

4. **DataHub 的四個 upstream PR 中，`#18622` 和 `#18630` 都和這個問題相關**（`list_schema_fields` 不回傳 editable descriptions，以及 schema 從未被 ingest 的 dataset 會 crash）。這說明這個問題是真實的，而且上游也認可。

**唯一的保留：** `detect_orphaned_docs` 的邏輯極其簡單（`detectors.py` 第 218–240 行，實際邏輯只有 10 行）。它的原創性在於**發現了這個問題**，而不在於解決問題的技術複雜度。評審如果只看程式碼行數可能會低估它。

---

### 總結排名（依扣分風險）

| 排名 | 問題 | 扣分風險 | 修正方式 |
|---|---|---|---|
| 1 | `2/2` holdout 的選擇門檻用了錯誤的 oracle，實際正例只有 2 個，不是 30 個 | **高** | README Evidence 表格加一句說明 |
| 2 | `4/4` dbt_hubspot orphaned doc 沒有對應的可驗證報告 | **中** | 加 `bench/HOLDOUT-orphan-hubspot.md` |
| 3 | 41/41 的說法「not two」會讓人誤以為有 41 種不同的正確答案 | **中** | 修正說法，說明 39 個月的正確答案是同一個集合 |
| 4 | orphaned doc 沒有完整的端對端修復範例 | **中**（Impact 分項） | 加 `examples/orphaned-doc/` |
| 5 | `mine_drift_labels.py` 沒有被 freeze 覆蓋 | **低** | 加入 `FROZEN_FILES` |
| 6 | L3 的「UI 看不到」論證缺少可重現步驟 | **低** | 加一個 quickstart 重現步驟 |

**前兩輪的所有發現均已作廢。** 程式碼已經完全重寫，舊的批評（regex phrase list、string similarity、false positive 問題）都不再適用。
