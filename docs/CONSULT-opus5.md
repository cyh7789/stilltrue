# OPINION — 三個決定的第二意見

> 審查日：2026-07-26。僅用本目錄檔案，未上網。
> 引文皆為原文；查不到的標「情報缺口」。

---

## 開頭三句話結論

- **決定 1（41% 原封不動發表）：有條件同意——但 README 首屏的呈現方式必須改，否則這個決定會傷你。**
- **決定 2（D2 結案）：推翻——你放棄得太早，有一條你沒試的路，且成本低。**
- **決定 3（「不存在本身就是答案」）：有條件同意——論證本身站得住，但現在的形態讓評審必須自己拼出結論，Nick Adams 和 Maggie Hays 不會替你拼。**

---

## 決定 1：凍結 holdout 跑出 41%，原封不動發表

### 你的理由

「修到跟開發集一致就不是 holdout 了。」

### 我的判定：有條件同意，但條件很重

你的核心邏輯是對的。`HOLDOUT-REPORT.md` 自己寫得最清楚：

> A holdout that gets fixed until it agrees with the development set is a development set.

這是方法論上的正確立場，兩輪審查都沒有推翻它。`VALIDATION-INTEGRITY.md` 也已把凍結流程做到位：`freeze.json` 釘住 hash、選源規則先提交、只跑一次、`freeze.py --check` 可驗。這是你整個提交裡最乾淨的一件事。

**但問題不在你的決定本身，在你打算怎麼呈現它。**

你說「README 首屏改成 41% 打頭」。這裡有一個你沒想到的第三條路，見下。

### 評審看到 41% 的第一反應

你問的問題是對的，但答案不是二選一。

**會細讀的評審**（Tim Bossenmaier、Mike Burke，或 BRIEF §6 保留條款的「automated AI-driven analysis」）：看到 41% 加上完整的 `HOLDOUT-REPORT.md` 時序，反應是「這人知道自己在做什麼」。`HOLDOUT-REPORT.md` 把兩類失敗模式都寫清楚了，這是加分。

**只看首屏和影片的評審**：取決於 41% 旁邊寫了什麼。如果首屏只有一個數字，沒有脈絡，第一反應是「這東西不準」。BRIEF §4 明寫：「Judges are not required to test the Project and may choose to judge based solely on the text description, images, and video provided in the Submission.」這不是少數情況，這是允許的預設行為。

### 第三條路

不是「41% 打頭」，也不是「藏起來」。

**把 41% 變成方法論的展示，而不是準確率的宣告。**

首屏的框架應該是：「我們做了一件大多數 hackathon 作品不做的事——在提交前用一個從未接觸過的來源做凍結驗證，結果是 41%，我們照登。」這把 41% 從「準確率低」變成「誠信高」的證據。

具體寫法：首屏一行說明凍結流程（選源規則先提交、只跑一次、結果不改），然後並排兩個數字：

| | 開發 benchmark | 凍結 holdout（未見過） |
|---|---|---|
| IDENTIFIER_CHANGE recall | 90%（dbt_shopify，開發期塑造過規則） | **41%（dbt_fivetran_log，凍結後單跑）** |

這個呈現方式讓評審看到的不是「41% 的系統」，而是「一個知道 90% 是擬合數字、主動揭露轉移落差的團隊」。`VALIDATION-INTEGRITY.md` 已把這個故事寫好了，首屏只需要把它壓縮成兩行。

### 關於「剩 15 天，應不應該修」

**不應該修。** 兩輪審查都沒有說你應該修，我也不說。理由：

1. 修完兩類失敗再重新凍結，需要一個你沒有的第三個來源——`HOLDOUT-REPORT.md` 已說明兩類失敗的機制，但新來源可能暴露第三類失敗，你沒有時間再跑一輪。
2. 你估的 1.5 天重跑成本是樂觀數字，不含新來源可能又跑出難看數字的應對時間。
3. 最重要的：`REVIEW-r2-duo.md` §4 明確說「Submission Quality 仍接近零」，那裡才是你現在最大的名次缺口，不是 41%。

**結論：決定本身對，呈現方式要改。首屏不是「41% 打頭」，是「凍結流程 + 並排兩個數字 + 一行說明限制」。**

---

## 決定 2：D2 新鮮度偵測宣告做不出來，結案

### 你的理由

四條實測都沒有資料：76 張表 0 筆描述宣稱更新週期、`get_entities` 不回傳時間戳、`get_dataset_assertions(FRESHNESS)` 全庫 0 筆、`nyc-taxi` datapack 不在 registry。

### 我的判定：推翻

你沒試的路是：**`nyc-taxi` 不是 datapack，但它是一個真實存在的公開資料集，BRIEF 說它有 planted freshness issues，這個 ground truth 可以用別的方式取得。**

`D2-FEASIBILITY.md` 的結論是：

> Implementing D2 here would mean writing both sides ourselves: descriptions that claim cadences we invented, checked against timestamps we planted.

這個結論的前提是「兩側都要自己造」。但你只確認了 `datahub datapack load nyc-taxi` 失敗，沒有確認 NYC Yellow Taxi Trip Records 本身是否有公開的 schema 歷史和更新週期文件。

**你沒試的路：**

BRIEF §8.5 說 `nyc-taxi` 是「NYC Yellow Taxi Trip Records（約 500k trips）。3-stage pipeline with planted freshness issues」。這個資料集是 NYC TLC 的公開資料，有公開的 data dictionary 和已知的更新週期（月更）。你已經有 `bench/oracles/mine_drift_labels.py` 的機制，也已經對 NYC TLC 做過 schema diff（`VALIDATION-INTEGRITY.md` 的 TLC 2/2 就是這樣來的）。

問題是：你有沒有試過直接用 NYC TLC 的公開 schema 歷史，找一個描述宣稱更新週期的欄位，然後用 TLC 的公開更新紀錄當「現實側」？

`D2-FEASIBILITY.md` 沒有記錄這條路被試過。它記錄的是 DataHub catalog 裡沒有資料，但 D2 的「現實側」不一定要從 DataHub 取——你的 D1/D3 的現實側也是從 git commit 和 schema diff 取的，不是從 DataHub 取的。

**另一條更快的路：**

`REVIEW-r2-duo.md` §3 第 3 件已經說了：「D2 的投入產出比是五類缺口中最高的，且有官方 ground truth。確定性規則（SPEC D2「觀測間隔 > 3 × 宣稱週期」）、官方 `nyc-taxi` datapack 自帶「planted freshness issues」（BRIEF 8.5）、順帶把「A 層開發集只用 1/3」的缺口關掉一格。」

這條路的前提是 `nyc-taxi` 的 planted issues 可以用其他方式取得。你沒有確認這個前提是否成立，就結案了。

### 但有一個邊界

你說「自己植入時間戳與週期宣稱＝自己出題自己改考卷，這條我已經排除」——這條排除是對的，我同意。如果 NYC TLC 的公開資料也找不到任何描述宣稱更新週期的欄位，那 D2 確實做不出來，結案是對的。

**但你需要先確認這條路是否可行，再結案。** 現在的 `D2-FEASIBILITY.md` 沒有記錄這條路被試過。

### 時間成本

如果 NYC TLC 公開資料有可用的 ground truth：D2 的確定性規則本身很簡單（觀測間隔 > 3 × 宣稱週期），`REVIEW-r2-duo.md` 估 1.5–2 天。如果沒有：確認失敗本身只需要幾小時，然後你可以用更強的理由結案。

**結論：給這條路 4–8 小時的停損時間。如果 NYC TLC 公開資料找不到任何描述宣稱更新週期的欄位，D2 結案是對的，且你的 `D2-FEASIBILITY.md` 會更完整。如果找到了，D2 可以做，且是你剩下 15 天裡投入產出比最高的一件事。**

---

## 決定 3：Originality 的缺口，用「它不存在本身就是答案」回答

### 你的理由

`NATIVE-COMPARISON.md` 論證 DataHub 開源版沒有讀描述內容判斷正確性的能力，證據是各 skill 的自述範圍、`datahub-search` 把 audit 定義為「how complete is our metadata」、assertion 七種型別主體全是資料。

### 我的判定：有條件同意，但現在的形態不夠

論證本身是對的。`NATIVE-COMPARISON.md` 的核心區分是：

> DataHub open source has rich machinery for whether a description exists, and none for whether it is still true.

這個區分是真實的，引文也是原文（`datahub-search` 的 audit 定義、assertion 七種型別）。評審如果細讀，會點頭。

**但問題是：Nick Adams 和 Maggie Hays 不會從 `NATIVE-COMPARISON.md` 讀到這個結論。**

### 為什麼會被當藉口

`REVIEW-r2-duo.md` §4 說得很準：

> 評審席上坐著 Nick Adams（四類 agent 清單作者）與 Maggie Hays（DataHub Founding PM），「這跟我們現成的 Quality skill 差在哪」是他們職務上必然會問的問題，而現在的答案是空白。

`NATIVE-COMPARISON.md` 的問題不是論證錯，是**它要求評審自己走完最後一步**。文件說「DataHub 的 audit 問的是 complete，不是 correct」，但沒有直接說「所以 StillTrue 做的事，DataHub 的任何現成工具都做不到，包括 Quality skill」。

Nick Adams 寫過四類 agent 清單（Data Analytics、Data Quality、Data Steward、Data Engineering）。他看到 `NATIVE-COMPARISON.md` 的第一個問題不是「這個論證對不對」，而是「Data Quality Agent 不就是做這個的嗎？」你的文件沒有直接回答這個問題。

`NATIVE-COMPARISON.md` 的 skill 表格列了 `datahub-quality`：「create or run assertions, check assertion outcomes, raise or resolve incidents」，然後說「no — data values」。但這個「no」對 Nick Adams 來說不夠——他需要看到「Data Quality Agent 的 assertions 主體是資料值，不是描述文字；StillTrue 的主體是描述文字，這是不同的問題」這句話明確寫出來。

### 具體要補什麼

**一段話，不是一份文件。** 在 README 的 Originality 段（或影片的對應位置），直接寫：

> DataHub's Data Quality Agent creates and runs assertions on data values — row counts, column distributions, freshness of the underlying data. StillTrue's subject is the documentation itself: it asks whether the prose a human wrote still matches the schema and lineage DataHub stores. DataHub's assertion type system has no type whose subject is documentation (`DATASET`, `FRESHNESS`, `VOLUME`, `SQL`, `FIELD`, `DATA_SCHEMA`, `CUSTOM` — all about data). You cannot write "assert this description still names columns that exist" in DataHub today, not because it would fail, but because the type system has no place to put it.

這段話讓 Nick Adams 不需要自己拼。`NATIVE-COMPARISON.md` 的論證是對的，但它是給願意細讀的人看的；README 和影片需要把結論直接說出來。

### 關於 `b2_datahub_native` 缺席

兩輪審查都說這是 Originality 最大的缺口。你的回答是「做不出來的理由本身就是答案」。這個回答在邏輯上是對的，但在評審動線上是弱的——因為它要求評審先接受「做不出來」這個前提，再接受「所以是原創」這個結論。

如果 D2 可以做（見決定 2），D2 的 baseline 表可以順帶補一個 `b2_datahub_native` 欄位，內容就是「DataHub Quality skill 對 D2 的輸出：N/A（assertion 主體為資料值，不為描述文字）」。這不是造一個假對照，而是把「做不出來」這件事放進一個可以被評審直接看到的表格裡。

**結論：論證本身站得住，但需要在 README 和影片裡把最後一步說出來，不能讓評審自己拼。如果 D2 可以做，順帶補一個 `b2_datahub_native` 欄位讓「做不出來」變成可見的表格項目。**

---

## 時間配置

你問：如果我判你錯了，要挪多少天去修，從哪裡挪。

| 決定 | 判定 | 需要挪的時間 | 從哪裡挪 |
|---|---|---|---|
| 決定 1 | 有條件同意（呈現方式要改） | 0.5 天（改 README 首屏框架） | 提交面工作的 4 天裡吸收 |
| 決定 2 | 推翻（先給 4–8 小時停損） | 0.5 天停損確認 + 若可行 1.5–2 天實作 | 從提交面 4 天裡挪 1 天；若 D2 可行，剩餘 3 天提交面仍夠用 |
| 決定 3 | 有條件同意（需補一段話） | 0.5 天（寫那段話 + 放進 README 和影片腳本） | 提交面工作裡吸收 |

**總計：最多挪 2.5 天去修，剩 12.5 天做提交面。** 兩輪審查都說提交面估 4 天，12.5 天綽綽有餘。

**硬約束**：如果 D2 可以做，時間軸是「D2 程式碼（1.5 天）→ 凍結（0.5 天）→ 提交面（4 天）」，凍結必須在所有程式碼改動之後。這個順序不能反。

---

## 一個你沒問但應該知道的事

`REVIEW-r2-duo.md` §4 說「最危險的一條從 Technical Execution 換成 Originality」。我同意這個判斷，但我要補一個更具體的風險：

**Nick Adams 在評審席上，而他的四類 agent 清單裡有 Data Steward Agent，其描述是「自動監控、執行、維護資料政策；依 platform/domain/ownership 找目標表，將 schema metadata 與關鍵 glossary terms 交叉比對後套用 glossary terms 與描述」（BRIEF §8.1）。**

StillTrue 的 D1/D3 做的事（description × schema/lineage）和 Data Steward Agent 的描述有重疊。如果 Nick Adams 問「這跟 Data Steward Agent 差在哪」，你現在的答案是「Data Steward Agent 是寫入，StillTrue 是偵測」——這個區分是真實的，但 `NATIVE-COMPARISON.md` 沒有明確說出來。

把這個區分加進 README 的 Originality 段，和上面說的那段話一起寫。
