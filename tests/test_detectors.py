"""Behavior tests for the D1 detector.

Each test maps to a real pitfall hit during development, none added just for coverage.
They test behavior: break the detection logic and these go red; renaming things won't.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stilltrue.detectors import detect_schema_break  # noqa: E402

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


def test_consistent_description_raises_no_problem():
    """A description consistent with reality must raise nothing -- one false positive ruins the credibility of the whole report.

    It is not silent: the resolved reference is recorded as CURRENT, which is
    what lets the report say how much it checked. What it must never do is
    report a problem.
    """
    fields = [{"fieldPath": "trip_distance", "description": "Elapsed trip distance in miles", "nativeDataType": "double"}]
    found = detect_schema_break(TLC_URN, "Records include trip_distance per ride.", fields, ["ev3"])

    assert [f.verdict for f in found] == ["CURRENT"]
    assert not [f for f in found if f.verdict in ("DRIFT", "INSUFFICIENT_EVIDENCE")]


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


# --- CURRENT: the third verdict ---------------------------------------------
# A detector that only ever speaks up about problems cannot say how much it
# checked. "11 of 12 references still resolve" is what makes the twelfth
# believable; silence on the eleven is indistinguishable from not looking.


def test_a_reference_that_still_resolves_is_recorded_as_current():
    fields = [
        {"fieldPath": "fare_amount", "description": "", "nativeDataType": "double"},
        {"fieldPath": "tip_amount", "description": "", "nativeDataType": "double"},
    ]
    found = detect_schema_break(
        TLC_URN, "Total is `fare_amount` plus `tip_amount`.", fields, ["ev1"]
    )
    current = [f for f in found if f.verdict == "CURRENT"]

    assert {f.subject for f in current} == {"fare_amount", "tip_amount"}
    assert not [f for f in found if f.verdict == "DRIFT" and f.category == "D1_SCHEMA_BREAK"]


def test_a_verified_reference_never_becomes_a_write_proposal():
    """CURRENT is a record, not a change: the Policy Gate must refuse it as a proposal."""
    from stilltrue.evidence import Evidence, EvidenceStore
    from stilltrue.proposal import PolicyGate, Proposal

    fields = [{"fieldPath": "fare_amount", "description": "", "nativeDataType": "double"}]
    current = [f for f in detect_schema_break(TLC_URN, "See `fare_amount`.", fields, ["ev1"])
               if f.verdict == "CURRENT"][0]

    store = EvidenceStore()
    ev = store.add(Evidence(entity_urn=TLC_URN, source_function="list_schema_fields", payload={"fields": fields}))
    result = PolicyGate(store).check(Proposal(
        entity_urn=TLC_URN, aspect="dataset_description", verdict=current.verdict,
        subject=current.subject, before_value="See `fare_amount`.", after_value="See `fare_amount` (checked).",
        rationale=current.reality, evidence_ids=[ev],
    ))

    assert not result.passed


def test_case_variant_is_drift_not_current():
    """The TLC event must not be swallowed by the new CURRENT path."""
    fields = [{"fieldPath": "Airport_fee", "description": "", "nativeDataType": "double"}]
    found = detect_schema_break(TLC_URN, "Includes `airport_fee`.", fields, ["ev1"])

    assert [f.verdict for f in found if f.subject == "airport_fee"] == ["DRIFT"]


def test_finding_order_is_stable_across_processes():
    """Ids are assigned by position, so unstable ordering makes every documented id wrong.

    identifier_mentions draws on regex finds. Set iteration order for strings depends
    on PYTHONHASHSEED, which is randomised per process -- so this only shows up
    across runs, never within one. It is how the finding id in
    examples/tlc-rename stopped matching what `make demo` printed.
    """
    import subprocess
    import sys

    script = (
        "import json,sys;"
        "sys.path.insert(0, 'src');"
        "from stilltrue.detectors import detect_schema_break as d;"
        "f=[{'fieldPath':n,'description':'','nativeDataType':'double'} "
        "for n in ['fare_amount','tip_amount','mta_tax','Airport_fee','tolls_amount']];"
        "t='Total is `fare_amount` plus `tip_amount`, `mta_tax`, `tolls_amount` and airport_fee.';"
        "print(json.dumps([x.subject for x in d('urn:li:dataset:(urn:li:dataPlatform:s3,t,PROD)',t,f,['ev'])]))"
    )

    orders = set()
    for seed in ("0", "1", "42", "12345", "99999"):
        out = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        orders.add(out.stdout.strip())

    assert len(orders) == 1, f"ordering varied by hash seed: {orders}"


# --- Evidence-gated assertion ----------------------------------------------
# An assertion needs proof the token was a field of this table. Two things
# qualify, and both come from DataHub rather than from reading the prose:
#   a near-match in the current schema  -> it was renamed
#   a removal in DataHub's change log   -> it was deleted
# Everything else abstains. Strings below are verbatim from the three corpora.

from stilltrue.detectors import VanishedField, vanished_fields  # noqa: E402


def _fields(*names):
    return [{"fieldPath": n, "description": "", "nativeDataType": "unknown"} for n in names]


def _verdicts(desc, *schema, vanished=None, subject=None):
    fields = _fields(*schema)
    fields[0] = {**fields[0], "description": desc}
    found = detect_schema_break(DBT_URN, "", fields, ["ev"], vanished=vanished)
    return [f.verdict for f in found
            if f.category == "D1_SCHEMA_BREAK" and (subject is None or f.subject == subject)]


def _gone(name, operation="REMOVE"):
    return {name: VanishedField(name=name, operation=operation, observed_at=1785043063766,
                                semantic_version="1.0.0",
                                datahub_says=f"removal of field: '{name}'")}


def test_a_rename_candidate_in_the_current_schema_still_asserts():
    """The TLC event, and it must survive with no change history at all."""
    assert _verdicts("Includes `airport_fee`.", "Airport_fee", "fare_amount",
                     vanished=None, subject="airport_fee") == ["DRIFT"]


def test_a_field_datahub_says_was_removed_asserts():
    """The other half: deleted with no similarly-named replacement to point at."""
    assert _verdicts("Derived from `legacy_total`.", "amount", "id",
                     vanished=_gone("legacy_total"), subject="legacy_total") == ["DRIFT"]


def test_the_change_event_travels_with_the_finding():
    """A steward has to be able to check the claim against DataHub's own log."""
    fields = _fields("amount")
    fields[0] = {**fields[0], "description": "Derived from `legacy_total`."}
    f = [x for x in detect_schema_break(DBT_URN, "", fields, ["ev"], vanished=_gone("legacy_total"))
         if x.subject == "legacy_total"][0]

    assert "1.0.0" in f.reality and "removal of field" in f.reality


def test_enumerated_values_are_structurally_incapable_of_asserting():
    """dbt_fivetran_log. No marker list: `broken` was never a field, so there is nothing to assert."""
    desc = ("Current sync status. Possible values include "
            "`broken`, `deleted`, `incomplete`, `connected`, `paused`")
    assert "DRIFT" not in _verdicts(desc, "connection_health", "connection_id",
                                    vanished=_gone("something_else"))


def test_entity_type_names_need_no_special_case():
    """dbt_hubspot: DEAL/CONTACT/COMPANY are object types, absent from the change log."""
    assert "DRIFT" not in _verdicts("Array of `DEAL` ids associated with the ticket.",
                                    "deal_ids", "ticket_id", vanished={})


def test_foreign_key_prose_needs_no_relation_marker():
    assert "DRIFT" not in _verdicts(
        "Foreign key referencing the ID of the `account` that the user belongs to.",
        "account_id", "user_id", vanished={})


def test_an_unresolved_doc_block_yields_no_field_candidate():
    """dbt_hubspot ships `{{ doc("history_source") }}`; the argument is a lookup key."""
    verdicts = _verdicts('{{ doc("history_source") }}', "change_source", "id", vanished={})
    assert "DRIFT" not in verdicts
    assert "INSUFFICIENT_EVIDENCE" in verdicts


def test_no_change_history_is_reported_as_such():
    """Absence of history is not evidence of drift, and the reader must be told which it was."""
    fields = _fields("new_field")
    fields[0] = {**fields[0], "description": "Derived from `old_field`."}
    never = [f for f in detect_schema_break(DBT_URN, "", fields, ["ev"], vanished=None)
             if f.subject == "old_field"][0]
    checked = [f for f in detect_schema_break(DBT_URN, "", fields, ["ev"], vanished={})
               if f.subject == "old_field"][0]

    assert never.verdict == checked.verdict == "INSUFFICIENT_EVIDENCE"
    assert "no change history" in never.reality
    assert "no change history" not in checked.reality


def test_spurious_renames_are_filtered_by_the_current_schema():
    """DataHub's differ is positional; on a busy diff it reports renames that did not happen.

    Real output from replaying NYC TLC schema history: three fields were claimed
    to have vanished, two of which are still in the schema. Only the third is.
    """
    events = [
        {"operation": "MODIFY", "field": "RatecodeID", "timestamp": 1, "semantic_version": "1.0.0",
         "description": "renaming of the field 'RatecodeID to Airport_fee'"},
        {"operation": "MODIFY", "field": "VendorID", "timestamp": 1, "semantic_version": "1.0.0",
         "description": "renaming of the field 'VendorID to RatecodeID'"},
        {"operation": "REMOVE", "field": "airport_fee", "timestamp": 1, "semantic_version": "1.0.0",
         "description": "removal of field: 'airport_fee'"},
    ]
    gone = vanished_fields(events, current={"RatecodeID", "VendorID", "Airport_fee"})

    assert set(gone) == {"airport_fee"}


def test_a_field_that_came_back_is_not_vanished():
    """Removed in one version, re-added in a later one. The log has both; only the end state counts."""
    events = [
        {"operation": "REMOVE", "field": "amount", "timestamp": 1, "semantic_version": "1.0.0",
         "description": "removal of field: 'amount'"},
        {"operation": "ADD", "field": "amount", "timestamp": 2, "semantic_version": "1.1.0",
         "description": "newly added field 'amount'"},
    ]
    assert vanished_fields(events, current={"amount"}) == {}


# --- Documentation left attached to a field that no longer exists -----------
# The purest form of the problem, and the one nobody can see. A human documents
# a column through the UI; that text lands in editableSchemaMetadata. The
# pipeline later drops the column, which rewrites schemaMetadata and never
# touches the editable aspect. The description stays, attached to nothing.
# DataHub does not clean it up and the UI does not render it -- the field is
# gone, so there is no row to show it on -- but it is still in the graph and
# every agent reading the catalog gets it.

from stilltrue.detectors import detect_orphaned_docs  # noqa: E402


def test_a_description_on_a_removed_field_is_orphaned():
    found = detect_orphaned_docs(
        DBT_URN,
        authored_fields={"order_id": "Order id", "legacy_total": "Total before the 2024 rewrite"},
        schema_fields={"order_id", "customer_id"},
        evidence_ids=["ev"],
    )
    assert [f.subject for f in found] == ["legacy_total"]
    assert found[0].verdict == "DRIFT"
    assert "Total before the 2024 rewrite" in found[0].claim


def test_documentation_on_live_fields_is_not_reported():
    assert detect_orphaned_docs(
        DBT_URN,
        authored_fields={"order_id": "Order id"},
        schema_fields={"order_id", "customer_id"},
        evidence_ids=["ev"],
    ) == []


def test_an_empty_description_is_not_orphaned_documentation():
    """A blank entry is a leftover key, not something a human wrote."""
    assert detect_orphaned_docs(
        DBT_URN,
        authored_fields={"legacy_total": "   "},
        schema_fields={"order_id"},
        evidence_ids=["ev"],
    ) == []


def test_an_empty_schema_abstains_rather_than_flagging_everything():
    """No schema read means no evidence; it must not read as 'every field is gone'."""
    assert detect_orphaned_docs(
        DBT_URN,
        authored_fields={"order_id": "Order id"},
        schema_fields=set(),
        evidence_ids=["ev"],
    ) == []
