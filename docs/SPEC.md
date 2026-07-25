# SPEC 定稿 — Context Drift Sentinel

> 合成自三路盲延伸（`runs/spec-{codex,claude,duo}-SPEC.md`，三路網路呼叫皆為 0）+ 主 session 補的第三方 holdout 驗證。
> 定稿日 2026-07-25。截止 2026-08-10 17:00 EDT ＝ 台北 2026-08-11 05:00，剩 16 天。
> 三路原稿保留不動；本檔只記**採用哪一套與為什麼**，細節指回原稿。

## 0. 題目與賽道

**Context Drift Sentinel**：一個 agent 持續把 DataHub graph 裡「人寫的 context」（description、glossary term、ownership、文件）拿去對照「資料與查詢的實際行為」，找出已經與現實脫節的條目，附證據提出修正並寫回 graph，套用與否由 steward 保留否決權；判斷工作流另以 skill 發布回 datahub-skills。

**賽道：Agents That Do Real Work**（三路一致，無分歧）。claude 的駁論最完整：賽道原文「reads DataHub... takes action, and writes results back so the next person or agent inherits the knowledge」幾乎是本題規格書；Stage One 是 pass/fail 的主題貼合檢查，措辭最貼近的賽道風險最低；不投 Metadata-Aware Code Gen（產出物不活在 Git PR）、不投 Production ML Agents（TOPIC 不含 ML 面，硬加是敘事拼貼）、不投 Wildcard（有精確對位賽道時投 Wildcard 等於放棄對位優勢）。

## 1. 架構模式 — 採 codex

控制流與安全機制以 codex 版為準（原稿 §1.1–1.4），理由：三路中唯一把「讀寫憑證分離」做到程序層級，且每一步都有可機械驗證的失敗態。

```
排程器/CLI → Deterministic Orchestrator → Read-only DataHub Adapter → MCP Server → Context Graph
                                        → Normalizer + Snapshot Diff → Deterministic Detectors
                                        → Single Proposal Agent → Policy Gate
                                          ├ 封鎖/證據不足 → Rejected or Abstained
                                          └ 通過 → SQLite State Store → Steward Review UI
                                                    ├ reject → State Store
                                                    └ approve(proposal_hash) → Write Executor → MCP
                                                                              → Read-back Verifier
所有階段 → Immutable Artifact Store → Hash-chained Audit Ledger
```

必守的六條（逐條來自 codex §1.2）：

1. **模型拿不到寫入能力**：Orchestrator 程序只載入唯讀憑證，adapter 只暴露 `search`、`get_entities`、`search_documents`、`grep_documents`、`list_schema_fields`、`get_lineage`、`get_dataset_queries`。寫入憑證只注入獨立的 Executor 程序。
2. **每個事實句綁證據**：Proposal 的每一句都必須引用既有 `evidence_id`（含 entity URN、來源 function、擷取時間、payload hash）。
3. **三態輸出**：`DRIFT` / `CURRENT` / `INSUFFICIENT_EVIDENCE`。棄權是合法輸出，不是失敗。
4. **寫前重讀**：Executor 寫入前重讀 entity，現況 aspect hash ≠ proposal 的 `before_hash` → 轉 `CONFLICT`，不寫。
5. **冪等**：`idempotency_key = SHA256(entity_urn + aspect + proposal_hash)`；同 key 已有成功收據就回傳原收據。
6. **寫後回讀**：Read-back Verifier 重讀同 aspect，內容 hash 符合 `after_hash` 才轉 `VERIFIED`；不一致轉 `VERIFY_FAILED`，**不自動重試**。

`edit` 會產生新 proposal hash，舊核准失效——這條擋掉「核准後偷改內容」的攻擊面。

## 2. 漂移分類 — 採 duo 的 D1–D5

duo 原稿 §3.2 的五類是三路中唯一可直接實作的分類學：

| 類 | 名稱 | 人寫側訊號 | 現實側訊號 | 偵測方式 |
|---|---|---|---|---|
| D1 | schema 斷鏈 | 描述/文件引用的欄位名 | `list_schema_fields` + 跨輪 diff | 確定性：引用欄位已不存在；同 diff 內出現同型別新欄位 → 標「疑似改名」；新增欄位無文件 |
| D2 | 新鮮度漂移 | 描述宣稱的更新週期 | entity 最後更新時間戳 | 確定性：觀測間隔 > 3 × 宣稱週期 |
| D3 | lineage 漂移 | 描述宣稱的來源表 | `get_lineage` 上游集合 | 確定性：宣稱來源不在上游；上游已 deprecated 仍被引用 |
| D4 | ownership 漂移 | ownership aspect 與描述中的團隊名 | owner urn 能否解析為現存使用者 | 確定性；**僅回報，不自動寫回** |
| D5 | 語意/glossary 漂移 | 同一 term 掛在多 entity 的定義文字 | 各 entity 的 sample queries 過濾邏輯 | 確定性預篩（term 掛 ≥2 entity 且 WHERE 邏輯不同）→ LLM 判讀，強制兩側引文 + 複驗閘 |

D5 直接取自 BRIEF §9.5 的 Pinterest 原文（Finance 與 Marketing 的 DAU 定義不同，「the failure mode is silent」）——提問的人是本場評審 Aman Gairola。

**LLM 只出現在 D5 的判讀**，D1–D4 全確定性。這守住 SKILL 3.3 的底線要求。

## 3. 證據與 benchmark — 採 claude 的三層 + 主 session 補的具體來源

### 3.1 三層資料

| 層 | 來源 | 用途 |
|---|---|---|
| A 開發集 | 官方 datapack `nyc-taxi`、`healthcare`、`showcase-ecommerce` | 功能開發與 D1–D5 召回調校。BRIEF §8.5 明示 safe for Apache 2.0 |
| B 內部 holdout | 自建注入情境，凍結後才跑 | 功能與五類 recall。**不冒充第三方泛化證據**（codex 原稿用語） |
| C 第三方 holdout | 見 3.2、3.3 | Grand 級主張的唯一依據 |

### 3.2 第三方 holdout H-C1：`fivetran/dbt_shopify`（已驗證）

claude 給了四條可測條件並明說「不憑印象指名 repo」，主 session 執行其候選程序後選定：

| 條件 | 要求 | 實測（2026-07-25） |
|---|---|---|
| 授權公開 | Apache/MIT/BSD | apache-2.0 ✅ |
| description 數 | ≥ 50 | `models/shopify.yml` 單檔 **592** ✅ |
| git 歷史 | ≥ 12 個月、≥ 200 commits | **428 commits**、2020-08→2026-07 ✅ |
| 正負例 | 正 ≥30、負 ≥100 | 待 `mine_holdout.py` 執行（D2 驗證） |

**標籤機制**（claude 原稿 §7.1）：挖 commit 對——`c1` 改了 model SQL 但沒改對應 yml description；`c2` 才補上文件。`c1..c2` 之間該 description 即 `drift=true`，類別由 diff 型態機械判定。**送進系統時只搬 `c1` 時點狀態進 DataHub，系統看不到 git**——git 只是 oracle 產地，agent 拿不到，天然防作弊。

額外優勢：該 repo `models/rest/` 與 `models/graphql/` 兩套並存，正處遷移期，文件落後現實的密度高。

### 3.3 第三方 holdout H-C3：NYC TLC（已驗證，完整清單見 `HOLDOUT-nyc-tlc.md`）

35 個月全掃描（HTTP range read 讀 parquet footer，不需下載完整檔），僅兩次 schema 變動：

| # | 月份 | 事件 | 對應偵測類 |
|---|---|---|---|
| 1 | 2023-02 | `airport_fee` → `Airport_fee`（大小寫靜默改名，欄位數不變） | D1 前半（疑似改名） |
| 2 | 2025-01 | 新增 `cbd_congestion_fee` | D1 後半（新增欄位無文件） |

分母：正例 2、陰性對照 33 個月無事件、欄位層級 18/20 橫跨三年未變。

**這條的獨有價值**：期望標籤由兩個月份的 parquet schema 差集機械算出，**連人工標註都不需要**——codex 原稿在 §4.2 自承的「人工 gold 一致性是情報缺口」在此不存在。且評審用兩個 URL 加一段 `read_schema` 就能獨立複驗，不必跑我們的系統。

兩條 holdout 互補：H-C1 測「文件 vs 程式碼」漂移，H-C3 測「文件 vs 資料」漂移。

### 3.4 對照組與指標

三個 baseline（claude 原稿）：`b0_nocontext`（只看描述文字不查 graph）、`b1_rules`（只用確定性訊號無 LLM）、`b2_datahub_native`（DataHub 現成 Quality skill 能做到的部分）。b2 是回答 Originality 條款的直接證據——證明這不是重造已出貨功能。

指標：precision / recall（分 D1–D5）、citation validity、unsupported-claim rate、abstention rate、gate escape、unauthorized mutation、duplicate mutation、audit verify exit code。**第三方 holdout 不預設效果門檻**（codex 原稿：「以免看到自然標籤後移動門柱」），公開實際分母、confusion matrix 與逐筆結果。

### 3.5 凍結宣告（提交時原文入 README）

> System code, prompts, policies, and category definitions were frozen before the third-party sources were acquired. Expected labels were derived mechanically (NYC TLC: published parquet schemas; dbt_shopify: the upstream project's own documentation-fix commits), not authored by the project team. Holdout outcomes were not used to modify the frozen system.

## 4. 可證明的審計 — 三路一致

hash 鏈 append-only ledger（JSONL）+ `verify` 命令。claude 的加成論述可直接用進 README：主辦品類論述明寫 context graph 優化的是「**operational trust**」，可證明的審計就是把他們的抽象名詞做成可執行的東西。

## 5. 交付形態

evaluator 消費順序固定（規則明寫評審可只看文字與影片）：

1. **影片 ≤2:50**（codex 原稿 §5.1 的分鏡最完整）：開場放一段仍宣稱舊 schema 的 DataHub context 與衝突證據 → scan 顯示 claim-citation proposal → Review UI 比對 before/after 並核准 → **回到 DataHub 原生 entity 頁看到 graph 已更新** → `audit verify` 顯示 root hash → 三層資料與 baseline 的同分母結果
2. **README 首屏**：一句話 → 20 秒動圖 → 三個結果數字 → 架構 → 三行快速開始 → 證據索引
3. **`examples/`**：至少一件 DRIFT、一件 CURRENT、一件 INSUFFICIENT_EVIDENCE 的完整輸出（規則的 Optional 條款，讓評審免跑程式即可驗貨）
4. **一鍵**：`make demo` / `make bench-replay`

## 6. 排程（16 天，倒推自 8/11 05:00 台北）

| 期間 | 交付 | 驗收 |
|---|---|---|
| D1–D2 | 環境 + read-only adapter + Normalizer/證據紀錄 | 能對 `showcase-ecommerce` 產出帶 evidence_id 的快照 |
| D3–D5 | D1–D4 確定性偵測器 + 內部 holdout 凍結 | 內部 holdout 五類 recall 有數字 |
| D6–D7 | Proposal Agent + Policy Gate + 三態輸出 | gate escape = 0；引用驗證 100% |
| D8–D9 | Write Executor + 冪等 + read-back + hash 鏈 ledger | `verify` exit 0；重複寫入 0 |
| D10 | D5 語意漂移（唯一用 LLM 的一類） | 強制兩側引文，複驗閘通過 |
| D11 | **系統凍結**（code/prompt/policy/分類定義 + freeze.json） | 凍結宣告可機械核對 |
| D12 | 兩條第三方 holdout 各跑一次正式評估 | 只跑一次；結果不回頭改系統 |
| D13 | skill 整理 + PR 發到 `datahub-project/datahub-skills` | PR 連結可引用（不需 merged） |
| D14 | 影片錄製 | ≤2:50，含 DataHub 原生頁面畫面 |
| D15 | README/描述定稿 + examples 補齊 | 引用逐條核原文 |
| D16 | repo 轉 public + Devpost 送出 | About 區 Apache-2.0 可見；**不勾 Feedback 獎**（與其他獎互斥） |

## 7. 斜角複核（Grand 三件套第三件）

問題：這題是主流形還是他們想對外講的故事？

**是後者，證據三條**：
1. 官方 Learning Center 的文章標題就是「Continuous Context: **Why Your AI Documentation Is Already Lying to You**」——他們花錢做內容行銷在講這件事，開源側零工具。
2. 官方部落格（作者 Nick Adams，本場評審）列的四類 agent 是 Analytics / Quality / Steward / Engineering，本題是**第五類：維護 context 本身的 agent**，落在條款明文放行的 extend/compose 區，不是 rebuild。
3. 三路盲跑在補上企業敘事層後**獨立收斂到同一家族**，兩路取了相同題名。

**Originality 風險與處置**：Cloud 版 Context Hub 有「內建 evaluations」。處置＝README 與影片明講邊界（「這是開源側的 X；Cloud 的 Context Hub 做的是 Y；我們不做 Y」）。依產品展示賽決勝變數，講清邊界本身即加分。

## 8. 開工前未解

1. `mine_holdout.py` 對 `fivetran/dbt_shopify` 的正負例產出量待實測（D2 驗證，不過門檻就換候選）
2. TLC data dictionary 的歷史版本可及性未確認；取不到則以 2023-01 實際 schema 當 context 基準並在報告揭露
3. D2 新鮮度偵測所需的「entity 最後更新時間戳」來源欄位名，需在 D1 環境搭起來後定案（duo 原稿列為情報缺口 1）
