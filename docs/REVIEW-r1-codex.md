# 外部審查報告

> 審查基準：只使用 `BRIEF.md`、`ROUTE.md`、`SPEC.md`、`STATUS.md`。`STATUS.md` 被視為現況事實來源；本報告未檢查實作 repo、PR 內容、README 或執行測試，因此凡 `STATUS.md` 未交代者一律標為「情報缺口」。

## 結論

Context Drift Sentinel 沒有換題，已做出最重要的讀取、提議、閘門、寫回、回讀與 hash 鏈閉環，也已有兩件上游 PR。就目前材料，這是一個有競爭力的 Challenge Winner 候選雛形，但還不是可成立的 Grand 級提交。

Grand 三件套中，「可證明的審計」已在實作層兌現；「斜角複核」仍成立，但最能證明斜角的 D5 語意漂移尚未接上真實 LLM、真實查詢紀錄與 CLI；「第三方 holdout」則沒有按 SPEC 的凍結與單次執行規則兌現。`dbt_shopify` 經三次跑分修正，不能再稱為未碰過的 holdout。現況最弱的評分項是 Submission Quality：影片未錄、repo 仍為 private、Devpost 未提交，依 BRIEF 的提交條款，現在甚至還不是可供正式評審的提交物。

## 1. SPEC 六節兌現度

### 1.1 架構

**已做到**

- 唯讀端、證據、提議、閘門、執行、回讀與審計的主要骨架已存在。SPEC 要求「Read-only DataHub Adapter」、「Policy Gate」、「Write Executor」、「Read-back Verifier」與「Hash-chained Audit Ledger」；STATUS 列出 `adapter.py`、`evidence.py`、`proposal.py`、`executor.py`、`ledger.py`，並明載 executor 有「寫前重讀（TOCTOU）、冪等鍵、寫後回讀。VERIFY_FAILED 不自動重試」。
- 三態輸出已做到。SPEC 要求「`DRIFT` / `CURRENT` / `INSUFFICIENT_EVIDENCE`」；STATUS 對 `detectors.py` 的原文是「全確定性，無 LLM。三態 verdict」。
- 寫前重讀、冪等與寫後回讀三項安全條件已有對應實作。SPEC 的要求分別是 aspect hash 衝突時不寫、相同 `idempotency_key` 回傳既有收據、回讀不符時轉 `VERIFY_FAILED` 且不自動重試；STATUS 對 `executor.py` 的描述逐項對得上，且端到端紀錄為「寫回 DataHub → read-back VERIFIED」。

**做了但與規格不同**

- SPEC 的唯讀 adapter 應暴露七個工具：「`search`、`get_entities`、`search_documents`、`grep_documents`、`list_schema_fields`、`get_lineage`、`get_dataset_queries`」；STATUS 只有五個：「get_entities、list_schema_fields、get_lineage、get_dataset_queries、grep_documents」。`search` 與 `search_documents` 未做到或至少未列出。
- SPEC 要求 `evidence_id` 所代表的證據含「entity URN、來源 function、擷取時間、payload hash」；STATUS 只確認「id 由內容決定（不含時間戳）」。內容定址本身不必然違反規格，但證據物件是否另存擷取時間、來源 function 與 payload hash，屬情報缺口。
- SPEC 說「Proposal 的每一句都必須引用既有 `evidence_id`」；STATUS 只證明 PolicyGate 會擋「無證據」及「引用不存在證據」。是否做到逐句引用，而不是整份 proposal 只要有一筆證據即可，屬情報缺口。

**未做到或沒有現況證據**

- SPEC 圖中的排程器、Deterministic Orchestrator、Normalizer、Snapshot Diff、SQLite State Store、Steward Review UI、Immutable Artifact Store，STATUS 均未列出。不能把 CLI、JSONL ledger 或 `examples/` 自動視為這些模組。
- SPEC 的核心隔離要求是「寫入憑證只注入獨立的 Executor 程序」。STATUS 只說唯讀 adapter「寫入工具未 import」，沒有證明讀寫使用不同程序、不同憑證或不同權限。另一方面，STATUS 又說已「寫回 DataHub」，但未交代 executor 經由哪個 DataHub 寫入介面完成。這不是已證明的程序級隔離，而是情報缺口。
- SPEC 要求 `edit` 產生新 proposal hash 並使舊核准失效；STATUS 沒有對應敘述。

**本節判定：部分兌現。** 安全閉環的主要零件已存在，但原規格最有辨識力的程序級讀寫隔離、狀態儲存與 steward review 介面尚未被 STATUS 證明。

### 1.2 技術選型

**已做到**

- D1 schema 斷鏈、D1 未文件化欄位與 D3 lineage 漂移已實作。STATUS 原文：「`detectors.py`｜D1 schema 斷鏈、D1 未文件化欄位、D3 lineage 漂移。全確定性，無 LLM。」
- D5 的模組骨架採用 SPEC 指定的形狀：確定性預篩、注入式判讀器、引文閘。STATUS 原文：「`semantic.py`｜D5 語意漂移。確定性預篩 → 注入式判讀器 → 引文閘。」
- D1–D4 應為確定性、只有 D5 使用 LLM 的設計方向沒有被改成「所有判斷都交給模型」。

**未做到**

- SPEC 定義五類 D1–D5；STATUS 已實作清單沒有 D2 新鮮度漂移與 D4 ownership 漂移，故兩類未做到。
- D5 尚未成為可運行功能。STATUS 明載「D5 未接真實 LLM 判讀器，也未接進 CLI」，且「showcase-ecommerce 的 `get_dataset_queries` 回傳 total 為 0」。因此 D5 目前只是可注入判讀器的模組，不是端到端能力。

**本節判定：部分兌現且範圍縮小。** 現況實際產品是 D1、D3 為主的確定性 metadata/context 漂移檢查器；不是 SPEC 所描述的完整 D1–D5 agent。

### 1.3 模組與資料流

**已做到**

- CLI 已提供 `sentinel scan / findings / apply / verify`，對應掃描、檢視、套用與審計驗證。
- STATUS 記錄一次非 dry-run 閉環：「scan → 2 findings → apply → Gate passed → 寫回 DataHub → read-back VERIFIED → 重掃該筆消失 → `verify` 鏈有效（3 筆）。」這足以證明至少一條 D1 類路徑已從讀取走到寫回及再掃描消失，不只是模組列表。
- 未編輯輸出存於 `examples/tlc-rename/`，表示至少該條路徑有留存產物。

**做了但與規格不同**

- SPEC 資料流要求 steward 在 Review UI 中 `reject` 或 `approve(proposal_hash)`；STATUS 只出現「apply → Gate passed」及題目描述中的「經核准後寫回 graph」。PolicyGate 通過不等於人類 steward 核准。是否有不可繞過的人類核准、核准人、核准時間與 proposal hash 綁定，屬情報缺口。
- SPEC 的 Single Proposal Agent 沒有在 STATUS 中被辨識為獨立 agent；目前只有 `proposal.py` 的資料結構與 PolicyGate。除尚未接上的 D5 外，STATUS 沒有任何真實模型或 agent 執行證據。

**未做到或沒有現況證據**

- `reject` 路徑、`CONFLICT` 路徑、重複套用回傳原收據、`VERIFY_FAILED` 路徑，雖有程式能力描述，STATUS 沒有端到端實測紀錄。
- SPEC 要求提議與套用層分離、寫入憑證在獨立程序、所有階段寫入 artifact store；STATUS 未證明這三項資料流約束。

**本節判定：核心成功路徑已兌現，否決、衝突、重複寫入及失敗路徑的可執行證據不足。**

### 1.4 證據與 benchmark

**已做到**

- 兩個第三方來源都已有可報告的分母與結果。NYC TLC 為 35 個月、兩個 schema 事件，結果「2/2 偵測，0 誤報」；`fivetran/dbt_shopify` 為 Tier A 40 筆、負例 2,496，分開報告 IDENTIFIER_CHANGE 9/10 與 DEPRECATION 6/30。
- STATUS 沒有隱藏 `dbt_shopify` 的限制，明載「30 筆中 17 筆的描述不含任何識別碼」及「mart 模型用 `select *`，欄位無法從 SQL 原文重建」。這符合 SPEC「公開實際分母與逐筆結果」的誠實方向，但逐筆結果是否完整公開仍是情報缺口。
- 有一組相同輸入的 baseline 表，也有 `showcase-ecommerce` 25 張真實表的誤報觀察。
- SPEC 的 hash 鏈 JSONL 與 `verify` 命令已實作。STATUS 進一步說 verify 可抓「內容竄改、刪除、順序調換」，且實際鏈「有效（3 筆）」。

**做了但與規格不同**

- SPEC 的 baseline 是 `b0_nocontext`、`b1_rules`、`b2_datahub_native`；STATUS 改成「B0 無 context」、「B1 只看覆蓋率（DataHub 現成能力）」、「B2 描述 vs schema，大小寫不敏感」。名稱與內容都不一致：SPEC 的 B1 是確定性規則、B2 才是 DataHub native，STATUS 則把 DataHub 現成能力放在 B1，另新增大小寫不敏感的 B2。若 README 沿用 SPEC 名稱，會構成錯誤陳述。
- SPEC 要求三層資料：官方 datapack 開發集、凍結後的內部 holdout、第三方 holdout。STATUS 只證明使用 `showcase-ecommerce` 做真實表誤報觀察，沒有 `nyc-taxi`、`healthcare` 開發結果，也沒有「內部 holdout 五類 recall」。
- SPEC 指標包含 D1–D5 分類 precision/recall、citation validity、unsupported-claim rate、abstention rate、gate escape、unauthorized mutation、duplicate mutation、audit verify exit code。STATUS 只提供部分 D1 recall／誤報及一次鏈有效；其餘均未報。

**明確矛盾：第三方 holdout 沒有保持 holdout**

- SPEC 的凍結宣告是：「System code, prompts, policies, and category definitions were frozen before the third-party sources were acquired」以及「Holdout outcomes were not used to modify the frozen system。」
- SPEC 排程又要求 D11 先系統凍結，D12 才讓「兩條第三方 holdout 各跑一次正式評估」，並明寫「只跑一次；結果不回頭改系統」。
- STATUS 卻記錄「dbt_shopify 跑分經三次修正（schema 取 c1 → 取 c2；描述掛表層 → 掛欄位層；被刪欄位的描述遭丟棄 → 補回），第三次由外部診斷指出」。

這不是措辭差異，而是驗證程序被破壞。`dbt_shopify` 仍是有價值的第三方 benchmark，但已不能作為「未碰過、凍結後只跑一次」的 holdout。NYC TLC 的兩個事件也已在 SPEC 寫明後才實作系統，因此材料不足以證明它對系統開發完全不可見。若提交時照抄 SPEC 的凍結宣告，會與 STATUS 自己留下的開發紀錄衝突。

**本節判定：審計已兌現；第三方資料與初步結果已做到；Grand 級 holdout、三層切分與完整指標未兌現。**

### 1.5 交付形態

**已做到**

- 已有 `examples/tlc-rename/` 的未編輯輸出。
- README 存在的間接證據是 STATUS 說「README 已標明」D5 未完成，但 README 的內容與版面未提供。
- 上游已有兩件 open PR：DataHub 主 repo 的 #18622 與 datahub-skills 的 #49。

**未做到**

- SPEC 第一順位的「影片 ≤2:50」未錄。
- repo 仍為 private，Devpost 未提交。這也尚未滿足 BRIEF 要求的 public repo 與可測試 URL。
- SPEC 要求 `examples/` 至少各有一件 DRIFT、CURRENT、INSUFFICIENT_EVIDENCE；STATUS 只指名 `tlc-rename`，沒有 CURRENT 與 INSUFFICIENT_EVIDENCE 產物。
- SPEC 要求 `make demo` / `make bench-replay`；STATUS 沒有這兩個命令的證據。
- SPEC 影片必須呈現 Review UI、DataHub 原生 entity 頁寫回結果、audit root hash 與 benchmark；目前影片不存在，Review UI 也未列入已實作模組。

**情報缺口**

- README 首屏是否有一句話、動圖、三個結果數字、架構、三行快速開始與證據索引，材料不足。
- Apache 2.0 LICENSE 是否存在、未來轉 public 後是否能在 repo About 區顯示，材料不足。
- `examples/tlc-rename/` 是否包含同一筆 proposal、證據、URN、寫回後畫面與 audit receipt，材料不足。

**本節判定：只完成少量靜態產物，尚未形成可提交、可評審的交付包。**

### 1.6 排程

**提前完成的項目**

- D8–D9 的 executor、冪等、read-back、hash 鏈已有實作與一次閉環紀錄。
- D13 的 datahub-skills PR 已提前提出，另多一件 DataHub 主 repo PR。
- D12 的兩個第三方來源已有跑分，但不能算按排程完成，因為它們在 D11 凍結前已被使用與修正。

**尚未完成的技術項目**

- D3–D5 要求「D1–D4 確定性偵測器 + 內部 holdout 五類 recall」；目前 D2、D4 與內部 holdout 都沒有。
- D6–D7 的 Proposal/PolicyGate 已存在，但「gate escape = 0；引用驗證 100%」沒有數字。
- D10 的 D5 未達驗收，因為真實 LLM、CLI 與真實查詢輸入都缺。
- D11 的 `freeze.json` 與可機械核對的凍結宣告沒有現況證據。

**尚未完成的交付項目**

- D14 影片、D15 README／描述／完整 examples、D16 public repo／Devpost 均未完成。

**排程矛盾**

排程的關鍵不是日期，而是依賴順序：D11 凍結後才能做 D12 holdout。現況先跑第三方資料，再三次修改 benchmark 流程，已逆轉這個順序。不能用「進度提前」包裝；必須重建驗證程序或降級主張。

**本節判定：開發速度超前，但依賴順序失守。若不重排，會出現功能很多、Grand 證據不成立、提交物最後幾天才補的局面。**

## 2. 路線偏差與 Grand 三件套

### 題目與賽道：沒有偏離

ROUTE 的斜角一句話是：「別人做『用 context 讓 agent 變可靠』，得獎的形狀是『用 agent 讓 context 保持可信』。」候選 A 定義為把人寫的 context 對照實際行為、附證據修正並寫回 graph；STATUS 的題目仍是「偵測 DataHub 裡『人寫的描述』與『schema／lineage 現實』脫節之處，附證據提出修正，經核准後寫回 graph」，賽道也仍是 Agents That Do Real Work。主路線沒有換成 text-to-SQL、搜尋或泛用資料品質 agent。

### 工具綁定：L3 有功能事實，尚缺 ROUTE 規定的可見證據；L4 已有入口

- ROUTE 對 L3 的驗收不是只說寫回，而是「DataHub UI 上該 entity 頁面看得到」，並要求「附受影響 entity 的 URN 清單與 DataHub UI 截圖／錄影，逐筆可對」。
- STATUS 已有「寫回 DataHub → read-back VERIFIED → 重掃該筆消失」，因此功能層的 L3 不是空話；但 STATUS 沒有 UI 畫面、URN 清單或錄影，故尚未滿足 ROUTE 的評審可驗收標準。
- ROUTE 的 L4 目標是向 datahub-skills 提交新 skill PR。STATUS 有 #49，另有 DataHub 主 repo #18622，方向完全對位。兩件 PR 是否達到 BRIEF 所說的「meaningful」仍是情報缺口，因為材料只有標題與 open 狀態，沒有 diff、review 意見或連結。

### Grand 三件套

1. **第三方 holdout：未兌現。** 有兩個第三方資料來源，不等於有 holdout。`dbt_shopify` 已因結果做過三輪修正，違反 SPEC 的凍結與只跑一次規則；NYC TLC 的兩個答案在 SPEC 中已先寫明，材料不足以證明系統開發未看過。兩者應誠實改稱第三方 benchmark，另找一份凍結後才取得、只跑一次的新來源，才可恢復這一件。
2. **可證明的審計：實作層已兌現。** ROUTE 要求「hash 鏈、`verify` 命令級，不只寫 log」；STATUS 有 append-only JSONL、hash 鏈、可抓竄改／刪除／調序的 verify，並有 3 筆有效鏈的閉環紀錄。尚缺的是把同一筆 root hash、URN 與 DataHub UI 畫面放進 judge-facing 產物。
3. **斜角複核：選題層兌現，產品證據只兌現一半。** 題目仍是 context 自身可信度，沒有掉回一般搜尋或 talk-to-data；但 STATUS 把範圍縮成 description 對 schema／lineage，D5 語意／glossary 的 silent failure 尚不能運行，D2、D4 也缺。ROUTE 對 Aman Gairola 與「第五類 agent」的最強敘事證據目前尚未被 demo 證明。若最後只展示 TLC 欄位大小寫改名，評審可能把它看成 metadata linter，而不是新的 context management agent。

### 其他路線偏差

- ROUTE 要求審批閘、人類否決權、提議／套用分離與明確拒絕權。STATUS 證明 PolicyGate 與三態，但沒有證明人類核准不可繞過，也沒有 Review UI 或 reject 路徑的實測。
- ROUTE 要求明講與 DataHub Cloud Context Hub、既有 DataHub Quality 能力的邊界。STATUS 的 baseline 內容已偏離 SPEC，README 是否有產品邊界聲明屬情報缺口。Originality 防線還沒建立。
- ROUTE 把影片、README、`examples/` 視為評審主要消費面；目前資源投入明顯偏向程式與 benchmark，judge-facing 證據落後。

## 3. 對 BRIEF 評分標準的實際位置

### Use of DataHub：已越過只讀，但證明包尚未完成

BRIEF 說最強作品會「go beyond reading metadata and contribute back to the graph」。現況使用 Agent Context Kit 的五個讀取工具，並有一次 DataHub 寫回、回讀 VERIFIED、重掃消失的閉環；datahub-skills PR 也直接使用主辦生態。這一條目前是強項。

扣點在於 STATUS 沒有交代寫入所用的 DataHub 介面，也沒有 ROUTE 要求的原生 UI、URN 與錄影證據。若評審只看影片與 README，現有功能事實不會自動轉成評分證據。

### Technical Execution：核心路徑可信，完整規格與驗證程序未達成

有 34 個測試通過、確定性 D1/D3、PolicyGate、TOCTOU、冪等、回讀、tamper-evident ledger，以及一次非 dry-run 閉環。這些比只有 demo script 的作品扎實。

但「code do what the submission claims」目前只能支持縮小版主張：D1/D3 可動，不能支持完整 D1–D5。D2、D4 缺，D5 沒有真實 LLM／CLI／輸入，人類核准與程序級讀寫隔離沒有證據；第三方 holdout 又因三次修正失去 holdout 性質。若文案仍照 SPEC 宣稱完整分類、凍結與單次評估，這一條會由強項反轉成誠信與可重現性風險。

### Originality：題目角度新，但目前 demo 容易被看成規則式 linter

ROUTE 所找的「維護 context 自身」確實超出 DataHub 已列出的 Analytics／Quality／Steward／Engineering 四類 agent，且寫回加審計不是重造搜尋。兩件上游 PR也有助於證明是延伸生態。

弱點是最原創的 D5 silent semantic drift 尚未運行，目前最完整證據是 TLC schema 改名。STATUS 的 baseline 又沒有照 SPEC 做 `b2_datahub_native` 對照，且未見「本作品與 DataHub Quality、Cloud Context Hub 各自做什麼」的邊界。若不補，評審可合理問：這與 schema 文件覆蓋檢查器有何本質差異？

### Real-World Usefulness：問題成立，使用規模與使用者證據不足

寫回前閘門、TOCTOU、冪等、回讀、可驗證審計，都是平台團隊會在意的控制；`showcase-ecommerce` 也提供 25 張真實表的誤報觀察。`dbt_shopify` 對 DEPRECATION 的 6/30 及結構性不適用案例被分開報告，能讓使用者理解能力邊界。

但 STATUS 沒有真實 steward 使用、部署週期、處理時間、人工節省量或採用回饋；D5 又因沒有 query history 而無法證明 Pinterest 類 silent semantic failure。現況能證明「問題存在且工具能處理一小類」，還不能證明日常營運價值與涵蓋範圍。這些均為情報缺口，不應用 ROUTE 的市場敘事代替實測。

### Submission Quality：目前最弱

BRIEF 要求 public Apache 2.0 repo、可測試 URL、文字描述與三分鐘內的實際操作影片，並明說評審可以只看文字、圖片、影片。STATUS 明載「demo 影片未錄」、「repo 為 private，未轉 public」、「Devpost 表單未提交」。`examples/` 也只確認一個 `tlc-rename` 路徑，未達 SPEC 的三態樣本。

因此這一條不是「待潤飾」，而是尚未形成合格提交物。即使程式今天停止變更，現況仍無法進入正常評審消費流程。

### Bonus：已有兩個直接命中的 open PR，但「meaningful」尚待證明

BRIEF 明列 skills、fixes、RFCs、documentation improvements 都可加分。STATUS 的 datahub-skills #49 與 DataHub #18622 直接命中，且 #18622 顯示 CI 全綠。這是明確的正向位置。

但 PR 仍為 open，材料沒有 diff、review 意見、連結或被專案維護者採用的證據。不能僅憑 PR 數量判定「meaningful」；應在提交物中提供連結、動機、被本作品實際使用的路徑與最新 review 狀態。

## 4. 剩餘 15 天最該做的三件事

### 1. 先做出可送審、可在 2 分 50 秒內驗收的完整提交包

**預估工時：24–32 小時。**

把 repo 轉 public 前先核對 Apache 2.0 LICENSE 與 About 顯示；完成三行 quickstart、`make demo`、`make bench-replay`；補 DRIFT／CURRENT／INSUFFICIENT_EVIDENCE 三態 examples；錄同一筆 URN 的「DataHub 原生頁 before → scan/proposal/evidence → 人類核准 → 原生頁 after → audit verify」影片；最後填完 Devpost。影片與 examples 必須引用同一筆 proposal、URN 與 audit receipt，不能各演各的。

**不做的代價：** 不只是少拿 Submission Quality，而是 public repo、影片與提交表單都未滿足時，作品沒有可評審入口，其他四條與 bonus 的成果無法轉成名次。

### 2. 修復驗證誠信：凍結後建立一份真正未碰過的第三方 holdout

**預估工時：24–36 小時。**

先凍結 code、規則、prompt、分類定義與資料選擇程序，產生可核對的 `freeze.json`；把 NYC TLC 與 `dbt_shopify` 誠實改標為開發／第三方 benchmark；再依事先寫好的選擇條件取得一份團隊尚未看過的新來源，只跑一次，不因結果改碼。公開逐筆結果、完整 confusion matrix、D1–D5 適用性、誤報、棄權、gate escape、duplicate mutation 與 verify exit code。若找不到合格新來源，就刪除「holdout」與 SPEC 凍結宣告，不能換詞掩飾。

**不做的代價：** Grand 三件套直接缺一件；更嚴重的是 STATUS 已留下三次修正紀錄，若提交仍稱單次凍結 holdout，Technical Execution 與整體可信度會一起受損。

### 3. 完成一條真正有模型、有語意差異、有 steward 否決權的 D5 端到端路徑

**預估工時：32–48 小時；先設 8 小時資料取得停損點。**

先取得可合法放入 demo 的真實 sample query／query history；接上真實 LLM 判讀器與 CLI，強制兩側引文，再讓 proposal 經 proposal-hash 綁定的人類核准、獨立寫入權限、回讀與 audit。把成功案例與一個 `INSUFFICIENT_EVIDENCE`／reject 案例都拍進影片。若 8 小時內仍無真實查詢輸入，就停止追 D5，明確把提交範圍縮成 D1/D3，刪除 Pinterest semantic drift 與完整 D1–D5 主張，改用剩餘時間補程序級讀寫隔離與 steward approval 證據。

**不做的代價：** 現況容易被評為規則式 schema／lineage linter；「AI agent」、「silent semantic drift」與斜角複核最有力的部分都只停在宣稱，Originality、Technical Execution、Real-World Usefulness 三條同時受限。
