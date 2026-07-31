# One-command entry points. Everything here assumes `pip install -e .` has run
# and a DataHub is reachable at $(SERVER).

SERVER ?= http://localhost:8080
TLC_URN = urn:li:dataset:(urn:li:dataPlatform:s3,nyc_tlc.yellow_tripdata,PROD)
SHOPIFY ?= /tmp/dbt_shopify

.PHONY: help demo bench-replay test check-claims datahub-up load-benchmark clean

help:
	@echo "make datahub-up       start a local DataHub (takes a few minutes the first time)"
	@echo "make load-benchmark   load the NYC TLC dataset in its drifted state"
	@echo "make demo             scan -> refuse an unapproved write -> approve -> write back -> verify"
	@echo "make bench-replay     re-run every baseline and regenerate bench/REPORT.md"
	@echo "make test             unit tests"
	@echo "make check-claims     every number in the docs, against the file it came from"
	@echo "make codespace-demo   one command from a cold Codespace: DataHub, data, full loop"

datahub-up:
	datahub docker quickstart

# The zero-install path: a cold GitHub Codespace to the whole loop, one command.
# Kept separate from `demo` so the local path stays as short as it was.
codespace-demo:
	@echo "==> starting DataHub (first run pulls images, allow ~5 minutes)"
	datahub docker quickstart
	@echo "==> waiting for the graph to accept writes"
	@until curl -sf $(SERVER)/health >/dev/null; do sleep 5; done
	@$(MAKE) demo
	@echo
	@echo "The UI is on port 9002 (datahub/datahub). The dataset the demo just"
	@echo "corrected: nyc_tlc.yellow_tripdata, Columns tab, search airport."

# Resets the description to what it was before anyone fixed it, so `make demo`
# is repeatable -- the demo's whole point is writing that fix back.
load-benchmark:
	python3 bench/oracles/build_tlc_benchmark.py --server $(SERVER)

demo: load-benchmark
	@bash scripts/demo.sh "$(SERVER)"

bench-replay:
	python3 bench/run_bench.py --server $(SERVER)
	@echo
	@echo "dbt_shopify needs a local clone; set SHOPIFY=<path> to include it."
	@test -d "$(SHOPIFY)" && python3 bench/run_shopify_bench.py "$(SHOPIFY)" || true

check-claims:
	python3 scripts/check_claims.py

test:
	python3 -m pytest -q

clean:
	rm -rf runs .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
