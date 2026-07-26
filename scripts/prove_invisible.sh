#!/usr/bin/env bash
# Does removing an orphaned description change the page? Measure it, don't assert it.
#
# The claim is that DataHub renders nothing for a description keyed to a field
# the schema no longer has, so resolving one is invisible. Showing the same image
# file twice does not establish that -- it establishes that a file was reused.
# Two independent captures at the same viewport, and a pixel diff, do.
set -euo pipefail

URN='urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)'
PY=.venv/bin/python

# Writes to runs/ by default. This script re-captures both frames, so pointing it
# at docs/evidence would overwrite the committed pair it exists to explain, and a
# rerun during filming would silently replace the images the documents cite.
# `--publish` is how they get regenerated, on purpose.
#
# Parsed in a loop rather than by position: an earlier version assigned $1 to
# SERVER before testing it for the flag, so `prove_invisible.sh --publish` -- the
# obvious way to type it -- set SERVER=--publish and then published anyway.
SERVER=
OUT=runs/invisible
end_of_options=
for arg in "$@"; do
  if [ -z "$end_of_options" ]; then
    case "$arg" in
      --) end_of_options=1; continue ;;
      --publish) OUT=docs/evidence; continue ;;
      -*) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
  fi
  [ -n "$arg" ] || { echo "server may not be empty" >&2; exit 2; }
  [ -z "$SERVER" ] || { echo "two servers given: $SERVER and $arg" >&2; exit 2; }
  # After `--` a flag becomes an operand, per convention -- so `-- --publish`
  # means "the server is literally --publish". Nothing good follows from that;
  # every use here is an http address, so require one and fail loudly instead of
  # handing garbage to curl three steps later.
  case "$arg" in
    http://*|https://*) ;;
    *) echo "server must be an http(s) URL, got: $arg" >&2; exit 2 ;;
  esac
  SERVER="$arg"
done
SERVER="${SERVER:-http://localhost:8080}"
mkdir -p "$OUT"
echo "server $SERVER, frames -> $OUT"

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "1. Rebuild the drifted state, orphan included"
$PY bench/oracles/build_tlc_benchmark.py --server "$SERVER" 2>&1 | tail -3

step "2. Fix the description, so the orphan is the only thing left to change"
.venv/bin/stilltrue scan --urn "$URN" --server "$SERVER" > /dev/null 2>&1
BREAK=$(.venv/bin/stilltrue findings 2>/dev/null | grep SCHEMA_BREAK | sed 's/.*\[\([^]]*\)\].*/\1/')
FIXED='NYC Yellow Taxi trip records. Each row is one completed trip. Fare components are broken out into fare_amount, extra, mta_tax, tip_amount, tolls_amount and improvement_surcharge; Airport_fee applies to LGA and JFK pickups only. Distances are in miles and all monetary values are USD.'
TOKEN=$({ .venv/bin/stilltrue apply "$BREAK" --to "$FIXED" --server "$SERVER" 2>/dev/null || true; } \
        | grep -o 'proposal_hash=[0-9a-f]*' | cut -d= -f2)
.venv/bin/stilltrue apply "$BREAK" --to "$FIXED" --approve "$TOKEN" --commit --server "$SERVER" 2>&1 | tail -1

step "3. Capture with the orphan still in the graph"
$PY scripts/capture_ui.py "$URN" "$OUT/05-orphan-present.png" --tab Columns --search airport 2>&1 | tail -1

step "4. Remove the orphan"
.venv/bin/stilltrue scan --urn "$URN" --server "$SERVER" > /dev/null 2>&1
ORPHAN=$(.venv/bin/stilltrue findings 2>/dev/null | grep ORPHANED_DOC | sed 's/.*\[\([^]]*\)\].*/\1/')
OTOKEN=$({ .venv/bin/stilltrue apply "$ORPHAN" --server "$SERVER" 2>/dev/null || true; } \
         | grep -o 'proposal_hash=[0-9a-f]*' | cut -d= -f2)
.venv/bin/stilltrue apply "$ORPHAN" --approve "$OTOKEN" --commit --server "$SERVER" 2>&1 | tail -1

step "5. Capture again, same viewport, same script"
$PY scripts/capture_ui.py "$URN" "$OUT/06-orphan-removed.png" --tab Columns --search airport 2>&1 | tail -1

step "6. Diff the two frames"
$PY scripts/diff_frames.py "$OUT/05-orphan-present.png" "$OUT/06-orphan-removed.png"
