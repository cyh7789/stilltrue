# StillTrue（Build with DataHub: The Agent Hackathon）— 接手紀錄

> 更新 2026-07-26，核心重建後。截止 2026-08-10 17:00 EDT ＝ 台北 8/11 05:00。
> repo `cyh7789/stilltrue`（private）。前身 Serow / Blast-Radius Guard 已封存。

## 一句話

DataHub 裡人寫的文件與 schema 現實脫節之處，證據取自 DataHub 自己的變更帳本，
附證據提出修正，經人確認後寫回 graph。投賽道 Agents That Do Real Work。

## ⚠️ 先讀這段：核心已經整個換過

**舊設計（已死）**：用正則從描述裡撈出「看起來像欄位名」的 token，
再用字串相似度猜有沒有被改名。四輪加標記清單修誤報，每個新語料都冒出新形式。
跨三個語料的成績是 **120 次斷言、17 次對**。

**現在的設計**：問 DataHub 什麼變了。斷言需要「這個 token 曾是這張表的欄位」的證據：
現況 schema 有近似欄位（改名），或變更帳本記錄它離開（刪除）。其餘一律棄權。

`detectors.py` 裡**零英文詞組清單**。列舉值、鄰表名、實體型別、未展開 Jinja
不會出現在 schema 變更帳本裡，所以一條排除規則都不用寫。

換設計的原因寫在 memory 的 `survey-platform-surface-before-building`：
我沒先把 DataHub 的能力面列完就開工，花四輪重造它已經publish的東西。

## 兩個偵測器

| | 抓什麼 | 證據來源 |
|---|---|---|
| `D1_SCHEMA_BREAK` | 描述**文字裡提到**已消失的欄位 | timeline 變更帳本 ／ 現況 schema 近似比對 |
| `D1_ORPHANED_DOC` | 描述**掛在**已消失的欄位上 | `editableSchemaMetadata` vs 現況 schema |

第二個是修 oracle 才發現的缺口。它抓的東西**今天沒有任何介面看得見**：
DataHub 不清理、UI 沒有欄位可以渲染、Agent Context Kit 整個 aspect 丟掉。

## 實測數字（2026-07-26 重跑確認）

| 偵測器 | 語料 | 結果 | 身分 |
|---|---|---|---|
| schema break | NYC TLC 41 個月真實發布歷史 | 41/41 月精確、0 誤報 | 開發 benchmark |
| orphaned doc | dbt_hubspot | 4/4、432 負例 0 誤報 | 開發驗證 |
| orphaned doc | **dbt_iterable** | **2/2、199 負例 0 誤報** | **凍結 holdout，單跑** |

57 測試綠。`bench/freeze.py --check` 綠（6 檔，凍結於 commit `ca13e88`）。

TLC 重播 2026-07-26 重跑過，涵蓋 TLC 已發布的全部 41 個月（2023-01..2026-05）。
逐月結果在 `bench/tlc-replay-results.jsonl`；schema 快取在 `bench/oracles/tlc-schemas.json`，
所以重跑不用再打 CDN。

⚠️ 這輪抓到一個**我自己犯的、跟本專案主題同型的錯**：舊 harness 報 27／31 個月，
說「其餘尚未發布」——那是 CloudFront 限流被誤讀成事實。`fsspec` 對限流和檔案不存在
拋同一個 `FileNotFoundError`，而這個 CDN 背後的 S3 沒開 ListBucket，
所以連不存在的檔案也回 403 不是 404，狀態碼本身分不出來。
現在 `is_published()` 用哨兵月份（2023-01）分辨：哨兵也連不上就是限流，
整個跑停掉而不是把限流寫成關於資料的結論。

⚠️ 兩個誠實註記已寫進報告：holdout 只有 2 個正例（證明機制可轉移，不證明比率）；
選源門檻仍用舊 oracle 評估，分母只有 2 就是這個不一致的顯影。

## 四支上游 PR（全部 open）

| PR | repo | 內容 |
|---|---|---|
| **#18622** | datahub | dataset 層描述解析（`resolve_description()`） |
| **#18628** | datahub | 欄位層 editable 描述——Kit 抓了資料、刪掉、從沒合併。docstring 承諾的行為不存在 |
| **#18630** | datahub | `list_schema_fields` 對沒有 schema 的 dataset 直接炸（`.get(k, {})` 遇到顯式 null）|
| **#49** | datahub-skills | skill 改成變更帳本做法，含兩個踩過的坑 |

#18630 是全機掃描時真的踩到的：`healthcare.main.patient_analytics` 掃不了。
兩段式提交（測試紅 → 修綠），395 測試過。

#18628 的 `python-lint` 曾紅過一次——我加的測試裡兩個 dict literal 超過 88 欄，
`ruff format --check` 擋下來。已用 CI 釘的 `ruff==0.15.22` 重排推上去。
**教訓：改上游前先裝它釘的 lint 版本跑一次，本地新版 ruff 的規則集不一樣。**

維護者尚未審任何一支。

## 平台上的三個發現（提交敘事可用）

1. **Timeline 有，agent 碰不到。** 九個分類，寫在 skills repo 自己的 agent CLI 參考裡，
   但五個 skill 零使用、Kit 三十八個匯出符號裡沒有。
2. **DataHub 的 schema differ 是按位置比對。** 同一版同時刪欄、改名、換型別就會吐出
   沒發生過的改名（`RatecodeID to Airport_fee`）。自我修正：被宣稱改名走的欄位還在 schema 裡，
   用現況過濾就只剩真的。
3. **孤兒描述沒有任何介面看得見**（見上）。

## 舊語料為何撤下

`dbt_shopify` / `dbt_fivetran_log` / `dbt_hubspot` 在舊設計下的數字全部撤下。
舊 oracle 標的是「描述後來被編輯過」，那是文件編輯行為。
`dbt_shopify` 10 筆 IDENTIFIER_CHANGE 正例裡，**9 筆的被引用 token 在漂移窗兩端
都不是該 model 的欄位**——是列舉值（`fixed_amount`）與上游 model 名。
舊偵測器正是打到那些才算命中，標籤型 oracle 對「因錯誤理由給出正確判定」也記一分。

新 oracle（`mine_orphaned_docs.py`）標的是可機械判定的：
欄位離開 model 的 SQL、它的 yml 描述還留著。

## 剩下的

**全部是把已有的東西變成評審看得到的**：

- ~~L3 可見證據~~ → `docs/L3-EVIDENCE.md` + `docs/evidence/*.png`，
  截圖由 `scripts/capture_ui.py` 從 URN 產生，可重跑。
  現在 TLC 那筆同時帶兩個偵測器的發現（schema break + orphaned doc），
  孤兒描述是**真實改名造成的**，不是道具表。`orphan_probe*` 三張已刪。
- 影片（素材現成：`make demo` 的 NOT_APPROVED / STALE 兩顆鏡頭、`airport_fee` 由 DRIFT 轉 CURRENT，
  加上 L3-EVIDENCE 的四張前後對照）
- repo 轉 public + About 區 Apache-2.0
- Devpost 送件。**不要勾** Feedback Survey 獎（與其他獎互斥）

這些不是卡點，是最後一哩。**不要再把它們列成待辦清單當進度回報。**

⚠️ 凍結生效中。再動 `detectors.py` / `adapter.py` / `evidence.py` /
`replay_tlc.py` / `mine_orphaned_docs.py` / `run_orphan_bench.py` 任一個，
`freeze.py --check` 就紅，holdout 的 2/2 可信度跟著沒。要改就得跑第五輪：
修 → 重凍結 → 換新來源單跑。前四輪流程都在 git 歷史裡，可重複。

## 外部意見（都在 repo）

- `docs/REVIEW-r1-{codex,duo}.md`、`docs/REVIEW-r2-{codex,duo}.md` — 兩輪四份審查
- `docs/CONSULT-{fable,opus5}.md` — 對三個已拍板決定的第二意見。
  Fable 推翻了「不修那兩類失敗」，並算出我沒算過的精確率 9.4%（96 筆警報 9 筆真）

⚠️ **派 duo 的前置條件**（踩過五種死法）：工作目錄必須是 git repo 且有 `.claude/rules/`；
websocket 1006 斷線會讓整回合工具通道失效，那是基礎設施問題不是任務問題，換目錄重派。

## 踩過的坑

1. **開工前沒列平台能力面** — 最貴的一個，花四輪重造 DataHub 已有的東西。已寫進 memory。
2. **DataHub 有兩個描述欄位**，UI 顯示 `editableProperties`。欄位層同理，且 Kit 會丟掉。
3. **不要把兩側都 lower() 再比對** — 會抹掉大小寫改名這個要抓的訊號。
4. **set 迭代順序隨 PYTHONHASHSEED 變** — finding id 依位置編號，同一個 process 內測不出來，
   回歸測試要跨子程序跑不同 seed。
5. **只報 recall 不報 precision 等於宣稱了沒寫下來的東西。**
6. **oracle 標錯東西比偵測器寫錯更難發現** — 標籤看起來合理、數字跑得出來，
   但量的不是你要的。查法：抽幾筆正例，確認「被引用的 token 在漂移窗兩端是不是真的是該表欄位」。

## 相關路徑

| 內容 | 位置 |
|---|---|
| 本專案 | `/Volumes/CyhSSD/Dev/hackathon/active/context-drift-sentinel` |
| 賽事情報基地 | `/Volumes/CyhSSD/Hackathon/active/datahub/` |
| datahub fork（PR 用） | scratchpad `datahub-fix/`，sparse checkout |
| skills fork | scratchpad `skills-fork/`，PR 分支 `feat/context-drift-skill` |
| dbt 語料 clone | scratchpad `holdout-search/`，compact 後可能已清 |
