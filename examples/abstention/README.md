# Worked example: 25 real tables, and the 29 times it said "I don't know"

The unedited output of scanning DataHub's own `showcase-ecommerce` datapack —
realistic, human-written metadata that nobody planted drift into.

```
$ stilltrue scan --limit 25
  urn:li:dataset:(...b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD): schema read
    incomplete (15 of 55), skipping the orphaned-doc check
  1 drift, 6 verified current, 29 abstained (36 checks)
```

**Zero false drift verdicts.** That is the number this example exists for, and it
was bought with the twenty-nine abstentions.

## Why abstaining is the whole point

Real descriptions are prose. They name other tables, DataHub entity types,
pipeline steps and placeholders — all of which look exactly like a column
reference to a regex:

```
order_entry     a schema, not a column
order_entry_d   a truncated name in prose
table_name      a placeholder in a template
{{ … }}         Jinja the catalog never expanded
```

The first version of this detector reported every unresolved identifier as
drift. On these same tables that produced **6 false drift verdicts**. The current
rule asserts only when DataHub's change log records the field leaving, and
abstains otherwise — including when a current column merely resembles the token,
which used to be enough on its own.

[`1-findings.jsonl`](1-findings.jsonl) — every abstention states what it saw and
what it could not establish:

```json
{
  "category": "D1_SCHEMA_BREAK",
  "verdict": "INSUFFICIENT_EVIDENCE",
  "subject": "table_name",
  "reality": "`table_name` is not a field here and DataHub's change log has no record of it leaving",
  "confidence": "medium"
}
```

Note the two different reasons this verdict gives. *"The change log has no record
of it leaving"* means the log was read and said nothing. When the log could not
be read at all, the text says that instead — not having looked is not the same
as having looked and found nothing, and a report that blurs the two is telling
you it checked when it did not.

## The truncated read in the output above

That first line is not noise, it is the same discipline. `list_schema_fields`
pages and also stops at a token budget: this table has 55 columns and 15 came
back. A column missing from a short page is indistinguishable from a column the
schema does not have — which is exactly what the orphaned-doc check decides. So
it does not run, and says why.

This is not hypothetical: it fires on DataHub's own showcase datapack. Before
the guard existed, a live documented column read as an orphan, and the fix path
would have deleted its description.

## What it costs

A column that was genuinely deleted, whose departure DataHub never recorded,
reads as abstention rather than drift. That case is missed on purpose.

The trade is deliberate: a report with false positives stops being read at all,
and then the true positives go with it. `INSUFFICIENT_EVIDENCE` is a verdict, not
a failure to reach one.
