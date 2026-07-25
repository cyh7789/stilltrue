# 診斷:holdout 跑分反直覺結果的成因

診斷日期:2026-07-25。
範圍:只診斷,未改任何既有程式碼。實驗腳本在 `/tmp/cds-diag/`(repo 外)。

## 結論先講

第 3 版的怪結果不是偵測器邏輯壞掉,是三個獨立機制疊在一起:

1. **跑分餵料 bug(主因)**:`bench/run_shopify_bench.py:60` 只在
   `c == r["column"]` 時掛描述;40 筆裡有 18 筆該欄位不在 c2 重建的 schema 裡,
   漂移描述被整個丟掉,偵測器根本沒看到文字。IDENTIFIER_CHANGE 的 9 筆無反應全在這裡。
2. **schema 重建對 mart 模型失真**:`sql_columns_at`(`bench/oracles/mine_holdout.py:64`)
   的 regex 只認 staging 風格 SQL;mart 模型用 `select *` + `dbt_utils.star()`,
   欄位根本不在 SQL 原文裡,抽出來的「schema」是殘缺的。
3. **DEPRECATION 的標籤語意跟偵測器抓的東西不是同一件事**:30 筆裡 17 筆的 c1 描述
   完全抽不出任何識別碼,偵測器沒東西可比。這部分 holdout 不適合測 `detect_schema_break`,
   換什麼跑分方法都救不回來。

修好 1 之後(實驗驗證,見下),IDENTIFIER_CHANGE 可達 9/10 DRIFT。
DEPRECATION 建議從這個偵測器的跑分裡拿掉。

## 【Origin】診斷格式

【Symptom】第 3 版把描述掛到欄位自己的 description 後,IDENTIFIER_CHANGE 從
「9 筆棄權」變成「9 筆完全無反應」;DEPRECATION 反而抓到 4 筆 DRIFT。

【Origin】三個機制,各自有 file:line 與實驗證據,下面分節。

【Verdict】機制 1、2 是跑分方法的 bug(會重複發生在任何 mart 模型上);
機制 3 是 holdout 標籤與偵測器目標的本質不匹配,不是 bug。

【Treatment】本次不修,只給診斷。修法建議在文末。

## 機制 1:描述掛載條件把 18/40 筆的漂移文字整個丟掉

`bench/run_shopify_bench.py:60`:

```python
"description": r["description_at_c1"] if c == r["column"] else "",
```

`c` 走遍 `sql_columns_at(repo, r["c2"], r["model"])` 的結果;
當 `r["column"]`(yml 裡的欄位名)不在這個集合裡,整個迴圈沒有任何一格拿到描述,
偵測器收到的是 40 個空描述欄位加空表描述——當然「無反應」。

實驗計數(`/tmp/cds-diag/diag_holdout.py`,對 40 筆 Tier A 分桶):

| 類別 | 桶 | 筆數 | 跑分結果 |
|---|---|---|---|
| IDENTIFIER_CHANGE | 欄位不在 c2 schema,描述被丟 | 9 | 全部無反應 |
| IDENTIFIER_CHANGE | 描述有掛上、識別碼確實缺席 | 1 | DRIFT |
| DEPRECATION | 欄位不在 c2 schema,描述被丟 | 9 | 全部無反應 |
| DEPRECATION | c1 描述抽不出任何識別碼 | 17 | 全部無反應 |
| DEPRECATION | 描述有掛上、識別碼缺席 | 4 | DRIFT |

這直接解釋「第 2 版有 9 筆被指出位置、第 3 版反而消失」:
第 2 版把描述放在 `entity_description`,一定會被讀到,unresolved 識別碼走
`src/sentinel/detectors.py:163` 的表描述分支 → INSUFFICIENT_EVIDENCE(棄權 9 筆)。
第 3 版描述改掛欄位,但掛載條件讓同樣那 9 筆的文字根本沒進偵測器 → 無反應。
變差的不是「掛對位置」這個決定,是掛載的實作。

反事實實驗(`/tmp/cds-diag/diag4.py`):把被丟掉的 18 筆描述強制掛回
(把 `r["column"]` 補進 fields),結果:

- IDENTIFIER_CHANGE 9 筆 → **8 筆 DRIFT**、1 筆無反應
- DEPRECATION 9 筆 → 2 筆 DRIFT、7 筆無反應

偵測器對 IDENTIFIER_CHANGE 的邏輯是好的:文字餵得進去就抓得到
(走 `src/sentinel/detectors.py:144` 的欄位描述 medium 分支)。

## 機制 2:為什麼 18 筆的欄位「不在」c2 schema——schema 重建對 mart 模型失真

`sql_columns_at`(`bench/oracles/mine_holdout.py:72-73`)只抓兩種樣態:
`as alias` 與「4 格縮排、行尾逗號」的裸欄位。這是 staging 模型的慣例。

實測 `shopify__customers.sql` @ c2(`/tmp/cds-diag/diag3.py`):

- `select *` → 有;`dbt_utils.star(` → 有
- SQL 全文 930 字元,`marketing_consent_state` 不在文字裡
- 抽出的「schema」只有 5 個欄位

mart 模型的欄位來自上游展開,SQL 原文看不到。所以餵給偵測器的 c2 schema
對 mart 模型是虛構的:被丟的 18 筆裡,`shopify__customers`、`shopify__products`、
`shopify__order_lines`、`shopify__inventory_levels`、`shopify__discounts` 全是 mart。
另有幾筆(如 `shopify__discounts.value`)欄位名其實出現在 SQL 文字裡但 regex 沒抽到。

連帶後果:就算修好機制 1 的掛載,mart 模型的「實際 schema」仍是殘缺的,
描述裡引用的兄弟欄位會大量假性 unresolved,DRIFT 數字會虛高。
上面「9/10」的反事實數字因此偏樂觀,只能當上界。

## 機制 3:DEPRECATION 標籤跟 detect_schema_break 抓的不是同一件事

DEPRECATION 的定義(`bench/oracles/mine_holdout.py:98`)是
「c2 描述新增了 deprecat 字樣」——漂移的內容是**資訊缺席**
(現實已棄用、文件還沒說),不是**過時的欄位引用**。

`detect_schema_break` 只會檢查「描述引用的識別碼是否還在 schema」。
17/30 筆 DEPRECATION 的 c1 描述抽不出任何識別碼(例:
`stg_shopify_gql__order_note_attribute.name` 的 c1 描述是 "Name of the attribute.")
——偵測器沒有任何東西可以比對,無反應是正確行為,不是 miss。

至於抓到的 4 筆 DRIFT,機制是錯位的巧合:例如
`shopify__order_lines.variant_weight` 的描述提到 `weight_unit`,
這個識別碼在(殘缺的)c2 欄位集裡 unresolved,於是欄位描述分支開火。
開火原因與標籤記錄的 deprecation 無關;而且真正的 mart 欄位是
`variant_weight_unit`,`weight_unit` 的 unresolved 有一部分本身就是機制 2 的假象。
這 4 筆不能算「偵測器會抓 DEPRECATION」的證據。

## 回答 DIAGNOSE.md 的第 4 題

- **跑分方法有 bug**:有,兩個——描述掛載條件(機制 1,主因)與
  mart 模型的欄位抽取(機制 2,機制 1 的上游成因)。
- **偵測器邏輯有問題嗎**:本次證據裡沒有。文字餵得進去時,
  IDENTIFIER_CHANGE 的行為符合設計(9/10 可抓);三態分支走向也都符合註解宣告的規則。
- **holdout 標籤語意不匹配嗎**:DEPRECATION 這一類是——它測的是資訊缺席,
  `detect_schema_break` 測的是過時引用,本來就不同一件事。
  IDENTIFIER_CHANGE 這一類匹配,holdout 可用。

## 修法方向(供後續,本次未動)

1. 掛載修正:`r["column"]` 不在重建欄位集時,仍應把它連同描述補進 fields
   (它在 yml 裡有文件,DataHub 上就是會有這個欄位條目)。
2. schema 重建:mart 模型別用 regex 刮 SQL——要嘛限定跑分範圍到 staging 模型
   (`sql_columns_at` 對其有效的子集),要嘛改走 dbt manifest/compile 取欄位。
3. DEPRECATION 從 `detect_schema_break` 的跑分拿掉,歸給 D5 語意偵測器的跑分,
   或另立 oracle 類別。
