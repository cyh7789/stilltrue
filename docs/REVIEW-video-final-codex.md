# 最終影片腳本審查

查核日期：2026-07-26（Asia/Taipei）

## 結論

**目前不宜直接開拍。** 孤兒描述的兩張畫面與像素差異已經成立，先前「同一檔案重複使用」的缺口確實消失；但 Shot 7 還藏著一段未標記的 DataHub 現場寫入與錄製，Shot 9 目前缺少命令必要的 `dbt_iterable` 本機副本，Shot 11 則沒有片尾卡檔案，而且儲存庫沒有 `LICENSE`，GitHub 也辨識不到授權。旁白另有至少八個未被「Claims to keep off the narration」涵蓋的可反駁主張，其中 Shot 2、3、8 可由目前程式碼或結果直接推翻。

## 一、先處理會擋拍攝的缺陷

### 1. Shot 7 是未標記的現場鏡頭

Shot 7 要拍的是 `bash scripts/prove_invisible.sh` 的終端機輸出（`docs/VIDEO-SCRIPT.md:27`），但這支腳本不是對兩張既有 PNG 做唯讀比對：它會重建基準測試、寫入修正文、擷取第一張圖、移除 orphan、再擷取第二張圖（`scripts/prove_invisible.sh:17-42`）。因此它和 Shot 4–5、Shot 9 一樣需要運作中的 DataHub 與連續現場錄影，且會覆寫 `docs/evidence/05-orphan-present.png`、`06-orphan-removed.png`（`:28-42`）。腳本把「只有兩段現場終端機錄影」寫在 `docs/VIDEO-SCRIPT.md:13-15`，又把「其他都是已提交檔案或 `bash scripts/prove_invisible.sh`」寫在 `:49`；這把一支本身會現場寫入、擷取的腳本誤列成靜態素材。

本輪 `curl --max-time 3 http://localhost:8080/config` 與 `http://localhost:9002` 都回 HTTP 200，`.venv/bin/stilltrue --help` 也成功，所以環境今天可錄；但我沒有執行 `prove_invisible.sh`，因為它會改變 DataHub 狀態並覆寫被審查的證據檔。這是標記與拍攝排程缺陷，不是目前環境故障。

### 2. Shot 9 的現場命令今天缺一個必要輸入

Shot 9 的完整命令需要 `<clone>` 與 labels（`docs/VIDEO-SCRIPT.md:41-47`；`bench/run_orphan_bench_datahub.py:35-38`）。本輪在 `/tmp/dbt_iterable`、專案相鄰目錄與 `/Volumes/CyhSSD/Dev/hackathon/active/dbt_iterable` 都找不到 Git clone；直接執行 `python3 bench/run_orphan_bench_datahub.py` 只印 Usage 並以 1 結束。已提交報告可拍成靜態表格，且確實記錄一般模式 2/2、mutation 0/2（`bench/HOLDOUT-orphan-iterable-datahub.md:48-54`），但腳本指定的是「Terminal run」，所以若不先取得本機副本，今天不能照分鏡拍現場終端機。這個需求在「Footage that must be recorded」有揭露，不是隱藏缺陷；它仍是開拍前置條件。

### 3. Shot 11 沒有可引用的片尾卡，而且 Apache-2.0 尚未成立為儲存庫授權

Shot 11 只描述「Title card: name, repo URL, Apache-2.0」，沒有命名來源檔或產生命令（`docs/VIDEO-SCRIPT.md:31`），因此不符合腳本自己在 `:13` 所稱「Every shot names the file or command that produces it」。儲存庫網址可由 `git remote -v` 取得，README 也在 `README.md:454-456` 寫了 Apache 2.0；但 `git ls-files` 找不到 `LICENSE`／`COPYING`／`NOTICE`，`pyproject.toml:1-13` 也沒有授權欄位，本輪 `gh repo view cyh7789/stilltrue --json licenseInfo` 回 `licenseInfo:null`。在這個狀態下，能做出寫著 Apache-2.0 的卡，卻不能用儲存庫內授權檔支持它。

### 逐鏡素材判定

| Shot | 判定 | 今天是否能從指定來源製作 |
|---|---|---|
| 1 | 可拍 | `docs/evidence/02-before-columns.png` 已提交；本輪 OCR 同時讀到左側 `Airport_fee` 與右側 `airport_fee`，符合 `docs/VIDEO-SCRIPT.md:21`。 |
| 2 | 可拍 | `docs/evidence/04-after-columns.png` 已提交；本輪 OCR 讀到左右皆為 `Airport_fee`，符合 `docs/VIDEO-SCRIPT.md:22`。旁白的「human confirmed」另見第三節，素材存在不代表主張成立。 |
| 3 | 可拍 | `bench/REPORT.md:20-25` 有 B1 與 StillTrue 兩列，可直接渲染；旁白說分數 perfect 則不成立。 |
| 4 | 可現場錄製 | DataHub 兩個本機端點今天均回 200，CLI 存在；指定命令與三項 finding 也由 `docs/L3-EVIDENCE.md:48-63` 支持。未實跑，因為 `make demo` 會重載並寫入 DataHub（`Makefile:20-26`）。 |
| 5 | 可接 Shot 4 現場錄製 | `scripts/demo.sh:18-32` 依序產生 NOT_APPROVED、STALE、VERIFIED；必須保留同一次執行的要求成立（`docs/VIDEO-SCRIPT.md:35-39`）。 |
| 6 | 可拍，關切消失 | 不必依賴當下 timeline：完整 curl 與 MODIFY 輸出已提交於 `docs/L3-EVIDENCE.md:162-179`。若導演堅持拍真正的 shell curl，則它也是未標記的現場素材；但指定檔案本身已足以製作畫面。 |
| 7 | **未標記的現場鏡頭** | 兩張 PNG 與差異數字都已存在，但要照分鏡拍 `bash scripts/prove_invisible.sh` 的輸出，就必須執行會寫入 DataHub 並重新擷取的完整流程（`scripts/prove_invisible.sh:17-42`）。左側 aspect curl 的完整命令與輸出只在 `docs/L3-EVIDENCE.md:194-204`，Shot 7 本身沒有命名該檔。 |
| 8 | 可拍 | `bench/REPLAY-REPORT.md:22-36` 與 `bench/tlc-replay-results.jsonl` 已提交；本輪 `jq -s` 得 41 rows、41 correct、0 wrong、1 quiet、1 onset、39 holds。旁白的「written once」另見第三節。 |
| 9 | **現場錄製目前缺本機副本** | 靜態 2/2、0/2 表存在（`bench/HOLDOUT-orphan-iterable-datahub.md:48-54`），但指定終端機執行的 `<clone>` 目前不在查核位置。 |
| 10 | 今天可錄，但不是已提交素材 | 本輪四次 `gh pr view` 確認 `datahub#18622`、`#18628`、`#18630`、`datahub-skills#49` 皆為 OPEN，頁面存在；儲存庫沒有四張 PR 截圖，需另做瀏覽器現場擷取。這推翻 `docs/VIDEO-SCRIPT.md:49` 的「Everything else is a committed file」，但不構成今天無法取得的素材。 |
| 11 | **缺來源與授權證物** | 沒有片尾卡檔案或產生命令，且沒有已追蹤的 `LICENSE`；只能支持儲存庫名稱、URL 與 README 自述，不能支持 GitHub 可辨識的 Apache-2.0 授權。 |

### 孤兒畫面缺口已消失

這項先前關切已關閉。本輪實際執行：

```text
$ shasum -a 256 docs/evidence/05-orphan-present.png docs/evidence/06-orphan-removed.png
05fcbc85…  docs/evidence/05-orphan-present.png
e369881e…  docs/evidence/06-orphan-removed.png

$ python3 scripts/diff_frames.py docs/evidence/05-orphan-present.png docs/evidence/06-orphan-removed.png
1440x900, 1296000 pixels
differing pixels: 110  (0.0085%)
all differences inside x 704-783, y 252-265
```

兩個雜湊不同，兩張圖皆為 1440×900；PNG 建立時間相差 12 秒。本輪對兩張完整圖片執行 OCR，差異位置的 chip 分別讀成 `12.0.0 - 13 seconds ago` 與 `12.0.0 - 25 seconds ago`，其他 OCR 文字一致。這重現 `docs/L3-EVIDENCE.md:228-256` 的數字與解釋；`scripts/diff_frames.py:17-39` 也確實逐像素比較兩個輸入，而非比較路徑或檔名。

## 二、時間

依腳本自己的逐鏡字數，總速率不是整數 155，而是 `440 / 170 × 60 = 155.29 wpm`。以這個速率分配每鏡容量，**真正讀不完的是 Shot 1 與 Shot 3**：

| Shot | 字數／秒數 | 局部速度 | 155.29 wpm 可容納 | 至少要刪 |
|---|---:|---:|---:|---:|
| 1 | 55／12s | 275.0 wpm | 31.06 字 | **24 字** |
| 3 | 30／8s | 225.0 wpm | 20.71 字 | **10 字** |

Shot 10 是 32 字／12 秒＝160 wpm，若要每鏡都不超過全片平均，需再刪 1 字；但 160 wpm 本身仍可清楚朗讀，不應和 Shot 1、3 的不可讀密度列為同級。Shot 7 是 81 字／32 秒＝151.9 wpm，數字雖大，時間也相應較長；其餘 shots 都在 147.3 wpm 以下。計算命令為一段以 `(shot, seconds, words)` 列表逐項印出 `words / seconds × 60` 與 `seconds × (440 / 170)` 的 Python 腳本；逐鏡字數總和也重新核得 440，與 `docs/VIDEO-SCRIPT.md:3-4` 相符。

## 三、「Claims to keep off the narration」不足

五項清單本身都值得保留，但它沒有攔住旁白欄現有的可反駁句子。不是只多一個第六項；至少有下列八項。

### 可由目前 repo 直接推翻

1. **Shot 2：「a human confirmed it」不成立。** 指定素材是一個連續 `make demo` run（`docs/VIDEO-SCRIPT.md:35-39`）；`scripts/demo.sh:26-32` 自己從 dry run 擷取 token，再把同一 token 傳給 commit command，中間沒有人工輸入。程式也明說 token 沒有 identity 或 privilege boundary，不能證明另一位 steward 審過（`src/stilltrue/proposal.py:99-114`；`README.md:416-422`）。「精確內容 token 已匹配」成立，「human confirmed」不成立。
2. **Shot 3：「A coverage check scores this table perfectly」不成立。** 畫面指定的 B1 列就是 1/2，不是 perfect（`bench/REPORT.md:20-25`）；B1 找到未文件化的 `cbd_congestion_fee`，只漏掉 rename（`:33-36`）。若這句想說 dataset-level description 存在，畫面卻展示 field-level B1 benchmark，兩者不是同一個分數。
3. **Shot 8：「The description is written once」不成立。** `replay_tlc.py` 每個月都建立帶有 `description=DESCRIPTION` 的 `Dataset` 並 upsert（`bench/oracles/replay_tlc.py:83-96`、`:114-123`）；只有 column documentation 受 `with_docs=(i == 0)` 限制。它是「同一段 dataset description 每月重寫、內容從未修訂」，不是只寫一次。41／41 與 1＋1＋39 仍成立，本輪 `jq -s` 已重算；錯的是 setup 敘述，不是結果數字。
4. **Shot 11：「Everything shown is in the repo」不成立。** Shot 4–5、7、9 是現場終端機畫面，Shot 10 是外部 GitHub 頁，Shot 11 的片尾卡也不存在；`docs/VIDEO-SCRIPT.md:24-31` 自己就列出這些來源。較窄的「產生命令與已提交證據都在儲存庫」也尚未完全成立，因為 Shot 10 沒命名 URL／命令，Shot 11 沒命名產生方式。

### 範圍過廣，評審可用現有材料反駁

5. **Shot 1：「Nothing failed」沒有證據，而且是全稱主張。** Repo 的 oracle 只證明 2023-02 schema 移除 `airport_fee` 並新增 `Airport_fee`（`bench/oracles/tlc-drift-events.json:2-12`）；它沒有檢查所有 query、model 或 consumer 是否失敗。「Every description … kept running」也把不會執行的描述寫成會 running。畫面能支持的是描述仍留在 catalog 且變舊（`docs/L3-EVIDENCE.md:27-46`），不能支持沒有任何下游失敗。
6. **Shot 3：「it is the one nobody is asking」過廣。** Repo 自己記載 DataHub Cloud Context Hub 會評估 context quality，只是 Cloud-only、private beta，且未確認是否做相同 description-vs-reality check（`docs/NATIVE-COMPARISON.md:131-146`、`:181-187`）。Open-source DataHub 沒有這個能力的窄版主張成立；「nobody」不成立。
7. **Shot 4：「No entry, no claim」只能限定在 broken-reference DRIFT。** `detect_schema_break` 確實要求 change-log departure 才輸出 broken-reference DRIFT（`src/stilltrue/detectors.py:267-297`）；但同一 scan 的 undocumented finding 由目前 fields 與 description coverage 產生（`:299-355`），orphan finding由 `editableSchemaMetadata` 對目前 schema 的差集產生（`:358-397`），都不需要 change-log entry。旁白緊接著說三項 findings，會使全稱版本被讀成三類都靠 timeline。
8. **Shot 7：「one DataHub cannot show you」過廣，且下一句自己反駁。** aspect API 正是 DataHub surface，旁白隨即說「The aspect API returns it」（`docs/VIDEO-SCRIPT.md:27`）；repo 的精確邊界是標準 dataset pages 不呈現、Agent Context Kit 不交付，但 aspect API 會回傳（`docs/L3-EVIDENCE.md:209-220`）。這也表示既有清單 `docs/VIDEO-SCRIPT.md:56-58` 的「不要說 invisible everywhere」尚未真正約束旁白。

### 逐鏡其餘主張的查核結果

- **Shot 1 的同頁矛盾與 2023-02 case rename 成立。** OCR 與 `bench/oracles/tlc-drift-events.json:2-12` 相符；只有「Nothing failed」與「description kept running」超出證據。
- **Shot 4 的三項 finding 與 broken-reference 機制成立。** 提交的 `findings.jsonl` 本輪以 `jq` 重算得 3 DRIFT、5 CURRENT，三個 DRIFT 分別是 SCHEMA_BREAK、UNDOCUMENTED、ORPHANED_DOC；DataHub 誤配 `airport_fee to cbd_congestion_fee` 也已在 `docs/L3-EVIDENCE.md:70-83` 坦白揭露。只有「No entry, no claim」必須限縮到 SCHEMA_BREAK。
- **Shot 5 成立。** proposal hash 除了 before／after content，也涵蓋 URN、aspect、subject、verdict 與 evidence（`src/stilltrue/proposal.py:50-62`）；無 token 與不符 token 分別回 NOT_APPROVED／STALE（`:99-130`），executor 寫後重讀，不一致不會報 VERIFIED（`src/stilltrue/executor.py:143-155`）。本輪 `python3 -m pytest -q` 得 `67 passed in 0.41s`。
- **Shot 6 成立，但「same log」是同一 timeline service、不同 category。** detector 讀 TECHNICAL_SCHEMA（`src/stilltrue/adapter.py:171-200`），畫面中的 correction 是 DOCUMENTATION（`docs/L3-EVIDENCE.md:168-179`）。這仍是 DataHub 自己的 change log，不是 StillTrue 自寫紀錄。
- **Shot 7 的像素數、clock 與 UI merge 機制成立。** 本輪已重現差異；`docs/L3-EVIDENCE.md:209-220` 說明標準頁面只迭代 current fields。須刪掉的只是廣義「DataHub cannot show you」。另有一個 provenance 風險：這筆 steward note 是 benchmark builder 透過 API 寫入的 fixture（`bench/oracles/build_tlc_benchmark.py:76-96`），不是 repo 證明的真實使用者歷史；若「Someone documented」被理解為真實事件，評審可打開該檔反駁。
- **Shot 8 的結果成立，setup 的 written-once 不成立。** 41／41、0 wrong、1 onset、39 holds 均由本輪 `jq` 重算；`bench/REPLAY-REPORT.md:30-50` 也正確說這是狀態判定，不是 41 個事件。
- **Shot 9 成立。** mutation 在 `bench/run_orphan_bench_datahub.py:186-194` 略過第二次 schema ingestion；提交報告記錄 0/2（`bench/HOLDOUT-orphan-iterable-datahub.md:40-54`）。
- **Shot 10 成立且目前仍未合併。** 本輪四次 `gh pr view … --json number,title,state,url,mergedAt,closedAt` 均回 OPEN、`mergedAt:null`；`gh pr diff 18628 -R datahub-project/datahub --patch` 也直接顯示 GraphQL 取得 `editableSchemaMetadata`、清理程式宣稱已 merge 後刪除、但原先沒有 merge 實作的修補內容。原五項清單對「不要說 merged」足夠。
- **Shot 11 的 Apache-2.0 只能由 README 自述，尚無授權檔。** 這不只是 footage sourcing；若片尾把 Apache-2.0 當成 repo 的實際 license，評審可由 GitHub `licenseInfo:null` 與缺少 `LICENSE` 反駁。

## 四、超時刪減順序

**先切 Shot 3 不矛盾，順序是對的。** 前次評決要求加入 Shot 3，是因為它用八秒支付 Originality、避免前 21 秒只像 `datahub-enrich`；同一段也明說這八秒是已存在素材的 baseline 差異，不是 end-to-end 證明（`docs/REVIEW-video-codex.md:85-91`）。當影片超時時，保住 Shot 1–2 的問題／結果與 Shot 4–7 的偵測／拒寫／寫回證據，比保住 baseline 解釋重要。Shot 3 又是全片第二快的 225 wpm，所以先整段切除比硬塞 30 字合理。

真正的矛盾在刪減清單第三順位：前次評決明說兩張 before／after 圖不構成 StillTrue 因果鏈，DataHub timeline「必須保留」（`docs/REVIEW-video-codex.md:71-75`）；目前卻把 Shot 6 列成第三個可切項目（`docs/VIDEO-SCRIPT.md:65-68`）。若真的需要再省那 12 秒，切 Shot 6 會撤掉前次裁決要求保留的獨立寫回證物。這不改變「Shot 3 先切是正確的」答案，但表示現有 cut order 只能安全執行前兩步，第三步會破壞既定證據鏈。

## 最終判定

- **素材就緒度：未通過。** Shot 7 要標成現場錄製，Shot 9 要先提供本機副本，Shot 11 要有可引用的片尾卡來源與實際授權檔。
- **Timing：未通過。** Shot 1 至少刪 24 字，Shot 3 至少刪 10 字；若不改字，Shot 3 應依既定 cut order 整段移除。
- **Narration truthfulness：未通過。** 最低限度必須處理 Shot 2 的 human confirmation、Shot 3 的 perfect coverage、Shot 8 的 written once，以及 Shot 11 的 everything／license；Shot 1、4、7 的全稱措辭也應限縮到 repo 真正證明的範圍。
- **先切 Shot 3：通過。** 這是條件式優先順序，不是否定加入 baseline 的原判斷；但不要執行第三順位的 Shot 6 刪除。
