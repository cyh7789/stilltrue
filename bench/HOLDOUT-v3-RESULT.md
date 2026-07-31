# Third holdout: no candidate satisfied the frozen thresholds

The walk declared in [`HOLDOUT-v3-DECLARATION.md`](HOLDOUT-v3-DECLARATION.md) ran
once and stopped without selecting anything. That declaration says a null result
is the published result, so here it is.

```
python3 bench/select_holdout_v3.py /tmp/holdout-v3-search
population: 80 repositories across 6 organisations
thresholds imported from the frozen bench/select_holdout.py
...
no candidate satisfied the frozen thresholds
```

Full rejection log with the threshold each repository missed:
[`holdout-v3-walk.log`](holdout-v3-walk.log). Nothing was scored, so no number
from this walk enters any claim.

## Why all 80 failed

| Rejected at | Count |
|---|---|
| licence outside {Apache-2.0, MIT, BSD-2, BSD-3} | 36 |
| fewer than 200 commits | 21 |
| fewer than 50 column descriptions | 21 |
| fewer than 30 mined positives | 2 |

The three large buckets are all the same fact seen from different angles: the
organisations that publish dbt code outside fivetran mostly publish *tooling*.
`dbt-labs/dbt-utils`, `dbt-core`, `dbt-adapters`, `dbt-codegen` and the rest are
macro packages, adapters and demo projects. They have no `models/**/*.yml` with
documented columns, so the description threshold rejects them before mining is
even attempted. Another 36 are training and partner-demo repositories with no
licence file at all.

## The two that reached the mining stage

These are the interesting rejections, because the miner actually ran:

```
skip brooklyn-data/dbt_artifacts              mined positives 0 < 30
skip elementary-data/dbt-data-reliability     mined positives 19 < 30
```

Both are real modelled dbt packages with documented columns. The phenomenon
exists in the second one: 19 columns left a model's SQL while their description
outlived them. It is below the frozen threshold of 30, so it was rejected.

**It was not scored, and the threshold was not lowered to admit it.** Choosing a
corpus after seeing that it produces a workable number of labels is the selection
bias the frozen rule exists to prevent, and 19 is exactly the sort of near-miss
that makes lowering a threshold feel reasonable.

## What this changes about the claim

The 14 of 14 across 503 correct descriptions still stands, and it still rests on
two repositories from one organisation. This walk was an attempt to widen that
and it failed, so the boundary is now measured rather than assumed:

- Within the six organisations searched, **no corpus meets the same bar the first
  two met**. The shape those two have, a large dbt package with 50+ documented
  columns and years of schema churn, is not common outside the company that
  produces them at scale.
- The mechanism is not shown to fail elsewhere. It is shown to be **hard to test**
  elsewhere, which is a different and smaller statement, and the one the evidence
  actually supports.
- A larger population would probably find a passing candidate: private warehouses
  and the analytics repositories of individual companies have exactly this shape.
  None of them is public, which is why the search was over packages in the first
  place.

## Reproducing

```bash
python3 bench/select_holdout_v3.py /tmp/holdout-v3-search
```

Requires network access to the GitHub API and clones each candidate that passes
the licence check. The thresholds and the miner are imported from the frozen
`bench/select_holdout.py`; `bench/freeze.py --check` is green before and after.
