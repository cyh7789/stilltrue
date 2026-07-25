# Worked example: a one-letter rename that broke the docs

A real event. In February 2023 the NYC TLC renamed `airport_fee` to
`Airport_fee` in its published trip records. Nothing failed. The published data
dictionary was never updated.

This directory is the unedited output of running the tool against that dataset
loaded into DataHub. Every file here was produced by the commands below, not
written by hand.

## 1. Detect

```
$ sentinel scan --urn "urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)"
  2 findings (2 drift, 0 abstained)
```

[`1-findings.jsonl`](1-findings.jsonl) — the finding carries the evidence ids it
rests on, so the claim can be traced back to the exact `get_entities` and
`list_schema_fields` calls that produced it:

```json
{
  "category": "D1_SCHEMA_BREAK",
  "verdict": "DRIFT",
  "subject": "airport_fee",
  "claim": "dataset description references `airport_fee`",
  "reality": "the schema has no `airport_fee`, but it does have `Airport_fee`",
  "evidence_ids": ["ev_244ba567531119f2", "ev_1dc997884ca32e38"],
  "suspected_rename": "Airport_fee"
}
```

## 2. Propose, gate, write back

```
$ sentinel apply 2062223fa0a5-0000 --to "…Airport_fee applies to LGA and JFK pickups only…" --commit
Gate passed, proposal_hash=6c0b1975f2ceb02a
VERIFIED: written and confirmed by read-back
```

`VERIFIED` means the executor re-read the value from DataHub after writing and
the content matched. A successful API response alone does not earn that status.

## 3. The graph now holds the corrected context

Re-running the same scan against the same dataset:

```
$ sentinel scan --urn "…nyc_tlc.yellow_tripdata…"
  1 findings (1 drift, 0 abstained)

  D1_UNDOCUMENTED  cbd_congestion_fee exists in the schema but has no description
```

The rename finding is gone because the description in DataHub no longer claims
`airport_fee`. The remaining finding is the second real TLC event — the column
added in January 2025 that nobody documented.

## 4. The trail is verifiable

[`3-audit-ledger.jsonl`](3-audit-ledger.jsonl) — three records, hash-chained:

```
scan     {"findings": 2, "evidence": ["ev_244ba567531119f2", "ev_1dc997884ca32e38"]}
propose  {"gate_passed": true, "proposal_hash": "6c0b1975f2ceb02a…"}
execute  {"status": "VERIFIED", "detail": "written and confirmed by read-back"}
```

```
$ sentinel verify --run 2062223fa0a5
OK: chain valid (3 records)
```

Edit any record, delete one, or swap two around, and `verify` reports the first
position where the chain breaks.

## Reproducing this from scratch

```bash
datahub docker quickstart
python3 bench/oracles/build_tlc_benchmark.py   # loads the dataset from public TLC data
sentinel scan --urn "urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)"
```
