# REVIEW — 外部審查：SPEC/ROUTE/BRIEF vs STATUS

> 審查日 2026-07-26，距截止 15 天。僅依目錄內 BRIEF.md / ROUTE.md / SPEC.md / STATUS.md 推導，未用網路與外部工具。`run.log` 僅含一行 bun 警告，無證據價值。
> 本審查引文皆為原文；查不到的標「情報缺口」。

---

## 1. 兌現度：SPEC 六節逐節對照 STATUS

### 1.1 架構（SPEC §1）

**做到的：**

- 三態輸出：SPEC「`DRIFT` / `CURRENT` / `INSUFFICIENT_EVIDENCE`。棄權是合法輸出」↔ STATUS detectors.py「全確定性，無 LLM。三態 verdict」。✅
- 寫前重讀：SPEC 第 4 條「現況 aspect hash ≠ proposal 的 `before_hash` → 轉 `CONFLICT`，不寫」↔ STATUS executor.py「寫前重讀（TOCTOU）」。✅
- 冪等與寫後回讀：SPEC 第 5、6 條 ↔ STATUS「冪等鍵、寫後回讀。VERIFY_FAILED 不自動重試」。✅（冪等鍵是否為 SPEC 的 `SHA256(entity_urn + aspect + proposal_hash)` 公式：**情報缺口**）
- Policy Gate：STATUS proposal.py「擋六類：白名單外 aspect、非 DRIFT verdict、無證據、引用不存在證據、前後相同、清空內容」，對應 SPEC 架構圖的「Policy Gate ├ 封鎖/證據不足」。✅
- 模型拿不到寫入工具：STATUS adapter.py「唯讀 adapter……寫入工具未 import」。方向兌現，但見下。

**做了但與規格不同：**

- **adapter 工具面 5 個 vs 規格 7 個**。SPEC 第 1 條列「`search`、`get_entities`、`search_documents`、`grep_documents`、`list_schema_fields`、`get_lineage`、`get_dataset_queries`」共 7 個；STATUS 只包 5 個（get_entities、list_schema_fields、get_lineage、get_dataset_queries、grep_documents），缺 `search` 與 `search_documents`。
- **evidence_id 定義相反**。SPEC 第 2 條要求 evidence 含「entity URN、來源 function、**擷取時間**、payload hash」；STATUS evidence.py 明寫「id 由內容決定（**不含時間戳**）」。內容定址有其工程理由（冪等），但這是對規格的默改，SPEC 未留這個選項。
- **審批閘形態降級**。SPEC 架構圖有「Steward Review UI ├ reject └ approve(proposal_hash)」與「`edit` 會產生新 proposal hash，舊核准失效」；STATUS 只有 CLI（`sentinel scan / findings / apply / verify`），無 Review UI，也無 proposal_hash 級核准與「edit 使舊核准失效」機制的任何佐證。STATUS §4 的閉環是「apply → Gate passed → 寫回」，人類核可只體現在「人去敲 apply」這一層。ROUTE 3.3 把審批閘列為「缺一件是扣分項」的底線第 1 件，這裡是弱化實作。
- **憑證程序層級分離未證實**。SPEC §1 採 codex 的理由就是「唯一把『讀寫憑證分離』做到**程序層級**」；STATUS 只說寫入工具未 import、executor.py 存在，未提兩個程序、兩份憑證。**情報缺口**，且這是當初選 codex 架構的核心理由。

**沒做到的：**

- 排程器（SPEC 圖第一格「排程器/CLI」的排程半邊）與 SQLite State Store：STATUS 全文未見。題目自述是「**持續**把……拿去對照」（SPEC §0），現況是單發 CLI。

### 1.2 技術選型／模組與資料流（SPEC §2，D1–D5）

| 類 | SPEC 要求 | STATUS 現況 | 判定 |
|---|---|---|---|
| D1 | 斷鏈＋疑似改名＋新增欄位無文件 | detectors.py「D1 schema 斷鏈、D1 未文件化欄位」 | ✅ |
| D2 | 新鮮度漂移「觀測間隔 > 3 × 宣稱週期」 | **全文未提** | ❌ 未實作 |
| D3 | lineage 漂移 | detectors.py「D3 lineage 漂移」 | ✅ |
| D4 | ownership 漂移「僅回報，不自動寫回」 | **全文未提** | ❌ 未實作 |
| D5 | 確定性預篩 → LLM 判讀 → 複驗閘 | semantic.py 有骨架，但「未接真實 LLM 判讀器，也未接進 CLI」（STATUS §6.1），且無輸入資料（§6.6「get_dataset_queries 回傳 total 為 0」） | ⚠️ 半成品，不可運行 |

五類實作了 2.5 類。**更嚴重的是申報問題**：STATUS §6「未完成」列了 D5，**但 D2、D4 既不在模組表、也不在未完成清單**——一份自稱「事實描述」的現況文件對規格的兩整類偵測器保持沉默。這是矛盾點（詳見 §1.7 C2）。

順帶指出：D2 的開發集是現成的——BRIEF 8.5「`nyc-taxi`……planted **freshness** issues」，官方自帶 ground truth，卻未被使用。

### 1.3 證據與 benchmark（SPEC §3）

**做到的：**

- 第三方 holdout H-C3（NYC TLC）：SPEC 3.3 的兩事件（2023-02 大小寫改名、2025-01 新增欄位）↔ STATUS「2/2 偵測，0 誤報」，標籤「兩份已發布 schema 的差集，非人工標註」與 SPEC 的機械標籤主張一致。✅
- 第三方 holdout H-C1（dbt_shopify）：SPEC 3.2 待驗的正負例門檻「正 ≥30、負 ≥100」→ STATUS「Tier A 40 筆……負例 2,496」達標；結果「IDENTIFIER_CHANGE 9/10；DEPRECATION 6/30，分開報告」，且遵守 SPEC 3.4「第三方 holdout 不預設效果門檻」的精神把弱項寫明。✅（逐筆結果與 confusion matrix 是否已放 `examples/`：STATUS 只提「examples/tlc-rename/」一件——**情報缺口，傾向未做**）
- 真實表誤報控制：showcase-ecommerce「schema-break 誤報 0（收緊規則前為 6）」。✅

**沒做到的：**

- **B 層內部 holdout 完全缺席**。SPEC 3.1「B 內部 holdout：自建注入情境，凍結後才跑。功能與五類 recall」、排程 D3–D5 驗收「內部 holdout 五類 recall 有數字」——STATUS 全文無內部 holdout。三層證據結構塌了中間一層。
- **A 層開發集只用了三分之一**：nyc-taxi、healthcare 兩個 datapack（SPEC 3.1 明列）未見使用。
- **指標面大幅縮水**：SPEC 3.4 要求「precision / recall（分 D1–D5）、citation validity、unsupported-claim rate、abstention rate、gate escape、unauthorized mutation、duplicate mutation、audit verify exit code」；STATUS 只報 recall／誤報與 verify 鏈有效。gate escape = 0、引用驗證 100% 是排程 D6–D7 的驗收條件，現況無數字。

**做了但與規格不同：**

- **Baseline 三件套被換掉了**。SPEC 3.4：「`b0_nocontext`（只看描述文字不查 graph）、`b1_rules`（只用確定性訊號無 LLM）、`b2_datahub_native`（DataHub 現成 Quality skill 能做到的部分）。b2 是回答 Originality 條款的直接證據」。STATUS 的表是「B0 無 context／B1 只看覆蓋率（DataHub 現成能力）／B2 描述 vs schema，大小寫不敏感」——b1、b2 定義皆非原規格。B1 是否忠實代表「DataHub 現成 Quality skill 能做到的部分」無從查證（**情報缺口**），Originality 舉證功能弱化。且 B2「大小寫不敏感」對 TLC 事件 1（`airport_fee` → `Airport_fee`）**依構造必然漏掉**——這條 baseline 有「造來輸」的嫌疑，評審追問撐不住。
- **Baseline 只跑在分母 2 的 holdout 上**。表格 Recall 全是 x/2，即只對 TLC 跑；40 正例、2,496 負例的 dbt_shopify 沒有 baseline 對照。統計說服力建立在 n=2。

**凍結宣告——最大的未兌現，見 §1.7 C1。** SPEC 3.5 的宣告原文現況下不可用。

### 1.4 可證明的審計（SPEC §4）

兌現。STATUS ledger.py「append-only JSONL，hash 鏈。verify 可抓內容竄改、刪除、順序調換」＋ §4「`verify` 鏈有效（3 筆）」。規模是 demo 級（3 筆），但機制存在且經 E2E 驗證。這是 SPEC 六節裡兌現最乾淨的一節。

### 1.5 交付形態（SPEC §5）

| 項 | SPEC 要求 | 現況 |
|---|---|---|
| 影片 ≤2:50 | 分鏡含 DataHub 原生頁面 | ❌ 未錄（STATUS §6.2） |
| README 首屏 | 一句話→動圖→三數字→架構→快速開始→證據索引 | 存在（§6.1「README 已標明」）但內容規格達成度**情報缺口** |
| `examples/` | 至少 DRIFT、CURRENT、INSUFFICIENT_EVIDENCE 各一 | ⚠️ 只有 `examples/tlc-rename/` 一件（DRIFT）；CURRENT 與 INSUFFICIENT_EVIDENCE 未見 |
| `make demo` / `make bench-replay` | 一鍵 | 未提及，**情報缺口，傾向未做** |
| repo public + Apache 2.0 About 區可見 | pass/fail 級形式要件 | ❌ private（§6.3），Devpost 未提交（§6.4） |

未錄影、未公開、未提交都在排程 D14–D16 內，不算逾期；但依 BRIEF 4「Judges are not required to test the Project and may choose to judge based solely on the text description, images, and video」，**評審消費面現況接近零**。

### 1.6 排程（SPEC §6）

查核日是排程 D2。對照驗收條件：D1–D9 的內容（adapter、偵測器、gate、executor、ledger）已全數存在，D12（第三方 holdout 評估）、D13（skills PR，STATUS §5 #49 open；另加一條規格外的 datahub 主 repo PR #18622 CI 全綠）也已發生——**進度大幅超前**。

但超前是用**順序倒置**換來的：排程明定「D11 系統凍結 → D12 兩條第三方 holdout **只跑一次；結果不回頭改系統**」，實際是 holdout 先跑、跑分驅動系統迭代（見 C1）。也有跳項：D3–D5 的內部 holdout、D2/D4 偵測器、D10 的 D5 接線都沒做。超前的是量，違背的是這份排程存在的理由——凍結順序。

另有一條時間線疑點：SPEC 定稿 2026-07-25、STATUS 查核 2026-07-26，一天之隔卻出現 8 個 commit、34 個測試、兩條 holdout 全程跑完、E2E 閉環與兩條上游 PR——這個完成量不可能發生在一天內。合理解釋是大量實作先於 SPEC 定稿存在，但如此一來「三路盲延伸後拍板、拍板後動工」的敘事與凍結時序都需要以 repo commit 時間戳重新核對（材料內無此資料，列情報缺口 9）。

### 1.7 STATUS 與 SPEC/ROUTE 的矛盾點（明列）

- **C1（最重）：凍結紀律已被自己的開發過程推翻。** SPEC 3.5 凍結宣告原文：「System code, prompts, policies, and category definitions were **frozen before** the third-party sources were acquired……Holdout outcomes were **not used to modify** the frozen system.」對照 STATUS §7：「描述來源：原僅讀 `properties.description`，**導致 holdout 掃描回 0 findings。改為 editableProperties 優先後修正**」——這是 adapter.py（系統程式碼）的修改，觸發源是 holdout 的輸出；又「dbt_shopify 跑分經**三次修正**……第三次由外部診斷指出」。其中 c1→c2、表層→欄位層、被刪欄位補回三項或可辯稱屬 oracle 端（mine_holdout.py）修正而非系統修正，但 editableProperties 那條無可辯——**系統依 holdout 結果改過了**。STATUS 全文也沒有 freeze.json、沒有凍結時點。結論：SPEC 3.5 的宣告若照原文放進 README，就是可被一次追問戳破的不實陳述，直接撞上評分第 2 條「Does the code do what the submission claims?」。
- **C2：STATUS 的未完成清單不完整。** D2、D4 兩類偵測器未實作卻不在 §6「未完成」六項之列；STATUS §1 把題目重述為「『人寫的描述』與『schema／lineage 現實』」，悄悄比 SPEC §0 的「description、glossary term、**ownership、文件**」窄了兩個名詞。範圍縮水本身可以是合理決策，未申報的縮水是誠實問題。
- **C3：Baseline 定義偏離 SPEC 3.4 且只跑 n=2**（見 §1.3）。
- **C4：adapter 工具 5 個 vs 規格 7 個**（缺 search、search_documents）。
- **C5：Steward Review UI／proposal_hash 核准／edit 失效機制／SQLite State Store／排程器皆無對應物**，審批閘弱化為 CLI apply。
- **C6：evidence_id「不含時間戳」直接違反 SPEC §1 第 2 條的「擷取時間」欄位。**

---

## 2. 路線偏差：對照 ROUTE 預測的得獎形狀

### 2.1 Grand 級三件套逐件核

**第 1 件：第三方 holdout —— 做了，但成色打折。**
真做了兩條，且 ROUTE 3.4 要求的「DataHub 沒提供、你也沒改過的外部來源」「公開分母、逐筆原始結果」在來源選擇與標籤機制上兌現得很好（git oracle 隔離、parquet schema 差集連人工標註都免）。但 ROUTE 3.4 同段的警告原文是：「若『從這批案例學出規則，再拿同批案例證明改善』＝ CASES 敗因 2 的**循環驗證，評審一追問就破**」——C1 顯示 dbt_shopify 這條已部分踩進去：它在開發期被反覆跑、其結果改動了系統程式碼，現在的 9/10 是「迭代後同批重測」，不是凍結後盲測。TLC 那條是否在 adapter 修改前後都跑過、時序如何，STATUS 未載——**情報缺口**。判定：**不是「只是宣稱」，是「真做了但已喪失宣稱『凍結後只跑一次』的資格」**，除非重跑（見 §4）。

**第 2 件：可證明的審計 —— 兌現。**
hash 鏈 + verify + 抓竄改/刪除/順序調換 + E2E 實跑，非宣稱。ROUTE 說這件「與主辦『operational trust』品類論述對位」的敘事價值仍在，但需要 README/影片把它講出來，現況兩者皆無。

**第 3 件：斜角複核 —— 賽前已做，實作端守住了一半。**
題目本身仍站在斜角上（「用 agent 讓 context 保持可信」），未滑回擁擠的 data quality 題。但斜角敘事的兩根支柱在實作端缺席：其一，N4（Pinterest 語意衝突，「the failure mode is silent」——**提問者 Aman Gairola 就是評審**）對應的 D5 是半成品且無輸入資料；其二，ROUTE 候選 A 明定的 Originality 處置「README 與影片明講邊界（『這是開源側的 X；Cloud 的 Context Hub 做的是 Y；我們不做 Y』）」尚無載體。斜角選對了位置，還沒把旗插上去。

### 2.2 其他路線要件

- **L3/L4 綁定：超額兌現。** L3「DataHub 的使用者在原生介面看得到」——STATUS §4 閉環「寫回 DataHub → read-back VERIFIED → 重掃該筆消失」成立（URN 清單與 UI 截圖仍待提交物補上）。L4 不只有 ROUTE 規劃的 skills PR（#49），還多了一條 datahub 主 repo 的 feature PR（#18622，CI 全綠）——超出 ROUTE 與 SPEC 的規劃，是現況最強的一張牌。
- **確定性框架四件（ROUTE 3.3 底線）**：提議/套用分離 ✅、冪等 ✅、明確拒絕權 ✅（三態＋「改為需有改名候選才斷言，其餘棄權」正是拒絕權的實例）、審批閘 ⚠️ 弱化（C5）。ROUTE 說「缺一件是扣分項」，且審批閘那條 ROUTE 特別註明「做出審批閘＝展現懂產品邊界」——這件的缺口有雙重代價。
- **範圍偏差**：題目自述從四種 context 面（description/glossary/ownership/文件）縮到 description×(schema/lineage)。方向沒偏，面積縮了，且未申報（C2）。

---

## 3. 對 BRIEF 評分標準的實際位置

1. **Use of DataHub（tie-break 第一順位）：五條中位置最好。** 「The strongest submissions go beyond reading metadata and contribute back to the graph」——寫回、read-back、重掃消失的閉環是這條款的字面兌現；用了 Agent Context Kit（指定四工具之一，Stage One 無虞）。扣分面：讀取面只用 5/7 工具，search/search_documents 未用，「meaningfully use ... context graph」的覆蓋面（ownership、glossary、documents）縮水。
2. **Technical Execution：中上，但埋著本案最大的雷。** 正面：「actually works end-to-end」有實跑閉環、34 測試、真實 holdout 數字、連 DEPRECATION 6/30 的難看數字都照實分開報——這種誠實正是條款要的。反面：條款的後半句是「Does the code do what the **submission claims**?」——若提交敘述沿用 SPEC 的五類漂移、凍結宣告、審批閘措辭，code 與 claims 之間有 C1/C2/C5 三處裂縫，每一處都經不起評審一問。位置好壞完全取決於敘述是否收斂到已實作範圍。
3. **Originality：中。** 斜角站位仍優（監管 context 自身，非重造既有功能），但兩個舉證器都弱化了：b2_datahub_native 被換成定義可疑的 B1/B2（C3），Cloud Context Hub 邊界聲明未寫。「Building on top of ... is welcome; rebuilding them as if from scratch isn't」——本題不在 rebuild 風險區，但「clearly go beyond」目前靠讀者自行體會，沒有對照證據。
4. **Real-World Usefulness：中上。** 「Would a real data, ML, or AI platform team see clear value」——兩條真實世界 holdout 抓到真實漂移（TLC 2/2、dbt_shopify identifier 9/10）比多數參賽作品的合成 demo 硬。弱點：DEPRECATION 6/30 與「17 筆的描述不含任何識別碼，該偵測器結構上不適用」暴露了對真實文件語料的覆蓋窄；評審席上那位付錢者原型（Aman）最痛的語意衝突題（D5）不可運行。
5. **Submission Quality：五條中最弱，現況接近零。** 影片未錄、README 未定稿、examples 一件、repo private。評審的預設消費方式（BRIEF 4：可以只看文字、圖、影片）意味著這條現在等於整個作品的可見度。排程上這本來就是 D14–D16 的事，不算失職，但 15 天內它從 0 到滿的執行風險，是名次的第一變數。
- **Bonus（開源貢獻）：強。** 兩條 open PR，其中 #18622 對主 repo 且 CI 全綠；條款明寫 fixes 與 skills 都算、SPEC 明寫「不需 merged」。這是超出 ROUTE 樣本推論的加分面。

**最弱的一條：Submission Quality。** 但要區分「最弱」與「最危險」：Submission Quality 弱是排程使然，做了就補上；**最危險的是 Technical Execution 裡 claims 與 code 的裂縫（C1 為首）**——那不是沒做，是做了會被反咬的陳述，補救窗口只在提交前。

---

## 4. 剩餘 15 天最該做的三件事（按對名次的邊際效益排序）

**第 1 件：把評審消費面從零建到滿——影片、README 首屏、examples 補齊、repo public。**
預估工時：4–5 天（examples 補 CURRENT/INSUFFICIENT_EVIDENCE 各一件與 holdout 逐筆結果 1 天；README 首屏含邊界聲明與 L3/L4 綁定證據 1 天；影片分鏡照 SPEC §5 錄製剪輯 2 天，必含「DataHub 原生 entity 頁看到 graph 已更新」與「拒絕權演一次」兩顆鏡頭；repo public + About 區 Apache 2.0 檢查半天）。
不做的代價：影片與 public repo 是提交規格的硬要件，缺一件直接無法有效提交；「Judges ... may choose to judge based solely on the text description, images, and video」——沒有這層，前面所有工程等於評審看不見，名次為零。邊際效益是全表最大的，因為它是從「不可評」到「可評」的一步。

**第 2 件：立即凍結、改寫凍結宣告為誠實版本、兩條 holdout 正式重跑一次。**
做法：現在打 freeze tag + freeze.json；宣告改寫為「開發期曾接觸 holdout 並據以修正（列出三次修正與 editableProperties 事件），於 <日期> 凍結後對兩條 holdout 各正式重跑一次，以下數字以凍結後那一次為準」；重跑逐筆結果進 examples/。
預估工時：1–1.5 天（凍結半天，重跑與逐筆導出半天，宣告與 README 段落半天）。
不做的代價：沿用 SPEC 3.5 原文＝不實陳述，Technical Execution 與 Grand 級「第三方 holdout」主張一問即破（ROUTE 原話：「評審一追問就破」）；連帶污染 Bonus 與 Use of DataHub 建立起來的信任。這件事便宜、可逆性零（提交後無法補救），排第 2 只因第 1 件是存在性門檻。注意時序：**凍結要在任何進一步改碼（含第 3 件）完成後、重跑之前**，故第 3 件的程式碼工作須排在凍結前。

**第 3 件：宣稱與實作對齊——用 nyc-taxi 補上 D2 新鮮度偵測，D4/D5 明文降級。**
做法：D2 是確定性規則（「觀測間隔 > 3 × 宣稱週期」），官方 `nyc-taxi` datapack 自帶 planted freshness issues 當開發集，是五類缺口中投入產出比最高的一類；D4、D5 則在 README「本系統不做什麼／尚未做什麼」段明文降級（D5 已有骨架與注入式判讀器，照實寫「確定性預篩已實作、LLM 判讀未接線、缺真實查詢紀錄輸入」）。
預估工時：2–3 天（D2 偵測器與測試 1.5–2 天，含進 baseline 對照；降級聲明半天）。
不做的代價：提交敘述若保留「五類漂移」而實作只有 2.5 類，就是 Technical Execution 的第二道裂縫；若改為只講 2 類，題目面積縮到「schema diff 工具」附近，Originality 的斜角敘事（context 全面腐化的哨兵）失去支撐。補 D2 後可講「四類實作、一類明文降級」，敘事與程式碼對得上。

三件以外刻意不排的：D5 接真實 LLM（輸入資料缺口未解，STATUS §6.6，15 天內風險大於收益）、Steward Review UI（CLI apply 加一個逐筆確認提示即可堵住審批閘缺口，成本一小時級，可併入第 1 件）、內部 holdout 補建（兩條第三方 holdout 已存在時邊際效益低）。

---

## 情報缺口彙總

1. 讀寫憑證是否做到 SPEC 所採 codex 架構的「程序層級」分離。
2. 冪等鍵是否為 SPEC 的 SHA256 公式；「edit 使舊核准失效」機制是否存在。
3. README 現況內容與 SPEC §5 首屏規格的達成度。
4. `examples/` 除 tlc-rename 外是否已有 holdout 逐筆結果、confusion matrix。
5. TLC 跑分與 adapter（editableProperties）修改的先後時序——決定 TLC 那條 2/2 是否乾淨。
6. `make demo` / `make bench-replay` 是否存在。
7. B1「只看覆蓋率（DataHub 現成能力）」是否忠實代表 DataHub 現成 Quality skill 的能力面。
8. freeze.json 或任何凍結紀錄是否存在（STATUS 未提，推定不存在）。
9. repo commit 時間戳——SPEC 定稿與實作的實際先後（一天內完成 STATUS 所列全部工作不可信，見 §1.6）。
10. PolicyGate 的 aspect 白名單實際內容（只開 description，或含 glossary/tag/domain）——影響 Use of DataHub 的覆蓋面判斷。
