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

Usage:
  python3 build_tlc_benchmark.py [--server http://localhost:8080]
"""

from __future__ import annotations

import sys
import warnings

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


def remote_schema(month: str) -> list[tuple[str, str]]:
    import fsspec
    import pyarrow.parquet as pq

    fs = fsspec.filesystem("https")
    schema = pq.read_schema(fs.open(TLC_PARQUET.format(month)))
    return [(f.name, str(f.type)) for f in schema]


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
    dataset = Dataset(
        platform="s3",
        name="nyc_tlc.yellow_tripdata",
        description=DESCRIPTION,
        # The reality side: the schema as published in 2025-01. Descriptions are
        # the ones written for the 2023-01 columns, so cbd_congestion_fee arrives
        # undocumented -- exactly what happens when a column is added and nobody
        # updates the docs.
        schema=[(name, dtype, COLUMN_DOCS.get(name, "")) for name, dtype in reality],
    )
    client.entities.upsert(dataset)

    print(f"\nloaded as {dataset.urn}")
    print("expected findings (derived from the schema diff, not hand-labelled):")
    print("  1. description references `airport_fee`, schema has `Airport_fee`  -> rename")
    print("  2. `cbd_congestion_fee` present in schema, absent from the description")


if __name__ == "__main__":
    main()
