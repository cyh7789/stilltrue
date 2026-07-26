# Why D2 (freshness drift) is not implemented

The design enumerated five drift families. Two of them — D2 freshness and D5
semantic conflict — need a signal that an open-source DataHub catalog does not
carry. This page records the measurements, because "we ran out of time" and "the
data does not exist" are different statements and only one of them is true here.

D2's rule is one line: *a description claims a refresh cadence; the observed gap
between updates exceeds 3× that cadence.* It needs both sides.

## The authored side: nobody claims a cadence

Scanned every dataset in a quickstart loaded with `showcase-ecommerce` —
DataHub's own 1,049-entity demo catalog, the richest sample they publish.

| | Count |
|---|---|
| Datasets | 76 |
| With a description | 20 |
| Descriptions claiming a refresh cadence | **0** |

One regex hit turned out to be a false match. `order_entry.regions` says:

> It is **refreshed on** query with the current timestamp, ensuring that
> downstream consumers have access to the most up-to-date geographic
> information.

That is the opposite of a cadence claim — it says the table has no refresh
schedule at all.

## The reality side: three routes, no data

**1. `get_entities` returns no timestamp.** The Agent Context Kit's dataset
response carries exactly these keys:

```
['editableProperties', 'health', 'name', 'platform',
 'relatedDocuments', 'schemaMetadata', 'urn']
```

No `properties`, no `operations`, no `lastModified`. The only usage-and-recency
block in the Kit's GraphQL (`statsSummary`) is annotated `#[CLOUD]` on every
line — DataHub Cloud only.

**2. `get_dataset_assertions(assertion_type="FRESHNESS")` returns nothing.**
DataHub models freshness as an assertion type and the Kit exposes it, which
would be the correct signal. Across all 76 datasets: **0 assertions of any
type.** The API exists; the catalog is empty.

**3. `datasetProperties.lastModified` exists on 26 of 76 datasets** via the REST
API — but every value clusters on the datapack's own build date (2025-12-08/09).
It records when the sample was authored, not when a pipeline last ran. Comparing
a cadence claim against it would measure the age of the demo file.

## The ground truth we were told to use does not exist

The hackathon's Resources page lists a `nyc-taxi` pack with "planted freshness
issues", which would have supplied both sides at once. It is not in the registry
the CLI actually reads
([`registry.json`](https://raw.githubusercontent.com/datahub-project/datahub/master/metadata-ingestion/src/datahub/cli/datapack/resources/registry.json)):

```
$ datahub datapack load nyc-taxi
Error: Unknown data pack 'nyc-taxi'.
       Available packs: bootstrap, showcase-ecommerce
```

The registry contains two packs. `nyc-taxi`, `healthcare` and `fiction-retail`
are described on that page as datasets, not as loadable packs, and no
distribution for them is given.

## The decision

Implementing D2 here would mean writing both sides ourselves: descriptions that
claim cadences we invented, checked against timestamps we planted. The detector
would then pass a benchmark whose answers we authored — which is the failure
this project spent its validation work getting *out* of
([`VALIDATION-INTEGRITY.md`](VALIDATION-INTEGRITY.md)).

So D2 stays unimplemented and stays declared. The same reasoning retired D5:
`get_dataset_queries` returns `total: 0` on this catalog, and a semantic-conflict
detector fed synthetic query history is a silent failure of its own — which is
precisely the failure mode it was built to catch.

**What this is worth saying out loud:** two of five designed detectors are
blocked not by effort but by the catalog. A description drifts away from schema
and lineage because DataHub *stores* schema and lineage. It cannot tell you the
description drifted away from a refresh cadence or a query pattern, because
open-source DataHub does not store either by default. That boundary is a real
property of the problem, and it is the honest answer to "why only two
detectors".
