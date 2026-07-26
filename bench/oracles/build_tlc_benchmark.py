#!/usr/bin/env python3
"""Load the NYC TLC benchmark into DataHub.

Two states of the same dataset, taken from published parquet schemas:

  authored side: the 2023-01 schema, plus a description written against it
  reality side:  the 2025-01 schema, which renamed airport_fee -> Airport_fee
                 and added cbd_congestion_fee

The description is deliberately never updated. That is the point: it is what a
team wrote when the columns still matched, and nobody went back to fix it.
Expected findings fall out of the diff between the two published schemas, so no
human labelled anything here.

The load runs in the same order those states happened, because one of the
findings only exists if it does. A person documents `airport_fee` on the page
while that column is current; the write lands in `editableSchemaMetadata`, which
is a separate aspect from the ingested schema. The next ingestion replaces the
schema and renames the column. DataHub keeps the person's sentence, still keyed
to `airport_fee`, and shows it nowhere -- the UI renders descriptions per
current field, so a field that is gone has nothing to render into. Loading only
the final state would skip that entirely.

Usage:
  python3 build_tlc_benchmark.py [--server http://localhost:8080]
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

TLC_PARQUET = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{}.parquet"
AUTHORED_MONTH = "2023-01"
REALITY_MONTH = "2025-01"

# Written against the 2023-01 columns. Left untouched on purpose.
DESCRIPTION = (
    "NYC Yellow Taxi trip records. Each row is one completed trip. "
    "Fare components are broken out into fare_amount, extra, mta_tax, tip_amount, "
    "tolls_amount and improvement_surcharge; airport_fee applies to LGA and JFK "
    "pickups only. Distances are in miles and all monetary values are USD."
)


# Column descriptions as the TLC data dictionary described them when the
# 2023-01 schema was current. cbd_congestion_fee is absent on purpose: it only
# appeared in 2025-01 and nobody went back to document it.
COLUMN_DOCS = {
    "VendorID": "Code indicating the TPEP provider that supplied the record.",
    "tpep_pickup_datetime": "The date and time when the meter was engaged.",
    "tpep_dropoff_datetime": "The date and time when the meter was disengaged.",
    "passenger_count": "The number of passengers in the vehicle, entered by the driver.",
    "trip_distance": "The elapsed trip distance in miles reported by the taximeter.",
    "RatecodeID": "The final rate code in effect at the end of the trip.",
    "store_and_fwd_flag": "Whether the record was held in vehicle memory before sending to the vendor.",
    "PULocationID": "TLC Taxi Zone in which the taximeter was engaged.",
    "DOLocationID": "TLC Taxi Zone in which the taximeter was disengaged.",
    "payment_type": "Numeric code signifying how the passenger paid for the trip.",
    "fare_amount": "The time-and-distance fare calculated by the meter.",
    "extra": "Miscellaneous extras and surcharges.",
    "mta_tax": "MTA tax automatically triggered based on the metered rate in use.",
    "tip_amount": "Tip amount. Automatically populated for credit card tips; cash tips are not included.",
    "tolls_amount": "Total amount of all tolls paid in trip.",
    "improvement_surcharge": "Improvement surcharge assessed on hailed trips at the flag drop.",
    "total_amount": "The total amount charged to passengers. Does not include cash tips.",
    "congestion_surcharge": "Total amount collected in trip for NYS congestion surcharge.",
    "Airport_fee": "For pickups at LaGuardia and John F. Kennedy airports.",
}


# Written on the dataset page while `airport_fee` was still a column, the way a
# steward annotates something the data dictionary does not cover. The rename in
# 2023-02 leaves it keyed to a name the schema no longer has.
DEPARTED_COLUMN = "airport_fee"
STEWARD_NOTE = (
    "Only charged on LGA and JFK pickups. Zero for every other pickup zone, "
    "so filter it out before averaging."
)


def annotate_column(server: str, column: str, note: str) -> None:
    """Write a column description the way the UI does -- editableSchemaMetadata."""
    from datahub.sdk import DataHubClient
    from datahub_agent_context import DataHubContext
    from datahub_agent_context.mcp_tools import descriptions

    with DataHubContext(DataHubClient(server=server)):
        descriptions.update_description(
            entity_urn="urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)",
            operation="replace", description=note, column_path=column,
        )


SCHEMA_CACHE = Path(__file__).resolve().parent / "tlc-schemas.json"


SENTINEL_MONTH = "2023-01"          # published since 2023; only a throttle hides it


def publication_status(month: str) -> int:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(TLC_PARQUET.format(month), method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def is_published(month: str) -> bool:
    """Whether the TLC has published this month, distinguished from a rate limit.

    Two things have to be told apart and the status code alone cannot do it.
    fsspec raises the same `FileNotFoundError` either way, and the S3 origin
    behind this CloudFront has no ListBucket permission, so a file that does not
    exist comes back 403 -- the same code the rate limiter uses. Read through
    that lens a throttled month looks exactly like one the TLC never published,
    which is how "later months not yet published" ends up in a report about a
    rate limit.

    A sentinel separates them. `2023-01` has been published for years, so if it
    answers 200 while the month in question answers 403, that 403 is about the
    file. If the sentinel is also 403, nothing can be concluded about any month
    and the caller has to wait rather than write down a fact.
    """
    if publication_status(month) == 200:
        return True
    if publication_status(SENTINEL_MONTH) == 200:
        return False
    raise RuntimeError(
        f"TLC CDN is rate-limiting this client: {SENTINEL_MONTH} is unreachable too. "
        f"Wait and rerun -- do not record {month} as unpublished."
    )


def remote_schema(month: str) -> list[tuple[str, str]]:
    """The published columns for one month. Cached, because the CDN throttles.

    A cache hit is the same bytes the CDN served on the first run -- the file for
    a past month does not change. Without it, a 31-month replay spends its last
    few months arguing with a rate limiter.
    """
    cache: dict[str, list[list[str]]] = {}
    if SCHEMA_CACHE.exists():
        cache = json.loads(SCHEMA_CACHE.read_text(encoding="utf-8"))
    if month in cache:
        return [(n, t) for n, t in cache[month]]

    import fsspec
    import pyarrow.parquet as pq

    if not is_published(month):
        raise FileNotFoundError(f"TLC has not published {month}")

    fs = fsspec.filesystem("https")
    schema = pq.read_schema(fs.open(TLC_PARQUET.format(month)))
    cols = [(f.name, str(f.type)) for f in schema]

    cache[month] = [[n, t] for n, t in cols]
    SCHEMA_CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return cols


def main() -> None:
    server = "http://localhost:8080"
    if "--server" in sys.argv:
        server = sys.argv[sys.argv.index("--server") + 1]

    from datahub.sdk import DataHubClient, Dataset

    authored = remote_schema(AUTHORED_MONTH)
    reality = remote_schema(REALITY_MONTH)

    authored_names = {n for n, _ in authored}
    reality_names = {n for n, _ in reality}
    print(f"{AUTHORED_MONTH}: {len(authored)} columns")
    print(f"{REALITY_MONTH}: {len(reality)} columns")
    print(f"  gone:  {sorted(authored_names - reality_names)}")
    print(f"  added: {sorted(reality_names - authored_names)}")

    client = DataHubClient(server=server)

    def upsert(schema: list[tuple[str, str]]) -> Dataset:
        ds = Dataset(
            platform="s3",
            name="nyc_tlc.yellow_tripdata",
            description=DESCRIPTION,
            schema=[(name, dtype, COLUMN_DOCS.get(name, "")) for name, dtype in schema],
        )
        client.entities.upsert(ds)
        return ds

    upsert(authored)
    annotate_column(server, DEPARTED_COLUMN, STEWARD_NOTE)

    # The reality side: the schema as published in 2025-01. Column descriptions
    # are still the ones written for the 2023-01 columns, so cbd_congestion_fee
    # arrives undocumented -- what happens when a column is added and nobody
    # updates the docs.
    dataset = upsert(reality)

    print(f"\nloaded as {dataset.urn}")
    print("expected findings (derived from the schema diff, not hand-labelled):")
    print("  1. description references `airport_fee`, schema has `Airport_fee`  -> rename")
    print("  2. `cbd_congestion_fee` present in schema, absent from the description")
    print(f"  3. the note on `{DEPARTED_COLUMN}` outlived the column it describes")


if __name__ == "__main__":
    main()
