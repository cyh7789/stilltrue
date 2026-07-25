# REVIEW — 第二輪外部審查（修正後複核）

> 審查日 2026-07-26，距截止 15 天。僅依本目錄 BRIEF.md / ROUTE.md / SPEC.md / STATUS.md（v3）/ VALIDATION-INTEGRITY.md / CHANGES.md / REVIEW-round1.md 推導，未用網路。`run.log` 仍只有一行 bun 警告，無證據價值。
> 引文皆為原文；查不到的標「情報缺口」。上一輪的誤判在 §1.3 自認，不迴避。

---

## 1. 上一輪發現逐條判定

### 1.1 六個矛盾點（round1 §1.7）

| # | 上輪發現 | 判定 | 依據（原文） |
|---|---|---|---|
| C1 | 凍結宣告被自己的開發過程推翻 | **部分關閉** | 誠實面已處理且超規格：CHANGES 6c3d153「The claim is withdrawn rather than reworded」、SPEC §3.5 已劃線並標「未執行，宣告作廢，不得放入提交物」、VALIDATION-INTEGRITY 附 commit hash 時序。但證據面未復原：同檔明寫「It has not been done yet」——凍結與凍結後單跑都還不存在，詳 §2.1 |
| C2 | 未完成清單不完整、範圍縮水未申報 | **已關閉** | STATUS §1「**範圍已縮**：SPEC §0 原寫……四面，實作只涵蓋 description × (schema / lineage)」；§6 完整清單 17 項，D2/D4 列第 1、2 項 |
| C3 | baseline 定義偏離 SPEC 3.4 且只跑 n=2 | **部分**（揭露了，沒修） | STATUS §3「⚠️ 與 SPEC 3.4 的偏離……**Originality 條款想要的 `b2_datahub_native` 對照目前沒有**」「baseline 只跑在分母 2 的 TLC 上」。缺口本體原封不動。另：上輪的「B2 造來輸」嫌疑被有依據地澄清——「那正是本專案第一版自己犯的 bug，回歸測試還留在 `tests/test_detectors.py`」，此點上輪判得過重 |
| C4 | adapter 工具 5 個 vs 規格 7 個 | **已關閉**（以申報方式） | STATUS §2 明寫缺哪兩個與理由「掃描範圍由 URN 清單或 `--limit` 決定，偵測路徑不需要搜尋」；CHANGES 6c3d153「Also disclosed in the README: … why the adapter wraps five of the Kit's seven read tools」。範圍決策已declared，可辯護 |
| C5 | 審批閘弱化／Review UI／State Store／排程器缺席 | **部分** | 最要害的一半已補實作：CHANGES 906eae1「Now `--approve <hash>` is required before a write, and the token covers the text, the cited evidence and the verdict」——「edit 使舊核准失效」從 docstring 變成機制（詳 §2.2）。Review UI、State Store、排程器仍無，但已入 STATUS §6 第 7、8 項明文申報 |
| C6 | evidence_id 不含時間戳違反 SPEC | **當初就判錯** | STATUS v3：「`captured_at`……擷取時間本身有存在紀錄裡（`evidence.py:47` 與 `to_dict()`）」。SPEC §1 第 2 條要求的是**證據紀錄**含擷取時間，紀錄一直有；只有 id 是內容定址。上輪把「id 不含時間戳」讀成「證據不含時間戳」，是引文只引半句就下結論的錯——本報告作者自己犯的 |

### 1.2 其餘發現與情報缺口

| 上輪項目 | 判定 | 依據 |
|---|---|---|
| D2、D4 未實作 | **未動**（已申報） | STATUS §6 第 1、2 項「無程式碼」 |
| D5 半成品、無輸入資料 | **未動** | STATUS §6 第 3 項「`get_dataset_queries` 回傳 total 為 0，沒有輸入資料」 |
| B 層內部 holdout 缺席 | **未動**（已申報） | STATUS §6 第 4 項「不存在」 |
| A 層開發集只用 1/3 | **未動**（已申報） | 同上「`nyc-taxi` 與 `healthcare` 未使用」 |
| 指標面縮水 | **未動**（已申報） | STATUS §6 第 10 項「citation validity……等無數字」 |
| examples/ 只有一件 | **已關閉** | CHANGES 906eae1「all three verdicts now have an unedited example」；STATUS「未編輯輸出：`examples/abstention/`」 |
| `make demo` / `make bench-replay` 傾向未做 | **已關閉**（當時判斷正確，本輪補上） | STATUS §2 Makefile 列；CHANGES「Also from the reviews: `make demo` / `make bench-replay`, plus scripts/demo.sh」 |
| 排程順序倒置（holdout 先跑、驅動迭代） | **已確證為事實** | VALIDATION-INTEGRITY 時序表與兩段引文（457b190、0757ee3）。事實面關閉；矯正動作（凍結）未做 |
| 缺口 5：TLC 跑分與 adapter 修改的時序 | **已關閉**（確認不乾淨） | 「`457b190` — TLC loader **and** `authored_description()` **and** the D1 tightening」同一 commit；「The TLC result was used as an acceptance check on a code change」 |
| 缺口 9：一天內完成量不可信、疑實作先於 SPEC | **缺口已補；上輪推斷錯誤** | 時序表顯示 07-25 22:44（miner）至 07-26 00:19（dbt 跑分）——主要工作發生在 SPEC 定稿（07-25）之後的數小時內。上輪「合理解釋是大量實作先於 SPEC 定稿」的假說被推翻。時間戳出自專案自己的誠信文件，原則上可對 repo 核驗 |
| 缺口 1：程序級憑證分離 | **已確證不存在**（申報，未修） | STATUS §6 第 9 項「**沒有兩個程序、兩份憑證的實作**。SPEC §1 採 codex 架構的核心理由……目前不成立」 |
| 影片／repo public／Devpost | **未動**（仍在排程內） | STATUS §6 第 11–13 項 |
| 缺口 2（冪等鍵公式）、缺口 10（gate 白名單內容）、缺口 7（B1 忠實度）、缺口 3（README 全文達成度） | **未答，缺口延續** | STATUS v3 皆未載；README 僅知揭露了 D2/D4 與 5/7 工具兩件事（CHANGES） |

### 1.3 新版 STATUS 是否還有同類的、會讓外部讀者誤判的省略

TASK 點名的 C6 型錯誤（寫太省 → 讀者補腦成違規）在 v3 有四個殘餘候選，按嚴重度排：

1. **dbt_shopify 的 2,496 筆負例沒有誤報數。** TLC 段明寫「0 誤報」，B 段只有 recall（9/10、6/30）。外部讀者會預設 precision 同樣乾淨——如果實際不是 0，這是 v3 版的 C6：省略製造出一個未宣稱但會被默認的主張。**這是本輪最該立刻補的一個數字**（或明寫「負例誤報數未量測」）。
2. **B1 的括號「（DataHub 現成能力）」仍是未經驗證的等號。** 上輪缺口 7 未答；在 `b2_datahub_native` 不存在（STATUS 自認）的情況下，這個標籤會被讀成「已與 DataHub 現成 Quality skill 對照過」。要嘛驗證，要嘛改寫成「覆蓋率檢查（近似 DataHub 現成能力，未逐項比對）」。
3. **showcase-ecommerce「25 張表」的選樣方式未寫。** BRIEF 8.5 載該 datapack 有「1,049 entities」；25 張怎麼挑的不明，「誤報 0」的分母選擇不透明，評審一問就要現場補答。
4. （輕）**`--approve` 的核准者未認證這件事，在 §2 的 proposal.py 行看不出來**，要讀到 §6 第 9 項才拼得出「核准＝任何敲得到 CLI 的人」。建議在 §2 該行加半句。

---

## 2. 三個改動本身的審查

### 2.1 撤回凍結宣告、改稱 benchmark——夠不夠？

**誠實面：夠，且超出上輪要求。** 上輪建議的是「改寫為誠實版本」；實作選了更硬的「撤回而非改寫」（"withdrawn rather than reworded"），附 commit hash 級時序、把警語內嵌進兩份 bench 報告（「a judge opening only REPORT.md still sees it」）、保留審查紀錄原文（「rewriting those would be the dishonest move」）。作為誠信處置，這是教科書等級。

**證據面：不夠，而且「揭露了就沒事」確實把問題講小了。** 揭露不會把 benchmark 變回 holdout。VALIDATION-INTEGRITY 自己說得最準：「A benchmark that shaped the rules measures **fit, not transfer**.」ROUTE 3.4 把第三方 holdout 列為 Grand 級三件套第 1 件——這一件現在**是空的**，不是打折。專案目前沒有任何轉移性證據，只有擬合數字加一份誠實的說明書。

**評審看到「規則是對著 benchmark 調的」會怎麼反應？** 分兩種讀者。會細讀的（Tim Bossenmaier、Mike Burke，或 BRIEF 6 保留條款的「automated AI-driven analysis」）：把 2/2、9/10 折價成擬合證據，同時給誠實加分——淨效果中性偏正。只看 README 首屏和影片的：取決於警語的位階，見下。

**揭露有沒有可能反而比含糊更傷？有，但傷的不是揭露本身，是現在的呈現位階。** 風險情境：評審先看到「That sentence is false」等級的自白當主敘事，而 repo 裡又沒有任何 holdout 補位——得到的印象是「差點造假」疊加「沒有轉移證據」，比從頭沒提過凍結更糟。但**回頭含糊帶過是更差的選項**：commit 457b190 的訊息裡就躺著「made the TLC holdout scan return nothing」，BRIEF 6 明寫評選「may utilize expert panels, peer review, automated AI-driven analysis」——含糊是可以被機器從 git 歷史裡翻出來的，而被翻出來的含糊＝坐實隱瞞。

**建議（兩步，缺一不可）：**

1. **調位階，不刪內容。** README 首屏對數字的註記收成一行（「兩份第三方來源為開發期 benchmark，非凍結 holdout，完整時序見 VALIDATION-INTEGRITY.md」）；VALIDATION-INTEGRITY 從自白體改方法論體——先講三條仍成立的性質（標籤非自產、分母公開、難看數字照報），撤回的宣告移到中段當時序紀錄。認錯的內容一字不少，但評審動線上第一眼看到的是「什麼仍然為真」。
2. **把故事改掉：補一條凍結後的真 holdout（見 §3 第 2 件）。** 一旦存在「凍結→新來源→單跑」的紀錄，VALIDATION-INTEGRITY 就從認罪書變成嚴謹度證據——「我們區分擬合與轉移，兩種都給你」比「我們只有擬合，但很誠實」高一個級距。

### 2.2 `--approve <proposal_hash>`——關掉缺口了，還是把一個命令變兩個命令？

**兩者都是，取決於問哪個威脅。**

**真關掉的：核准與內容的綁定。** 上輪的發現是「核准是 docstring」——寫了「approvals bind to this value」但無程式碼執行，人類核可實質等於「有人去敲 apply」。現在 token「covers the text, the cited evidence and the verdict」，改字即 STALE、fail-closed，且拒絕入鏈（STATUS §2「被拒絕的嘗試也入鏈（NOT_APPROVED / STALE）」，demo 實跑過 NOT_APPROVED 與 STALE 兩次拒絕）。這關掉的是「核准無害措辭、寫入另一份內容」的 TOCTOU 攻擊面——**這是質變，不是門檻加高**。選 hash 而非 y/n prompt 的理由也成立（「a prompt cannot detect that the text changed after it was read」），比上輪建議的一小時級 prompt 方案好。

**沒關掉的：核准者的身分。** 無認證、無獨立憑證、無隔離程序——同一個 shell 能敲 scan 也能敲 approve 再敲 apply。對「自動化程序繞過人類」這個威脅，它確實只是把一個命令變成兩個命令。緩解這點的是架構其餘部分：模型拿不到 CLI（D5 未接線）、adapter 無寫入工具，所以現有系統內沒有一個能自己敲命令的 agent。真正補完這一半的是 STATUS §6 第 9 項那個尚未實作的程序級憑證分離。

**判定：對 hackathon 的「steward 保留否決權」宣稱夠用，前提是 README 明寫信任域**——「核准未認證，信任域是單使用者 CLI；多使用者部署需憑證分離（未實作）」。寫了這句，這個閘是誠實的工程；不寫，就是第二個等著被追問的 C6。

### 2.3 D1/D3 產出 CURRENT——補足宣稱，還是湊規格的噪音？

**補足宣稱，理由站得住。** 修正前三態宣稱實質為假：「The three-verdict design shipped as two: D1 and D3 silently skipped references that resolved, so only `semantic.py` — which isn't wired to the CLI — could ever emit CURRENT」——即 SPEC §1 第 3 條「三態輸出」在可運行路徑上是二態。修正的論證也不是湊數：「"2 drift, 5 verified current, 0 abstained" states how much it checked; "2 findings" does not, and an abstention is only believable next to the references that did resolve」——棄權（本作賣點之一）的可信度需要解析成功的引用當對照，CURRENT 是拒絕權敘事的分母。測試有 mutation check（「stub the CURRENT branch -> 3 red」），不是形狀測試。

一個營運面小風險，非缺陷：大 graph 上 CURRENT 筆數會淹沒 findings 輸出（TLC 一次掃描 5 筆 CURRENT、25 張表 14 筆棄權；showcase-ecommerce 全量是 1,049 entities）。建議 CLI 預設輸出三態計數摘要、`findings` 預設 filter 到 DRIFT，完整三態留給 `--all` 與 examples。工時小時級，可併入提交面工作。

---

## 3. 剩餘 15 天最該做的三件事（按對名次的邊際效益排序）

執行順序有一條硬約束先講：**凍結必須在所有程式碼改動之後、holdout 單跑之前**。所以時間軸是「第 3 件（D2 程式碼）→ 凍結 → 第 2 件（新來源單跑）→ 第 1 件（提交面）」，與下面的邊際效益排序不同。

**第 1 件：提交消費面——影片、README 定稿、命名統一、repo public、Devpost。**
與上輪同位，但內容縮了：examples 三態與 make demo/bench-replay 本輪已補完。剩：影片 2 天（分鏡照 SPEC §5，必含 DataHub 原生頁 graph 已更新、拒絕權演一次——現在有現成素材：demo 的 NOT_APPROVED 與 STALE 兩顆鏡頭）；README 定稿 1 天（首屏含 Cloud Context Hub 邊界聲明、L3 證據——URN 清單與 UI 截圖即 STATUS §6 第 14 項、benchmark 一行註記、§1.3 列的四個省略補寫）；命名統一 0.5 天（§6 第 15 項——影片講 StillTrue、終端機印 sentinel，是 Submission Quality 的自傷）；public + About 區 Apache 2.0 檢查 + Devpost 0.5 天。合計約 4 天。
不做的代價：影片與 public repo 是提交規格硬要件，缺一件無法有效提交；「Judges are not required to test the Project and may choose to judge based solely on the text description, images, and video」——這層不存在，名次為零。

**第 2 件：凍結 + 一條凍結後的新第三方來源，單跑一次。**
**這件與上輪第 2 件不同，順序沒變但內容換了，換的原因是本輪新事實**：上輪建議「凍結後對兩條 holdout 各正式重跑一次」；VALIDATION-INTEGRITY 證實兩條來源都塑造過規則（457b190、0757ee3），重跑它們量的仍是 fit——該檔自己寫了唯一的復原條件：「A source acquired **after** a recorded freeze, scored once, with the code untouched afterwards regardless of outcome」。作法：`freeze.json` 釘住 detectors、分類定義、跑分腳本的 hash（半天）；用現成的 `mine_drift_labels.py` 換一個未接觸過的同型 dbt 套件當新來源（oracle 腳本已存在、機制同 dbt_shopify，1 天）；單跑一次、結果無論好壞照登、寫進 VALIDATION-INTEGRITY 收尾段（半天）。合計 1.5–2 天。
不做的代價：Grand 三件套第 1 件持續空缺，headline 數字全是擬合證據，§2.1 的自白留在頭條沒有補位敘事。這件事的槓桿在於它同時修 Technical Execution 的殘餘與 Originality 的證據面，單位工時的名次效益僅次於第 1 件。風險要照 SPEC 3.4 原則管理：「第三方 holdout 不預設效果門檻」，跑出難看數字照登——登難看數字傷的是一個 benchmark 段落，移動門柱傷的是整份誠信文件。

**第 3 件：D2 補實作，D4/D5 明文降級——兩路分歧選 D2 這一路。**
理由三條，按硬度排：

1. **D5 的停損幾乎必然觸發，而且觸發了也沒有然後。** 硬前提缺失是既成事實：STATUS §6 第 3 項「`get_dataset_queries` 回傳 total 為 0，沒有輸入資料」。8 小時取資料停損的最可能結局是燒掉一天確認死路；就算取到部分資料，接上 LLM 後的評測若靠自植查詢補分母，等於在剛清完的驗證誠信傷口上再開一刀。
2. **D2 的投入產出比是五類缺口中最高的，且有官方 ground truth。** 確定性規則（SPEC D2「觀測間隔 > 3 × 宣稱週期」）、官方 `nyc-taxi` datapack 自帶「planted **freshness** issues」（BRIEF 8.5）、順帶把「A 層開發集只用 1/3」的缺口關掉一格。做完可講「三類實作＋兩類明文降級」，宣稱與程式碼對得上。
3. **斜角敘事不靠 D5 運行也站得住，靠假資料跑 D5 反而毀掉它。** N4（Pinterest，「the failure mode is silent」，提問者是評審）的對位改放 README 邊界段：「D5 的確定性預篩與判讀骨架已實作、引文閘已測，缺真實查詢紀錄輸入——這是我們不假造的東西」。對 Aman 這席，一個誠實標界的半成品加上可信的 D1/D2/D3，比一個灌了合成輸入的「完整」D5 更像他會採用的東西——他的痛點本來就是 silent failure，而合成輸入正是另一種 silent failure。

工時 1.5–2 天（偵測器與測試 1.5，含進 baseline 對照；降級聲明半天）。不做的代價：宣稱面積停在 2.5/5 類，「官方 datapack 自帶 ground truth 卻沒用」在評審眼裡是顯眼的未撿之球；且第 2 件的凍結一旦打下，D2 就永遠進不了凍結範圍內的正式數字。

**刻意不做的**：D5 接真 LLM（上述）、Review UI（`--approve` 已堵住實質缺口，UI 是形態問題）、程序級憑證分離（README 標界即可，15 天內做完的價值低於其排擠成本）、內部 holdout（第 2 件的凍結後新來源已覆蓋其目的）。

---

## 4. 對 BRIEF 五條評分標準的現在位置

1. **Use of DataHub：仍是五條中位置最好，本輪再進一格。** 閉環未變（寫回→read-back VERIFIED→重掃消失），demo 現在含兩次拒絕且可重跑；5/7 工具有了declared理由。缺的是 L3 可見證據載體（STATUS §6 第 14 項：UI 截圖與 URN 清單）——屬第 1 件工作。
2. **Technical Execution：中上，上輪的雷拆掉大半。** claims 與 code 的三處裂縫（C1/C2/C5）分別以撤回、17 項清單、`check_approval()` 處置；「Does the code do what the submission claims?」現在大體成立。殘餘風險移到兩處：README 定稿時怎麼寫（寫回任何「holdout」式措辭立刻復發），與 §1.3 的四個省略。
3. **Originality：中，本輪唯一原地踏步的一條。** 兩個舉證器依然缺席：`b2_datahub_native` 不存在（STATUS 自認「Originality 條款想要的 `b2_datahub_native` 對照目前沒有」）、Cloud Context Hub 邊界聲明無載體（README 內容仍是情報缺口）。斜角站位本身仍優，但「clearly go beyond features DataHub already provides out of the box」目前沒有任何對照證據，全靠讀者體會。
4. **Real-World Usefulness：中上，微升。** 真實表棄權範例（25 張、14 棄權、0 誤報）是給「real data platform team」看的正確證物；DEPRECATION 6/30 照實分開報維持可信。弱點未變：付錢者原型（Aman）最痛的 D5 不可運行。
5. **Submission Quality：仍是最弱，且仍接近零。** 影片未錄、repo private、Devpost 未交、命名分裂（sentinel/StillTrue）。examples 與 make demo 的補齊讓「從零到滿」的距離縮短，但可見度本體還是零。

**最弱的一條：Submission Quality**——同上輪，這是排程使然，做了就補上。
**最危險的一條：本輪換人，從 Technical Execution 換成 Originality。** 理由：Technical Execution 的雷是「已埋好、會爆的陳述」，本輪已用撤回拆除；Originality 是唯一一條**目前拿不出任何肯定證據**的——沒有 b2 對照、沒有邊界聲明、D5 停擺後「第五類 agent」只剩敘事。評審席上坐著 Nick Adams（四類 agent 清單作者）與 Maggie Hays（DataHub Founding PM），「這跟我們現成的 Quality skill 差在哪」是他們職務上必然會問的問題，而現在的答案是空白。它的解法散在三件工作裡：b2 對照（若第 3 件工時允許，補在 D2 的 baseline 表）、邊界聲明（第 1 件 README）、凍結後 holdout（第 2 件，「有轉移證據的漂移偵測」本身就是與現成功能的區隔）。

---

## 情報缺口彙總（本輪）

1. README 現況全文與 SPEC §5 首屏規格達成度（僅知揭露了 D2/D4 與 5/7 工具兩件事）。
2. 冪等鍵是否為 SPEC 的 `SHA256(entity_urn + aspect + proposal_hash)` 公式（兩輪未答）。
3. PolicyGate aspect 白名單實際內容（兩輪未答）。
4. B1「只看覆蓋率」與 DataHub 現成 Quality skill 的等價性（兩輪未答，見 §1.3 第 2 點）。
5. dbt_shopify 2,496 筆負例上的誤報數（新，見 §1.3 第 1 點）。
6. showcase-ecommerce 25 張表的選樣方式（新，見 §1.3 第 3 點）。
7. `--approve` 核准紀錄的存放位置與生命週期（核准是否入 ledger、可否撤銷）。
8. VALIDATION-INTEGRITY 的 commit 時間戳未經對 repo 直接核驗（本審查無 repo 存取；該檔主張可核，列此存查）。
