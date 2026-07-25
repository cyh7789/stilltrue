# Worked example: 25 real tables, and the 14 times it said "I don't know"

The unedited output of scanning DataHub's own `showcase-ecommerce` datapack —
1,049 entities of realistic, human-written metadata that nobody planted drift
into.

```
$ stilltrue scan --limit 25
  3 drift, 0 verified current, 14 abstained (17 checks)
```

**Zero false drift verdicts.** That is the number this example exists for, and it
was bought with the fourteen abstentions.

## Why abstaining is the whole point

Real descriptions are prose. They name other tables, DataHub entity types,
pipeline steps and placeholders — all of which look exactly like a column
reference to a regex:

```
order_entry                 a schema, not a column
table_name                  a placeholder in a template
export_table_orders_to_s3   a pipeline job
DASHBOARD, DATA_JOB         DataHub entity types
deprecation_gate            a policy step
```

The first version of this detector reported every unresolved identifier as
drift. On these same 25 tables that produced **6 false drift verdicts**. The
current rule asserts drift only when it can point at a rename candidate — a case
variant or the same letters with underscores moved — and abstains otherwise.

[`1-findings.jsonl`](1-findings.jsonl) — every abstention states what it saw and
what it could not establish:

```json
{
  "category": "D1_SCHEMA_BREAK",
  "verdict": "INSUFFICIENT_EVIDENCE",
  "subject": "table_name",
  "claim": "dataset description references `table_name`",
  "reality": "the text mentions `table_name`, which is not a field here and has no close match",
  "confidence": "medium"
}
```

## What it costs

A column that was genuinely deleted, named only in a table description, with no
similarly-named replacement, reads as abstention rather than drift. That case is
missed on purpose.

The trade is deliberate: a report with false positives stops being read at all,
and then the true positives go with it. `INSUFFICIENT_EVIDENCE` is a verdict, not
a failure to reach one.

## The three drift findings it did report

They are in the same file, filtered with `stilltrue findings --verdict DRIFT`.
Each is an undocumented-column case on a table that is itself documented — the
"documentation stopped keeping up" shape, not a guess about prose.

## Reproducing

```bash
datahub datapack load showcase-ecommerce
stilltrue scan --limit 25
stilltrue findings --verdict INSUFFICIENT_EVIDENCE
```
