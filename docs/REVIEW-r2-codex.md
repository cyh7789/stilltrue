# 第二輪外部審查報告

> 審查基準：只使用本目錄的 `BRIEF.md`、`ROUTE.md`、`SPEC.md`、`STATUS.md`、`VALIDATION-INTEGRITY.md`、`CHANGES.md` 與 `REVIEW-round1.md`，未上網。此目錄不是 Git 儲存庫，無法直接查核提交內容、實作、測試、README、PR 或執行結果；下列「已關閉」只表示新材料已提供足以關閉上一輪文件層發現的證據。材料未提供者一律標為情報缺口。

## 結論

這輪修正把報告從「可能對外作出假宣告」拉回「誠實但證據仍不足」。凍結宣告確實撤回，兩份資料也正確降級為開發期 benchmark；這關閉了錯誤宣告，沒有補回 Grand 級泛化證據。`--approve <proposal_hash>` 關閉的是「核准後內容被換掉」的完整性缺口，不是「只有 steward 能核准」的授權缺口。D1／D3 產出 `CURRENT` 則是合理補強，因為它公開檢查分母與成功解析的對照，不是為湊三態；但應在預設介面顯示摘要，不應把大量 `CURRENT` 混進待處理佇列。

上一輪確定誤判的是 `Evidence` 擷取時間：當時把「`evidence_id` 不含時間戳」錯讀成證據不含擷取時間。新版 `STATUS.md` 已明載 `captured_at` 欄位，這條應判「當初就判錯」。不過新版仍有一個同類風險：頂部說「經 steward 核准後寫回 graph」，實作證據卻只有同一個 CLI 接受 `--approve <hash>`，沒有 steward 身分、獨立權限或不可自行簽發的核准物。外部讀者仍可能把「內容確認」誤讀為「具身分與權限的人工核准」。

目前最弱的是 **Submission Quality**：影片、公開 repo、Devpost 與 L3 可見證據都還不存在。最危險的是 **Technical Execution**：benchmark 調校、核准授權缺口、程序級憑證隔離未做及 D5 無輸入，都直接碰到「Does the code do what the submission claims?」。最弱是尚未交付；最危險則是一旦文案多講半步，既有證據會反過來證明主張不成立。

## 1. 上一輪發現逐條複核

以下合併上一輪內重複出現的同一問題，但不省略任何實質發現。

| # | 上一輪發現 | 判定 | 一句依據 |
|---|---|---|---|
| 1 | 題目與賽道沒有偏離，仍是「用 agent 維護 context」 | 已關閉 | `STATUS.md:9-13` 仍定義為「description × (schema / lineage)」並投 Agents That Do Real Work；方向未換，只是範圍縮小。 |
| 2 | adapter 少了 SPEC 的 `search`、`search_documents` | 未動 | `STATUS.md:19` 明載「5 個讀取工具」且「Kit 另有 `search`、`search_documents` 未包」，只是補了理由，不是補實作。 |
| 3 | 把「`evidence_id` 不含時間戳」視為證據缺少擷取時間 | 當初就判錯 | `STATUS.md:20` 明列 `captured_at`，並說「只有 id 不含 `captured_at`」；`CHANGES.md:2-5` 也明載 Evidence 一直有 `captured_at`。內容定址的 id 與證據物件的時間欄位是兩件事。 |
| 4 | Proposal 是否做到「每一句」引用證據是情報缺口 | 未動 | `STATUS.md:23` 仍只說 Gate 擋「無證據、引用不存在證據」，沒有逐句 claim-to-citation 的資料模型或驗證結果；SPEC 的要求仍是「每一句都必須引用」（`SPEC.md:36`）。 |
| 5 | 排程器、SQLite State Store、Steward Review UI 等架構零件未證明 | 部分 | `STATUS.md:27` 新增 `make demo` 與重播腳本，但 `STATUS.md:97-99` 仍明載「SQLite State Store、排程器」與 Review UI 不存在；Normalizer、Snapshot Diff、Immutable Artifact Store 仍無現況證據。 |
| 6 | 程序級讀寫憑證分離未證明 | 未動 | `STATUS.md:99` 直接承認「沒有兩個程序、兩份憑證的實作」，因此 adapter 未匯入寫入工具與 executor 分檔仍不構成權限隔離。 |
| 7 | 編輯 proposal 後舊核准是否失效是情報缺口 | 已關閉 | `STATUS.md:23` 與 `CHANGES.md:17-23` 說 token 涵蓋文字、證據與 verdict，改字即 `STALE`；`STATUS.md:74-76` 也記錄 A 文核准後寫 B 文被擋。 |
| 8 | D1、D3 已做，D2、D4 未做 | 未動 | `STATUS.md:21` 仍只列 D1／D3；`STATUS.md:91-92` 明載 D2、D4「無程式碼」。 |
| 9 | D5 只有骨架，沒有真實 LLM、CLI 與輸入 | 未動 | `STATUS.md:22,93` 明載「未接真實 LLM，未接進 CLI」，且 `get_dataset_queries` 的 total 為 0。 |
| 10 | CLI 成功閉環有現況證據 | 已關閉 | 證據比上一輪更強：`STATUS.md:74-78` 記錄 2 DRIFT、5 CURRENT、兩次拒絕、正當核准、DataHub 寫回、回讀 `VERIFIED`、重掃轉 `CURRENT` 與 10 筆有效鏈。 |
| 11 | 人類核准不可繞過沒有證據 | 部分 | `--approve <proposal_hash>` 已讓寫入必須帶明確 token（`STATUS.md:23`），但材料沒有 steward 身分、獨立核准權限或不可由 apply 操作者自行產生的核准物；它證明內容綁定，未證明授權邊界。 |
| 12 | 沒有真實 agent／模型執行證據 | 未動 | `STATUS.md:21-23` 顯示可執行路徑是確定性 D1／D3 加資料結構與 Gate；唯一模型位置 D5 仍未連線。 |
| 13 | reject、CONFLICT、重複套用、VERIFY_FAILED 等失敗路徑缺端到端證據 | 部分 | `STATUS.md:74-76` 新增 `NOT_APPROVED` 與 `STALE` 的實跑證據，但仍沒有 steward 主動 reject、`CONFLICT`、重複套用回原收據或 `VERIFY_FAILED` 的端到端紀錄。 |
| 14 | 兩份第三方資料有公開分母、正負結果與限制 | 已關閉 | `STATUS.md:34-49` 保留 TLC 2/2、0 誤報與 dbt_shopify 9/10、6/30、2,496 負例及 `select *` 失真；`VALIDATION-INTEGRITY.md:82-86` 也保留分母與負面結果。 |
| 15 | SPEC 與實作 baseline 定義不一致，且缺 `b2_datahub_native` | 未動 | `STATUS.md:60-65` 明確承認偏離，並說「`b2_datahub_native` 對照目前沒有」；揭露偏離沒有補上 Originality 所需對照。 |
| 16 | 官方開發集與內部 holdout 不完整 | 未動 | `STATUS.md:94` 明載內部 holdout 不存在，開發集只用了 `showcase-ecommerce`，`nyc-taxi` 與 `healthcare` 未使用。 |
| 17 | 完整指標面缺失 | 未動 | `STATUS.md:100` 明載只報 recall、誤報與 verify 鏈，citation validity、unsupported-claim rate、abstention rate、gate escape、duplicate mutation 等仍無數字。 |
| 18 | 凍結宣告與實際時序矛盾，兩份資料不能稱 holdout | 已關閉 | `SPEC.md:106-116` 已將原宣告刪線並標「不得放入提交物」；`VALIDATION-INTEGRITY.md:20,70-72` 明說原句為假，兩份來源改稱開發期 benchmark；`CHANGES.md:49-75` 記錄撤回而非改寫。 |
| 19 | Grand 級第三方 holdout 不存在 | 未動 | 撤回錯誤宣告不等於建立新 holdout；`STATUS.md:95` 仍說沒有 `freeze.json`，`VALIDATION-INTEGRITY.md:91-99` 也說凍結後才取得、只跑一次的新來源「It has not been done yet」。 |
| 20 | 三態 examples 不完整 | 已關閉 | `CHANGES.md:37-43` 說 `make demo`、`examples/abstention/` 與重生的 `examples/tlc-rename/` 已涵蓋三態及拒絕紀錄；`STATUS.md:69-78` 對應列出棄權與 5 筆 CURRENT。 |
| 21 | 缺 `make demo`／`make bench-replay` | 已關閉 | `STATUS.md:27` 明列兩個命令，`CHANGES.md:37-40` 說完整閉環可重跑。 |
| 22 | 影片、公開 repo、Devpost 尚未完成 | 未動 | `STATUS.md:104-106` 仍逐項列為未完成。 |
| 23 | DataHub UI 畫面與受影響 URN 清單缺失，L3 尚不可由評審目視驗收 | 未動 | `STATUS.md:107` 明載「L3 可見證據未產出」；這仍未達 ROUTE「DataHub UI 上該 entity 頁面看得到」（`ROUTE.md:311-318`）的驗收標準。 |
| 24 | README 首屏、Apache 2.0 LICENSE／About 顯示是情報缺口 | 未動 | 新材料仍未提供 README 或 LICENSE 內容；`STATUS.md:104-108` 只列提交物缺口，無法確認 BRIEF 的公開 repo 與 Apache 2.0 形式要求（`BRIEF.md:49-56`）。 |
| 25 | 兩件上游 PR 存在，但是否屬 meaningful contribution 是情報缺口 | 未動 | `STATUS.md:82-85` 只提供標題、open 狀態與一件 CI 全綠，沒有 diff、review 或採用證據；不能由 PR 數量推出 BRIEF 所稱的「meaningful」。 |
| 26 | 可證明審計的實作已成立，但 judge-facing 證據鏈未完成 | 部分 | `STATUS.md:25,74-78` 把鏈增至 10 筆並納入拒絕事件；但 `STATUS.md:107,113` 仍缺 UI／URN 可見證據，且鏈末筆沒有外部錨點。 |
| 27 | 最原創的語意漂移未運行，作品容易被看成 schema／lineage linter | 未動 | `STATUS.md:12-13` 把實際範圍縮為 description × schema／lineage，`STATUS.md:93` 仍無 D5 輸入與執行路徑。 |
| 28 | 與 DataHub native／Context Hub 的產品邊界尚無可見證據 | 未動 | `STATUS.md:64,96` 仍缺 `b2_datahub_native`；本輪材料也沒有 README 或影片內容可證明已說清 Cloud Context Hub 的邊界。 |
| 29 | 真實 steward 使用、週期性部署、節省量與採用回饋缺失 | 未動 | `STATUS.md:97-99` 顯示仍是單發 CLI、無排程器與 Review UI；其餘使用者或營運成效數字未出現在新材料。 |

### 新版 STATUS 是否仍可能讓外部讀者誤判

`captured_at` 那類省略已修正。`STATUS.md:20` 同時說清楚物件欄位、id 的內容定址範圍與設計效果，足以避免原誤判。

仍有三處應改得更精確：

1. `STATUS.md:9-10` 的「經 steward 核准後寫回 graph」會讓人以為已有可驗證的 steward 身分與權限；但 `STATUS.md:98-99` 說只有 CLI hash，沒有 Review UI 或程序級憑證分離。建議改成「操作者在 CLI 明示確認 proposal hash 後寫回；尚未驗證操作者是否為獨立 steward」。
2. `STATUS.md:23` 說 hash「涵蓋文字＋證據＋verdict」，沒有交代 entity URN、aspect、`before_hash` 與預期新值是否也在簽核範圍。這不等於它們沒被涵蓋，但外部讀者無法判定。應列出完整 canonical payload，或標情報缺口。
3. `STATUS.md:27` 與 `CHANGES.md:38-39` 把 `make demo` 稱為「全閉環含兩次拒絕」，容易被讀成已有 steward 的明確 reject 流程；實際兩次是 `NOT_APPROVED` 與 `STALE`（`STATUS.md:74-76`）。應稱「兩次自動拒寫」，與「steward 主動否決」分開。

## 2. 三個新改動本身的審查

### 2.1 撤回凍結宣告、改稱 benchmark

**判定：必要且處理正確，但只修復了誠信，不修復驗證強度。**

撤回方式是對的。`VALIDATION-INTEGRITY.md:20` 明說「That sentence is false. It has been removed rather than reworded」，並在 `:35-60` 指出 TLC 結果改變 adapter、dbt_shopify 分數決定 detector 分支；`SPEC.md:106-116` 也保留刪線原文與作廢原因。這比換一個模糊名稱繼續暗示 untouched evaluation 好。

「揭露了就沒事」會把問題講小。`VALIDATION-INTEGRITY.md:88-89` 已正確說出實質後果：「A benchmark that shaped the rules measures fit, not transfer.」這表示 2/2 與 9/10 只能證明規則對已參與開發的案例有 fit／回歸價值，不能證明對新來源的泛化。評審若看到「規則 producing 9/10 was chosen because of the 9/10」（`VALIDATION-INTEGRITY.md:60`），合理反應不是單純嘉許誠實，而是下修該數字的證據權重，並追問是否有獨立驗證。

揭露本身可能比含糊帶過更傷眼前分數，因為它把過度配適風險放到評審面前；但含糊帶過的尾端風險更大。`BRIEF.md:72` 的 Technical Execution 直接問「Does the code do what the submission claims?」，而提交資料內已有可追查的提交雜湊與因果註解。若淡化成「第三方資料」並讓評審誤以為是泛化證據，一旦被看穿，損失會從 benchmark 一項擴大為整份提交的可信度。

建議不是把完整自白放在影片開場，也不是藏起來：

- 任何呈現 2/2、9/10 的同一畫面或同一段文字，緊鄰標示「development benchmark; measures fit, not transfer」，不要讓限制只存在另一份文件。
- README 的結果區用一至兩句說明限制，連到 `VALIDATION-INTEGRITY.md` 的完整時序；影片不必逐筆講提交歷史，但不得稱 holdout、unseen、frozen 或 generalization。
- 不把 2/2 當前三個主打成效數字。可把它定位成「公開、可重生的回歸基準」，把 6/30 負面結果與棄權行為一起呈現，證明工程誠信而非模型準確率。
- 若要恢復 Grand 級主張，唯一正解仍是 `VALIDATION-INTEGRITY.md:91-97` 所列流程：先提交 `freeze.json`，再取得未看過來源，只跑一次，無論結果如何都不改該次受評系統。

### 2.2 `--approve <proposal_hash>` 核准閘

**判定：關閉核准完整性缺口，沒有關閉核准授權缺口。**

這次改動不是毫無價值。上一版「核准綁 hash」只有 docstring；現在 `CHANGES.md:17-23` 說改字後會 `STALE`，`STATUS.md:74-76` 也有 A 文核准、B 文寫入遭擋的實測紀錄。它防止「人看過一份內容，Executor 寫入另一份內容」，也讓核准意圖成為可審計輸入。

但若產生 proposal、讀取 hash 與執行 apply 的是同一個操作者、同一組權限，`--approve <hash>` 仍可由寫入者自行帶入。系統只知道呼叫者知道正確 hash，不知道 steward 看過內容、是誰核准、何時核准，也不知道核准權是否與寫入權分離。就「人類核准可繞過」這個發現而言，它確實只是把門檻從一次寫入命令改成取得 hash 後再帶一個參數；就「核准後偷換內容」而言，則是實質關閉。

要保留「steward 核准」主張，最小可驗收形狀應是：

1. `approve` 產生不可由 Executor 自行簽發的核准收據，至少綁定完整 proposal canonical payload、核准者身分、時間與 proposal hash。
2. 核准收據由獨立 steward 憑證簽署，或寫入只有 steward 角色能改的 state store；Executor 只有驗證權，沒有簽發權。
3. ledger 同時記錄 proposer、approver、executor，並拒絕 approver 與執行憑證不符合政策的請求。
4. 若 15 天內不做身分與權限邊界，就把對外用語降為「explicit content-bound operator confirmation」，不要稱「steward approval」或「human approval cannot be bypassed」。

### 2.3 D1／D3 開始產出 CURRENT

**判定：是補足可觀測的三態與分母，不是為湊規格製造假訊號；呈現層若逐筆灌入待辦清單，才會變成噪音。**

`CHANGES.md:25-30` 說舊版讓成功解析的引用靜默消失，導致「2 findings」看不出系統實際檢查多少；新版可報「2 drift, 5 verified current, 0 abstained」。這直接支撐 precision／abstention 的分母，也讓 `INSUFFICIENT_EVIDENCE` 不會在沒有成功對照時顯得只是保守逃避。`STATUS.md:74-76` 還記錄同一筆 `airport_fee` 經寫回後由 DRIFT 轉 CURRENT，對 read-back 與重掃閉環是有意義的終態證據。

風險在輸出形狀。持續掃描大量正常 entity 時，逐筆 `CURRENT` 很容易淹沒 DRIFT 與棄權。建議：

- ledger 與 benchmark 原始輸出保留逐筆 CURRENT，確保分母可重算。
- CLI 預設只顯示三態計數及 DRIFT／INSUFFICIENT_EVIDENCE 明細；用 `--include-current` 才展開正常項。
- Review UI 或影片只展示「修正前 DRIFT → 修正後 CURRENT」的同一筆，以及總計，不建立正常項待辦佇列。
- 明確定義判定單位是 entity、欄位引用還是 claim；否則「5 CURRENT」仍無法與「2 DRIFT」形成可解釋的同分母。

## 3. 剩下 15 天最該做的三件事

### 1. 做出可直接送審的單一證據鏈，並把核准主張校正到實作

**預估工時：24–32 小時。**

以同一個 URN 串起 DataHub 原生頁 before、scan、逐句證據、proposal、核准／拒寫、寫回、原生頁 after、重掃 CURRENT 與 audit root；完成兩分五十秒內影片、README 首屏、Apache 2.0／About 檢查、公開 repo、Devpost 草稿與 StillTrue／`sentinel` 命名處理。核准部分二選一：實作獨立 steward 核准收據與權限，或把影片與 README 降稱為內容綁定的操作者確認。`STATUS.md:104-108` 顯示影片、公開 repo、Devpost、L3 畫面與名稱統一全未完成，而 BRIEF 明說評審可只看文字、圖片與影片（`BRIEF.md:49-56`）。

**不做的代價：** Submission Quality 仍接近零，L3 寫回與審計即使真的可動也不會進入評審視野；若影片仍稱 steward 核准，Technical Execution 還會多一個可直接反證的主張。

### 2. 衝 D5，但把資料取得停損硬設為 8 小時；失敗才轉做 D2

**預估工時：8 小時資料取得停損；取得可合法重現的真實 query 輸入後，再投入 20–32 小時完成 CLI、雙側引文、棄權與 demo。**

我選 D5，不選先做 D2。理由不是 D5 較炫，而是目前最大的名次缺口在 Originality：`STATUS.md:12-13` 的實作品質已縮成 description × schema／lineage，`STATUS.md:93` 又顯示唯一語意判讀沒有輸入。D2 會增加一個確定性偵測類，且官方 `nyc-taxi` 已有 planted freshness issues（`BRIEF.md:145-149`），所以執行風險低；但它仍把作品往「更多規則的 metadata linter」推，無法證明 ROUTE 的 Pinterest silent semantic failure（`BRIEF.md:215-217`）或「第五類 agent」敘事。

8 小時內必須拿到可合法放入 repo、可由評審重生、能形成至少一個 DRIFT 與一個 INSUFFICIENT_EVIDENCE 的查詢輸入；拿不到就停止，不自建答案已知的漂亮案例來假裝真實性，改做 D2。D2 的驗收應是官方 planted issue 的端到端偵測、零硬編碼資料集名稱、公開分母與負例，而不是只新增 detector。

**不做的代價：** 若完全放棄 D5，Originality 仍靠文案支撐，評審很可能把 StillTrue 視為 schema／lineage 規則檢查器。若不設停損，則可能把最後一週耗在不存在的 `get_dataset_queries` 輸入上，連提交包都延誤。

### 3. 凍結後跑一份真正未碰過的第三方 holdout

**預估工時：20–32 小時。**

先固定 detectors、分類、scoring scripts、資料選擇準則與適用性規則，提交 `freeze.json`；再取得團隊未看過的來源，只跑一次，公開逐筆結果、分母、棄權、誤報與失敗，結果不回頭改本次受評版本。現有兩份 benchmark 保留作開發與回歸證據，不再承擔泛化主張。`VALIDATION-INTEGRITY.md:91-99` 已把恢復條件寫得夠清楚，可以直接變成機械流程。

**不做的代價：** 誠信風險雖已解除，Grand 三件套仍缺第三方 holdout；2/2 與 9/10 只能證明 fit，不足以讓評審相信規則能轉移到未見來源。

### 與上一輪排序的差異

第一名不變，但工作量下降：`make demo`、`make bench-replay`、三態 examples 與拒寫紀錄已補上（`STATUS.md:27,69-78`），現在要把它們組成評審看得到的同一條證據鏈。

D5 從第三升到第二，真正 holdout 從第二降到第三。原因是錯誤凍結宣告已撤回，驗證誠信不再是立即會反噬整份提交的危機；反而新版 `STATUS.md` 把範圍縮小與 D5 無輸入說得更清楚，使 Originality 的功能缺口成為下一個名次瓶頸。這不降低 holdout 的 Grand 價值，只是把「先恢復斜角的可運行證據」排在「再證明泛化」之前。

## 4. BRIEF 五條評分標準的現在位置

| 評分標準 | 現在位置 | 依據與主要扣分 |
|---|---|---|
| Use of DataHub | 強，但評審可見性不足 | 已有 Agent Context Kit 五個讀取工具、DataHub 寫回、回讀 VERIFIED、重掃轉 CURRENT（`STATUS.md:19,74-76`），符合「contribute back to the graph」（`BRIEF.md:71`）的方向；但原生 UI 畫面與 URN 清單尚未產出（`STATUS.md:107`），程序級讀寫憑證也未分離（`:99`）。 |
| Technical Execution | 中等且最危險 | 42 個測試、可重跑 demo、TOCTOU、冪等、回讀、hash 鏈與拒寫紀錄是實質優點（`STATUS.md:4,23-27,72-78`）；但 D2／D4 無程式碼、D5 無輸入與 CLI、核准無身分權限邊界、無程序級隔離、無完整指標，ledger 末筆也無外部錨點（`:91-100,113`）。任何「完整 D1–D5 agent」「steward-only approval」「tamper-proof」主張都會超過證據。 |
| Originality | 中等偏弱 | 「維護 context 自身」的題目角度仍有差異，但可運行產品只剩 description × schema／lineage（`STATUS.md:12-13`），D5 不可執行（`:93`），`b2_datahub_native` 又缺席（`:96`）。目前功能畫面容易被看成規則式 linter，無法只靠 ROUTE 的企業敘事補足。 |
| Real-World Usefulness | 中等偏弱 | 寫入前 Gate、TOCTOU、冪等、回讀與拒寫都是平台團隊會在意的控制，兩份公開 benchmark 也證明真實漂移案例存在；但仍是單發 CLI、無排程器、無 Review UI（`STATUS.md:97-99`），沒有真實 steward 使用、處理週期、節省工時或採用回饋。 |
| Submission Quality | 最弱 | `STATUS.md:104-108` 明載影片未錄、repo private、Devpost 未交、L3 畫面／URN 未產出、名稱未統一；而 BRIEF 把 demo、文字與 README 列為獨立等權評分，且允許評審完全不執行專案（`BRIEF.md:52,56,75`）。 |

**最弱：Submission Quality。** 原因是必備交付物仍不存在，不只是呈現尚待修飾。

**最危險：Technical Execution。** 原因是現有文件已留下 benchmark 反饋改碼與核准／憑證邊界未完成的精確證據；文案只要仍使用 holdout、steward approval、完整 agent 或 tamper-proof 等超出現況的詞，評分條款「Does the code do what the submission claims?」就會直接得到否定答案。

Bonus 目前是正向但未定：兩件 open PR 對準 BRIEF 的開源加分條款（`STATUS.md:82-85`；`BRIEF.md:76`），但是否 meaningful 仍是情報缺口，提交物應附 PR 連結、diff 摘要、實際採用路徑與最新 review 狀態。
