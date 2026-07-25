"""D1 偵測器的行為測試。

每一條都對應開發時真實踩過的坑，不是為了覆蓋率補的。
測的是行為：把偵測邏輯弄壞，這些會紅；只改名字不會。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.detectors import detect_schema_break  # noqa: E402

TLC_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,tlc.yellow_tripdata,PROD)"
DBT_URN = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)"


def _drift(findings):
    return [f for f in findings if f.verdict == "DRIFT"]


def test_tlc_case_rename_is_detected():
    """NYC TLC 2023-02 真實事件：airport_fee 被改成 Airport_fee，描述沒跟上。

    這個案例曾經完全抓不到 —— 因為偵測器把兩側都 lower() 之後，
    大小寫差異被自己的正規化抹平了。
    """
    fields = [{"fieldPath": "Airport_fee", "description": "Airport fee", "nativeDataType": "double"}]
    found = _drift(detect_schema_break(TLC_URN, "Fare breakdown includes airport_fee for LGA/JFK pickups.", fields, ["ev1"]))

    assert len(found) == 1
    assert found[0].subject == "airport_fee"
    assert found[0].suspected_rename == "Airport_fee"
    assert found[0].confidence == "high"


def test_tlc_new_undocumented_column_is_detected():
    """NYC TLC 2025-01 真實事件：新增 cbd_congestion_fee，沒有任何描述。"""
    fields = [
        {"fieldPath": "cbd_congestion_fee", "description": "", "nativeDataType": "double"},
        {"fieldPath": "trip_distance", "description": "Elapsed trip distance", "nativeDataType": "double"},
    ]
    found = _drift(detect_schema_break(TLC_URN, "Yellow taxi trip records.", fields, ["ev2"]))

    assert [f.subject for f in found] == ["cbd_congestion_fee"]
    assert found[0].category == "D1_UNDOCUMENTED"


def test_consistent_description_produces_nothing():
    """描述與現實一致時不得有任何輸出 —— 誤報一次就毀掉整份報告的可信度。"""
    fields = [{"fieldPath": "trip_distance", "description": "Elapsed trip distance in miles", "nativeDataType": "double"}]
    assert detect_schema_break(TLC_URN, "Records include trip_distance per ride.", fields, ["ev3"]) == []


def test_self_table_name_is_not_a_field_reference():
    """描述提到自己的表名/資料庫名是正常寫法。

    實測誤報：order_details、order_entry_db 都曾被當成不存在的欄位報出來。
    """
    fields = [{"fieldPath": "order_id", "description": "Order id", "nativeDataType": "NUMBER"}]
    desc = "Detailed order lines from order_entry_db.analytics.order_details."
    assert _drift(detect_schema_break(DBT_URN, desc, fields, ["ev4"])) == []


def test_identifier_qualified_as_schema_is_ignored():
    """描述寫「`order_entry` schema」時，作者已講明那不是欄位。

    實測誤報：showcase-ecommerce 的 order_details 描述就是這樣寫的。
    """
    fields = [{"fieldPath": "order_id", "description": "Order id", "nativeDataType": "NUMBER"}]
    desc = "Combines data from multiple tables in the `order_entry` schema."
    assert _drift(detect_schema_break(DBT_URN, desc, fields, ["ev5"])) == []


def test_unknown_bare_identifier_abstains_instead_of_reporting():
    """裸寫、又找不到相近欄位的識別碼 → 棄權，不是漂移。

    棄權是合法輸出（SPEC 三態設計）；把不確定的東西報成 DRIFT 才是問題。
    """
    fields = [{"fieldPath": "order_id", "description": "Order id", "nativeDataType": "NUMBER"}]
    findings = detect_schema_break(DBT_URN, "Joined with some_other_thing during ETL.", fields, ["ev6"])

    assert _drift(findings) == []
    assert [f.verdict for f in findings] == ["INSUFFICIENT_EVIDENCE"]
