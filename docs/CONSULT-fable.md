# OPINION — 三個決定的第二意見

> 依據：僅本目錄檔案，未上網。每個判斷附原文出處；查不到的標「情報缺口」。
> 審視日 2026-07-26，距截止 15 天。

## 一句話結論

1. **決定 1（41% 不修、原樣發表）：推翻一半。** 41% 原封不動發表是對的、且不可逆；但「因此 15 天內完全不修這兩類失敗」是把凍結紀律用錯了地方——正解是修碼 → 重新凍結 → 依同一機械規則取第三來源單跑一次，兩個 holdout 數字都登。另外「README 首屏 41% 裸打頭」是呈現錯誤，該打頭的是方法，不是數字。
2. **決定 2（D2 結案）：有條件同意。** 工程面的結案成立、證據充分；但有一條零成本的路你沒走——`nyc-taxi` 不在 registry 是主辦方 Resources 頁與 CLI 之間的矛盾，去 `#agent-hackathon` 問一句。揭露式自植維持排除，理由在下面。
3. **決定 3（「它不存在本身就是答案」）：有條件同意。** 論證本身站得住、不像藉口——前提是它不能是 Originality 的唯一證物。要跟 PR #49、holdout 方法、四類 agent 對位這三樣接在一起，缺了就會被讀成藉口。

時間配置：三題合計要挪約 3.5–4 天給決定 1 的修碼與重跑，**不需要從提交面的 4 天裡挪**——15 天只排了 4 天，且決定 2 結案正好釋出審查原建議給 D2 的 1.5–2 天。細算在最後一節。

---

## 決定 1：凍結 holdout 41%，不修、原樣發表

### 1.1 你做對且不可逆的部分

41% 這個數字本身不能動，這點沒有討論空間。`freeze.json` 的規則寫死了：

> "runs_allowed": 1
> "on_result": "published as measured; the frozen files are not modified in response"

事後修到好看再宣稱 holdout，就是 `VALIDATION-INTEGRITY.md` 剛花整份文件撤回的那種宣告。這半個決定同意。

### 1.2 「不修」推翻：三條理由

**第一，凍結規則自己就沒有禁止修碼。** `on_result` 的原文是 "the frozen files are not modified **in response**"——約束的是「不因這次結果回頭改這批受評檔案再重評」，不是「此後永遠不准改進產品」。`HOLDOUT-REPORT.md` 裡「A holdout that gets fixed until it agrees with the development set is a development set」講的是**對同一來源反覆重評**，不是修 bug 本身。你把「不能重評同一份考卷」擴大解釋成「不能讀書」了。

**第二，兩類失敗裡有一類根本不是 holdout 教你的，是開發集早就攤在桌上的。** 描述列舉值那一類，`SHOPIFY-REPORT.md` 在凍結前就寫得清清楚楚：

> The misses are one shape. Descriptions enumerate *values*, and enumerated values look exactly like column names

87 筆誤報、4.50%，成因單一，凍結時已知未修。修它的正當性來自開發資料，跟 holdout 純潔性毫無關係——不修它不是紀律，是把已知 bug 留在船上。外鍵散文指向鄰表那一類確實是 holdout 新教的，但 holdout 的功能本來就包含「教你東西」；它唯一不許的是被同一來源重複打分。

**第三，誤報才是這個工具實用性的真正殺手，而兩類失敗修的主要就是誤報。** 大家盯著 recall 41%，但換算警報精確率：dbt_shopify 上 9 真 + 87 假 = 一次掃描的 findings 裡只有約 9% 是真的；fivetran_log 上 13 真 + 7 假 = 65%（兩者負例母體規模不同，不能直接互比，但量級訊息一致）。一個「real data platform team」（BRIEF 評分標準 4 原文）收到十個警報九個假，第二週就關掉它。`HOLDOUT-REPORT.md` 自己說「a cross-model reference check would take out most of the false positives」——這是對 Real-World Usefulness 有直接分數的修復，不是為了美化 holdout。

### 1.3 第三條路（你問的那條）：修 → 重凍結 → 第三來源 → 單跑

流程完全複用你已經建好的機械：

1. 修兩類失敗（你自估各半天到一天，取 1.5–2 天），dbt_shopify 與 dbt_fivetran_log 從此都是開發 benchmark，回歸跑分照登。
2. 重新凍結：新 `freeze.json`，選源規則的 exclude 清單加入 `dbt_fivetran_log`（它已被看過），其餘門檻不變，接續字母序往下走。
3. 第三來源單跑一次，`runs_allowed: 1`、`on_result` 照舊，**無論多難看照登**。
4. README 兩個 holdout 數字都放：v1 凍結 41% → 修復 → v2 凍結 X%。

順序有一條硬約束，REVIEW-r2-duo.md §3 已經講過：「**凍結必須在所有程式碼改動之後、holdout 單跑之前**」。所以 README 與影片定稿必須排在 v2 跑完之後。

「新來源可能又跑出難看數字」——對，而且沒關係。兩個誠實的轉移數據點比一個好；如果 v2 還是 4 字頭，你得到的是「這個問題在野外就是這麼難」的量測，照登。真正的差別在敘事等級：REVIEW-r2-duo.md §2.1 說過「『我們區分擬合與轉移，兩種都給你』比『我們只有擬合，但很誠實』高一個級距」——而「我們量轉移、修、再量一次」又比單點高一級：它證明的是一個會收斂的工程迴圈，不是一次好運或一次認栽。

補充一條可選的透明化：修完的程式碼在 fivetran_log（此時已降為開發 benchmark）上重跑的數字可以登，但必須明標「post-hoc、非 holdout、回歸用途」。有 v2 之後這條不是必需，只是佐證修復有效。

### 1.4 「評審看到首屏 41% 的第一反應」——直接回答

分兩種讀者，這個劃分兩份審查都用過。會細讀的（Tim Bossenmaier、Mike Burke、或 BRIEF §6 保留條款的 automated AI-driven analysis）：讀出「這人誠實而且懂驗證」，加分。只掃首屏和影片的多數評審：**「這東西不準」**。裁決依據是 BRIEF §4 原文：

> Judges are not required to test the Project and may choose to judge based solely on the text description, images, and video provided in the Submission.

1,855 個參賽者、五條等權評分，掃讀是預設模式。一個沒有上下文的裸 41% 付出的 Real-World Usefulness 印象分，大於它從掃讀者身上賺到的誠實分——誠實要讀兩句話才看得出來，「不到一半」一眼就看得出來。

但解法不是回去讓 90% 打頭（那是引用擬合數字，`VALIDATION-INTEGRITY.md`：「A benchmark that shaped the rules measures fit, not transfer」），而是**讓方法打頭、數字成對出現**。你現在的 `README-submission.md` Evidence 段其實已經是正確形狀：

> The number that matters is the one measured on a source this code had never seen, after its rules were frozen […] The 90% was fitted; the 41% is the one to carry forward.

首屏維持問題敘事（documentation is lying），Evidence 段以「凍結 holdout」領頭、41% 與 90% 並排、一句話點明差距本身就是發現。「首屏改成 41% 裸打頭」是把該段落的一格數字抽出來當招牌，比現狀差——這一小步收回來。真正的招牌句是：**這可能是全場唯一能講出自己轉移數字的提交**。REVIEW-r2-codex.md 對 2/2 的建議在此同構適用：「不把 2/2 當前三個主打成效數字……定位成公開、可重生的回歸基準」。

---

## 決定 2：D2 宣告做不出來，結案

### 2.1 結案本身同意，證據夠硬

四條實測裡最硬的一條其實是宣稱側：`D2-FEASIBILITY.md`——76 張表、20 筆有描述、**0 筆宣稱更新週期**，唯一 regex 命中還是反例（「refreshed on query」＝沒有排程）。D2 的規則需要兩側（「a description claims a refresh cadence; the observed gap … exceeds 3× that cadence」），宣稱側是空的，現實側有沒有時間戳都救不回來。現實側三條路（get_entities 無時間戳、FRESHNESS assertion 全庫 0 筆、`datasetProperties.lastModified` 是 datapack 建置時間）把退路也封了。「太早放棄」不成立——這不是放棄，是量測出負結果，而且你把負結果寫成了文件，這份文件本身在 README 裡是資產（「blocked not by effort but by the catalog … that boundary is a real property of the problem」）。

我另外查過有沒有你沒試的技術路：dbt 的 source freshness 宣告（YAML 的 `freshness:` 區塊）能補宣稱側，但現實側需要 data-plane 的實際載入時間戳，git repo 裡沒有；死路。DataHub 的 operations aspect 你的文件只提到 Kit 回應裡沒有——REST 側是否查過是**情報缺口**，但不影響結論，因為宣稱側 0/20 獨立致死。

### 2.2 沒試的一條路：問主辦，零工程成本

`nyc-taxi` 的狀態是主辦方自己的矛盾：BRIEF §8.5 的 Resources 頁明載「`nyc-taxi` … 3-stage pipeline with **planted freshness issues**」和載入指令，而 `D2-FEASIBILITY.md` 實測 registry.json 只有兩個 pack、CLI 回 `Unknown data pack`。這看起來是未發布或漏上架，不是不存在。BRIEF §8.7：`#agent-hackathon` 頻道提供即時協助、賽程中段有 office hours。**發一則訊息問「Resources 頁列的 nyc-taxi datapack 載入回 Unknown data pack」**——成本一則訊息，可能的回報是官方 ground truth 憑空出現；順帶還是一次社群可見度，而且回報這個落差本身接近 Feedback 獎那類貢獻的性質。條件式重啟：官方 pack 若在剩 ≥5 天時上架，D2 是確定性規則加現成 oracle 機制，REVIEW-r2-duo.md 估過 1.5–2 天，做得完；沒回音或太晚，維持結案，一分力氣都不投。

### 2.3 揭露式自植：維持排除，理由說清楚

你問「有明確揭露的前提下可不可以接受」。分兩件事：

- **出數字**：不可以。揭露改變的是讀者知情與否，不改變「答案是你寫的」這個結構。一個自己出題自己改考卷的 benchmark，加上誠實標籤後仍然量不出任何東西，而這個專案的整個身分（`VALIDATION-INTEGRITY.md` 全文）就建立在剛把這種數字清出去。
- **當機制展示**：技術上可以（明標 synthetic demo、不附任何準確率宣稱，不違反 Technical Execution 的「Does the code do what the submission claims?」），但邊際價值低於機會成本——你現在「兩類偵測器被目錄擋住、量測俱在」的敘事比一個灌合成輸入的 demo 更有記憶點，後者反而稀釋它。除非官方 pack 復活（2.2 那條路），否則不做。

---

## 決定 3：Originality 用「它不存在本身就是答案」回答

### 3.1 論證本身：站得住，不是藉口——因為它可查證

藉口的形狀是「我們做不出來，請相信我」；`NATIVE-COMPARISON.md` 的形狀是「這東西在這個平台上無處安放，enum 在這裡自己看」。三條證據全是平台自己的話：skill frontmatter 自述、`datahub-search` 的「how **complete** is our metadata」、assertion 七型別「There is no assertion type whose subject is the documentation」。可查證的負存在宣告不是藉口，是舉證。而且結論句寫對了：「The absent baseline *is* the finding」——硬做 b2 只會跟 B1 重複或量到自己發明的東西，這個推理成立，B1 也已經在對照表裡替 native 能力站崗。

對 Maggie Hays 這一席，Cloud Context Hub 那段的姿態尤其對：「StillTrue does not replace it and cannot be compared against it — it is the open-source side of the same problem」，外加「If DataHub Cloud's Context Hub evaluations do exactly this, that is evidence the problem is worth solving」。對一個 Founding PM，這是在驗證她的路線圖而不是跟它打架。再加一層：DataHub 自己的內容行銷（BRIEF §9.4）就有一篇標題叫「**Continuous Context: Why Your AI Documentation Is Already Lying to You**」，你的 README 首句就是它的實作化——評審席的雇主已經替你寫好了 Indication。

### 3.2 條件：它不能獨自扛 Originality，要接三樣東西

REVIEW-r2-duo.md §4 判 Originality 最危險的理由是「唯一一條**目前拿不出任何肯定證據**的」。`NATIVE-COMPARISON.md` 補的是防禦面（「我沒有重造現成功能」）；肯定面的證據其實你已經有了，只是沒接上：

1. **PR #49（`datahub-skills` 的 `datahub-context-drift` skill，STATUS §5，open）。** 這是整個論證的殺手級收尾：不只說「DataHub 缺這個」，而是**已經把缺的那塊提交回 DataHub 自己的 skills repo**。負存在宣告變成建設性行動，還直接踩在 Bonus 條款（BRIEF §6：「new connectors, skills, fixes …」）與 §8.2「Browse the datahub-skills repo … and contribute new ones」上。`NATIVE-COMPARISON.md` 結尾與 README 的 Originality 段必須同段連結它，一句話：「the gap is real, and here is our PR filling it」。
2. **凍結 holdout 方法本身。** REVIEW-r2-duo.md §4：「『有轉移證據的漂移偵測』本身就是與現成功能的區隔」。現在它存在了（決定 1 之後會有兩個），把它算進 Originality 的證物清單，不要只放在 Evidence 段。
3. **四類 agent 對位一句話，預answer Nick Adams。** 他是四類 agent 清單的作者（BRIEF §7），職務上必問「這跟我列的哪一類差在哪」。BRIEF §8.1 原文裡：Data Quality Agent 的主體是資料（「自動掃描**資料**問題……新增 data quality assertions」）；Data Steward Agent 是**產出**metadata（「套用 glossary terms 與描述」）。StillTrue 是 Steward Agent 的逆運算：不寫文件，檢驗人寫的文件是否仍為真。`NATIVE-COMPARISON.md` 的 enrich 那一列（「writes what a human decided; does not evaluate it」）已經隱含這件事，補一行明寫四類對位，把這一問在他開口前收掉。

一個小風險記錄在案：論證引用了「`/datahub-audit` … is not itself in the repository」。負存在宣告有時效——評審期到 8/31，如果那個 skill 期間出貨且超出 completeness 範圍，這句會過期。文件現有的 hedge（「described but not yet shipped」）已經夠，但影片與 README 裡不要把「DataHub 沒有」講成永恆式，講成「as of submission, 附查核日」。

**判定：接上這三樣，這個論證會讓評審點頭；只靠它自己，會被當成寫得很好的藉口。**

---

## 時間配置（回答「挪多少天、從哪挪」）

| 事項 | 工時 | 來源 |
|---|---|---|
| 修兩類失敗（含回歸測試） | 1.5–2 天 | 你的自估（各半天到一天）；程式碼本體不可及，採信此估——**情報缺口** |
| 重新凍結 + 第三來源選取 + 單跑 + 報告 | 1.5 天 | 你對重跑一輪的自估 |
| 提交面（影片、L3、public、Devpost） | 4 天 | 原排程不動 |
| 決定 3 的接線（README／NATIVE-COMPARISON 補 PR #49、四類對位、holdout 入列） | 0.5 天 | 併入提交面 README 定稿日 |
| Slack 問 nyc-taxi | 一則訊息 | 今天就發，等回音不佔工時 |

合計約 7.5–8 天，剩 15 天，緩衝約 7 天。**不從提交面挪**：原計畫只配置了 4 天，未配置時間吸收全部新增項；且兩份審查原本各建議 1.5–2 天給 D2 或 D5，決定 2 的結案（D2-FEASIBILITY 的新事實推翻了那兩個建議的前提——nyc-taxi 不存在、`get_dataset_queries` total 0）正好釋出這段。

順序硬排（不可換）：**修碼 → 重新凍結 → v2 單跑 → README／影片定稿 → public → Devpost**。README 和影片裡的數字必須是 v2 落地後的最終版，先錄影片就是白錄。若 Slack 那邊 nyc-taxi 復活且剩 ≥5 天，D2 插在「修碼」段末、凍結之前（凍結後就永遠進不了正式數字，REVIEW-r2-duo.md §3 第 3 件講過這條）。

風險預告一條：字母序接續走下去，fivetran 的 `dbt_*` 母體裡是否還有能過六道門檻的候選，本目錄查不到——**情報缺口**。若母體耗盡，母體擴充規則（例如加入 dbt-labs 或其他公開 dbt 套件維護者）必須**在看任何候選之前**先 commit，跟你第一次做的一樣。

## 情報缺口彙總

1. `dbt_fivetran_log` 之後的字母序候選是否還有能過門檻者（影響 v2 選源，不影響判斷方向）。
2. DataHub operations aspect 是否經 REST API 查核過（不影響 D2 結論——宣稱側 0/20 獨立致死）。
3. 修兩類失敗的實際工時——程式碼 repo 不在本目錄，採用你的自估。
4. PR #49 的 diff 內容與 review 狀態（決定 3 的接線價值以「open 且存在」為底線成立；meaningful 與否兩輪審查都列為缺口，提交物應附 diff 摘要）。
