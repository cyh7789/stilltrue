"""Behavior tests for the D1 detector.

Each test maps to a real pitfall hit during development, none added just for coverage.
They test behavior: break the detection logic and these go red; renaming things won't.
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
    """Real NYC TLC 2023-02 incident: airport_fee became Airport_fee, the description didn't follow.

    This case used to be completely missed -- the detector lower()ed both sides,
    so its own normalization erased the case difference.
    """
    fields = [{"fieldPath": "Airport_fee", "description": "Airport fee", "nativeDataType": "double"}]
    found = _drift(detect_schema_break(TLC_URN, "Fare breakdown includes airport_fee for LGA/JFK pickups.", fields, ["ev1"]))

    assert len(found) == 1
    assert found[0].subject == "airport_fee"
    assert found[0].suspected_rename == "Airport_fee"
    assert found[0].confidence == "high"


def test_tlc_new_undocumented_column_is_detected():
    """Real NYC TLC 2025-01 incident: cbd_congestion_fee added with no description at all."""
    fields = [
        {"fieldPath": "cbd_congestion_fee", "description": "", "nativeDataType": "double"},
        {"fieldPath": "trip_distance", "description": "Elapsed trip distance", "nativeDataType": "double"},
    ]
    found = _drift(detect_schema_break(TLC_URN, "Yellow taxi trip records.", fields, ["ev2"]))

    assert [f.subject for f in found] == ["cbd_congestion_fee"]
    assert found[0].category == "D1_UNDOCUMENTED"


def test_consistent_description_produces_nothing():
    """A description consistent with reality must produce no output -- one false positive ruins the credibility of the whole report."""
    fields = [{"fieldPath": "trip_distance", "description": "Elapsed trip distance in miles", "nativeDataType": "double"}]
    assert detect_schema_break(TLC_URN, "Records include trip_distance per ride.", fields, ["ev3"]) == []


def test_self_table_name_is_not_a_field_reference():
    """Mentioning your own table/database name in a description is normal writing.

    Observed false positives: order_details and order_entry_db were both reported as nonexistent fields.
    """
    fields = [{"fieldPath": "order_id", "description": "Order id", "nativeDataType": "NUMBER"}]
    desc = "Detailed order lines from order_entry_db.analytics.order_details."
    assert _drift(detect_schema_break(DBT_URN, desc, fields, ["ev4"])) == []


def test_identifier_qualified_as_schema_is_ignored():
    """When a description says "`order_entry` schema", the author already made clear it's not a field.

    Observed false positive: the order_details description in showcase-ecommerce is written exactly like this.
    """
    fields = [{"fieldPath": "order_id", "description": "Order id", "nativeDataType": "NUMBER"}]
    desc = "Combines data from multiple tables in the `order_entry` schema."
    assert _drift(detect_schema_break(DBT_URN, desc, fields, ["ev5"])) == []


def test_unknown_bare_identifier_abstains_instead_of_reporting():
    """A bare identifier with no close field match → abstain, not drift.

    Abstaining is a legitimate output (SPEC three-state design); reporting something uncertain as DRIFT is the real problem.
    """
    fields = [{"fieldPath": "order_id", "description": "Order id", "nativeDataType": "NUMBER"}]
    findings = detect_schema_break(DBT_URN, "Joined with some_other_thing during ETL.", fields, ["ev6"])

    assert _drift(findings) == []
    assert [f.verdict for f in findings] == ["INSUFFICIENT_EVIDENCE"]
