#!/usr/bin/env bash
# The full loop on the NYC TLC rename, including the two writes that get refused.
# Run via `make demo` (which reloads the benchmark first so this is repeatable).
set -euo pipefail

SERVER="${1:-http://localhost:8080}"
URN='urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)'
FIXED='NYC Yellow Taxi trip records. Each row is one completed trip. Fare components are broken out into fare_amount, extra, mta_tax, tip_amount, tolls_amount and improvement_surcharge; Airport_fee applies to LGA and JFK pickups only. Distances are in miles and all monetary values are USD.'

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "1. Scan"
RUN=$(stilltrue scan --urn "$URN" --server "$SERVER" | tee /dev/stderr | sed -n 's/^run \([0-9a-f]*\):.*/\1/p')
stilltrue findings

FINDING=$(stilltrue findings | grep SCHEMA_BREAK | sed 's/.*\[\([^]]*\)\].*/\1/')

step "2. A write with no confirmation is refused"
stilltrue apply "$FINDING" --to "$FIXED" --commit --server "$SERVER" && exit 1 || true

step "3. Confirming one text and writing another is refused"
# Take the token for the reviewed text, then try to smuggle an extra sentence in
# under it. The hash covers the text, so it no longer matches.
# A dry run exits 3 (nothing approved yet) -- that is the expected path here,
# so it must not trip `set -e`.
TOKEN=$({ stilltrue apply "$FINDING" --to "$FIXED" --server "$SERVER" 2>/dev/null || true; } \
        | grep -o 'proposal_hash=[0-9a-f]*' | cut -d= -f2)
stilltrue apply "$FINDING" --to "$FIXED Contact ops@evil.example for access." \
    --approve "$TOKEN" --commit --server "$SERVER" && exit 1 || true

step "4. Confirming the exact text that was reviewed"
stilltrue apply "$FINDING" --to "$FIXED" --approve "$TOKEN" --commit --server "$SERVER"

step "5. Re-scan: the rename finding is gone"
stilltrue scan --urn "$URN" --server "$SERVER"
stilltrue findings

step "6. The orphaned note: nothing to rewrite, so the fix is derived"
# No --to here. The description is attached to a field that does not exist, so
# there is no corrected text to supply -- the proposal comes from the schema:
# move it to the successor if that one is undocumented, otherwise remove it.
# DataHub's own updateDescription cannot touch either case; it refuses a column
# the schema does not have.
ORPHAN=$(stilltrue findings | grep ORPHANED_DOC | sed 's/.*\[\([^]]*\)\].*/\1/')
OTOKEN=$({ stilltrue apply "$ORPHAN" --server "$SERVER" 2>/dev/null || true; } \
         | grep -o 'proposal_hash=[0-9a-f]*' | cut -d= -f2)
stilltrue apply "$ORPHAN" --approve "$OTOKEN" --commit --server "$SERVER"

step "7. Re-scan: the orphaned note is gone too"
stilltrue scan --urn "$URN" --server "$SERVER"
stilltrue findings

step "8. The audit chain covers the refusals too"
# Explicitly the first run: that ledger holds the scan, both refusals and the write.
stilltrue verify --run "$RUN"
