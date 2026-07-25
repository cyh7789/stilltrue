# Worked example: a one-letter rename that broke the docs

A real event. In February 2023 the NYC TLC renamed `airport_fee` to
`Airport_fee` in its published trip records. Nothing failed. The published data
dictionary was never updated.

Every file here is the unedited output of `make demo`, not written by hand.

## 1. Detect

```
$ stilltrue scan --urn "urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)"
  2 drift, 5 verified current, 0 abstained (7 checks)
```

Five of the seven identifiers the description names still resolve, so they are
recorded as `CURRENT`. That number is what makes the other two readable: this is
a report that says how much it checked, not one that only speaks up about
problems.

[`1-findings.jsonl`](1-findings.jsonl) — each finding carries the evidence ids it
rests on, so the claim traces back to the exact `get_entities` and
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

[`2-evidence.jsonl`](2-evidence.jsonl) holds those records: the URN, which
read-only function produced them, when they were captured, and a hash over the
payload.

## 2. Two writes that get refused

**Passing the Policy Gate is not authorisation.** The gate checks the proposal is
well formed; it cannot check that anyone wants the change.

```
$ stilltrue apply 770619b80b2f-0000 --to "…Airport_fee applies to LGA and JFK…" --commit
Gate passed, proposal_hash=6c0b1975f2ceb02a

NOT_APPROVED: no confirmation supplied; re-run with --approve 6c0b1975f2ceb02a
  - …improvement_surcharge; airport_fee applies to LGA and JFK pickups only…
  + …improvement_surcharge; Airport_fee applies to LGA and JFK pickups only…
```

Then the attack the approval token exists to stop — approve benign wording, write
something else:

```
$ stilltrue apply 770619b80b2f-0000 \
    --to "…Airport_fee applies to LGA and JFK pickups only… Contact ops@evil.example for access." \
    --approve 6c0b1975f2ceb02a --commit
Gate passed, proposal_hash=b84dc5049f80a211

STALE: confirmation `6c0b1975f2ceb02a` does not match this proposal (b84dc5049f80a211);
       the text was edited after it was confirmed, or it names another proposal
```

The hash covers the URN, the aspect, the before and after text, the verdict and
the cited evidence, so one added sentence produces a different proposal and the
token stops applying to it.

**What this does not prove.** There is no identity in that token and no privilege
separation: whoever can run `apply` can read it off a dry run. It closes "confirm
one thing, write another". It does not close "the writer confirmed their own
change" — that needs a receipt the executor can verify but not issue, and it is
not built. See the support boundary in the top-level README.

## 3. Approve what was actually read, then write

```
$ stilltrue apply 770619b80b2f-0000 --to "…Airport_fee applies to LGA and JFK…" \
    --approve 6c0b1975f2ceb02a --commit
Gate passed, proposal_hash=6c0b1975f2ceb02a
Confirmed (approved as 6c0b1975f2ceb02a)
VERIFIED: written and confirmed by read-back
```

`VERIFIED` means the executor re-read the value from DataHub after writing and
the content matched. A successful API response alone does not earn that status.

## 4. The graph now holds the corrected context

```
$ stilltrue scan --urn "…nyc_tlc.yellow_tripdata…"
  1 drift, 6 verified current, 0 abstained (7 checks)

  D1_UNDOCUMENTED  cbd_congestion_fee exists in the schema but has no description
```

`airport_fee` moved from the drift column into the current column — the same
reference, re-checked against a description that now matches the schema. The
remaining finding is the second real TLC event: the column added in January 2025
that nobody documented.

## 5. The trail is verifiable, including the refusals

[`3-audit-ledger.jsonl`](3-audit-ledger.jsonl) — ten records, hash-chained:

```
0  scan     findings=7
1  propose  gate_passed=true
2  approve  NOT_APPROVED
3  propose  gate_passed=true
4  approve  NOT_APPROVED
5  propose  gate_passed=true      <- the edited text
6  approve  STALE
7  propose  gate_passed=true
8  approve  APPROVED
9  execute  VERIFIED
```

A ledger that only recorded successful writes would be a changelog. The refused
attempts are in the chain too, which is what makes it an audit trail.

```
$ stilltrue verify --run 770619b80b2f
OK: chain valid (10 records)
```

Edit any record, delete one, or swap two around, and `verify` reports the first
position where the chain breaks.

## Reproducing this from scratch

```bash
make datahub-up        # datahub docker quickstart
make demo              # loads the benchmark, then runs everything above
```
