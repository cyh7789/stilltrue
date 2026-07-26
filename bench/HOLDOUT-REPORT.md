# Frozen holdout v2: fivetran/dbt_hubspot

> Scored once, on 2026-07-26T03:56:57+00:00 code.
> Regenerate: `python3 bench/run_holdout_bench.py <clone> drift-labels-dbt-hubspot.jsonl`

Unlike the two benchmarks in this repo, this source was fetched **after** the
freeze, chosen by a rule committed before any candidate was inspected, and
scored once. The numbers below are what came out.

| | Result |
|---|---|
| IDENTIFIER_CHANGE recall | **4/12** |
| False positives on negatives | **58/421** (13.78%) |
| Abstained on a positive | 3 |
| Positives with no SQL at c2 (unscorable) | 0 |

Selection: `bench/holdout-selection.json`. Freeze: `bench/freeze.json`,
verifiable with `python3 bench/freeze.py --check`.

---

## Two holdouts now, and they agree

*Written after the single scored run. `python3 bench/freeze.py --check` still passes.*

| | recall | false positives |
|---|---|---|
| dbt_shopify — development | 7/10 — 70% | 2.17% |
| **dbt_fivetran_log — holdout v1** (v1 code) | **13/32 — 41%** | 9.59% |
| **dbt_hubspot — holdout v2** (v2 code) | **4/12 — 33%** | 13.78% |

Two independently drawn sources, two freezes, two single runs, and they say the
same thing: **in the field this detector finds a third to a half of what the
development benchmark suggests.** One holdout can be unlucky. Two agreeing is a
property of the tool.

The two are not a before/after of the fix — different sources *and* different
code — so nothing here shows the fix helped recall. What it did to precision is
visible below, but only within v2.

## Where the 58 false positives come from

Split, because the two halves are different kinds of fact:

| | count | what it is |
|---|---|---|
| `{{ doc("history_source") }}` and friends | **50** | an artifact of our label miner |
| prose | **8** (1.90% of 421) | the detector genuinely getting it wrong |

`dbt_hubspot` documents heavily with **doc blocks** — the yml holds
`{{ doc("history_source") }}` and dbt resolves it at compile time. Our miner
reads the yml, so it captures the template, not the text. A human in DataHub
sees the resolved description; the detector here was handed Jinja and pulled
`history_source` out of it as a field reference.

That is a limitation of `mine_drift_labels.py`, and it is not fixed here for the
same reason nothing else is: the frozen files stay frozen. **The headline stays
58 and 13.78%.** The split is reported so the number can be read, not so it can
be restated — and it changes nothing about recall, because **0 of the 12
IDENTIFIER_CHANGE positives are doc blocks.** 4/12 is unaffected.

The 8 real ones are one shape, and it is the shape already known from
`showcase-ecommerce`: entity types in prose.

```
"Array of `DEAL` ids associated with the ticket."
"Array of `CONTACT` emails associated with the ticket."
```

`DEAL`, `CONTACT`, `COMPANY` are HubSpot object types. `names_something_else`
catches enumerations and relational prose; it does not know an uppercase token
is a type name. Addressable, not addressed.

## What the two rounds cost and bought

Round 1 said 41% and its two failure modes were fixed. Round 2 says 33% on a
different source with different failure modes. The pattern to take from that is
not "the fix failed" — it is that **each new corpus writes prose the last one
did not**, and a rule set tuned on two of them meets a third that does something
else. Every round has found a fresh way for a description to name something that
is not a column.

That is the honest shape of this problem, and it is worth more on the record than
a number that only holds on the data it was built from.
