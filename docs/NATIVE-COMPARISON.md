# What DataHub already does, and what it leaves open

The fair question about any tool built on a platform is whether the platform
already does it. This page answers it with the platform's own words rather than
ours.

Short version: **DataHub open source has rich machinery for whether a
description exists, and none for whether it is still true.** Those are different
questions, and the gap between them is what this project occupies.

## The agent-facing surface, by its own descriptions

Every DataHub skill declares its own scope in frontmatter. Quoted verbatim from
[`datahub-project/datahub-skills`](https://github.com/datahub-project/datahub-skills):

| Skill | Its own words | Reads description *content*? |
|---|---|---|
| `datahub-search` | "search the DataHub catalog, discover entities, answer ad-hoc questions" | as text to match, never to check |
| `datahub-enrich` | "**add or update** metadata in DataHub: descriptions, tags, glossary terms…" | writes what a human decided; does not evaluate it |
| `datahub-quality` | "create or run assertions, check assertion outcomes, raise or resolve incidents" | no — data values |
| `datahub-lineage` | "explore lineage, trace data dependencies, perform impact analysis" | no |
| `datahub-setup` | "set up a DataHub connection, install the CLI, configure authentication" | no |

The most telling line is in `datahub-search`, pointing at the audit skill:

> For systematic audits (**"how complete is our metadata"**), use `/datahub-audit`.

*Complete*, not *correct*. That is DataHub's own framing of what an audit
answers, and it is the distinction this project is built on. (`/datahub-audit`
is referenced by `datahub-search`, `datahub-enrich` and `datahub-lineage`, and
is not itself in the repository — the completeness surface is described but not
yet shipped.)

## Against the four agents DataHub itself proposed

DataHub's own post *Building Autonomous Data Agents with DataHub Agent Context
Kit* names four agents worth building. Three are plainly different work; the
fourth is the one that needs answering, and it is the inverse of this project.

| DataHub's agent | What it does, in DataHub's words | Relation to StillTrue |
|---|---|---|
| **Data Analytics** | text-to-SQL over descriptions, glossary terms, sample queries | *consumes* context; assumes it is true |
| **Data Quality** | "automatically scans for **data** problems… adds data quality **assertions**" | subject is the data — row counts, distributions, values |
| **Data Steward** | "cross-references schema metadata with glossary terms, then **applies** glossary terms and descriptions" | **writes** documentation |
| **Data Engineering** | reads lineage and schema to generate transformation pipelines | subject is the pipeline |

**StillTrue is the Data Steward Agent run backwards.** That agent produces
documentation; this one takes documentation a human already produced and asks
whether it is still true. Same object, opposite direction — and the reverse
direction is the one nobody has built, because the forward direction is what
everybody needs first. Once a Steward Agent has written descriptions across a
catalog at machine speed, the question of which of them are still accurate a year
later stops being hypothetical.

The Data Quality Agent is the one most likely to be mistaken for this, and the
distinction is one word: its assertions take **data** as their subject. Which
brings us to why that is not a naming accident.

## Assertions cannot express it

DataHub models data quality as typed assertions. The Agent Context Kit exposes
the full enum:

```python
assertion_type: Literal['DATASET', 'FRESHNESS', 'VOLUME', 'SQL',
                        'FIELD', 'DATA_SCHEMA', 'CUSTOM']
```

Seven types, all about the data: how fresh, how many rows, what a query returns,
what a column contains, what shape the schema has. **There is no assertion type
whose subject is the documentation.** You cannot write "assert this description
still names columns that exist" — not because it would fail, but because the
type system has no place to put it.

`DATA_SCHEMA` comes closest and moves the other way: it asserts the schema has
not changed. This project assumes the schema changed — that is the normal case —
and asks whether the prose kept up.

## Where the line falls in practice

| Capability | Available in OSS | Question it answers |
|---|---|---|
| Documentation coverage | yes (entity pages, and the described audit surface) | is a description **present**? |
| Assertions / incidents | yes (7 types above) | is the **data** within expectations? |
| Search & discovery | yes | where is the thing? |
| Lineage & impact | yes | what depends on what? |
| Context Hub evaluations | **no** — DataHub Cloud, private beta | is the context **good**? |
| Description-vs-reality check | **no** | is a written description **still true**? |

The last row is this project. The row above it is the closest existing thing and
is not open source: DataHub Cloud's Context Hub is a reviewer workspace with
built-in evaluations, announced in 2026 and in private beta. StillTrue does not
replace it and cannot be compared against it — it is the open-source side of the
same problem.

## What that means for our baselines

`bench/REPORT.md` compares against three baselines. Two of them exist because of
this page:

- **B1 (coverage only)** is the strongest thing DataHub gives you today for free,
  reimplemented honestly: which fields lack a description. It finds the
  undocumented column in the NYC TLC benchmark and structurally cannot find the
  rename, because it never reads the description. *It approximates the
  completeness surface described above; it is not a line-by-line
  reimplementation of a DataHub feature, and we do not claim it is.*
- **A `b2_datahub_native` baseline was specified and is not in the table**, and
  the reason is this page rather than time: on open-source DataHub there is no
  native capability that reads a description and judges it, so such a baseline
  would either duplicate B1 or measure something we invented. The absent baseline
  *is* the finding.

## We did not just write this down

The gap named on this page has a pull request against it.
[`datahub-project/datahub-skills#49`](https://github.com/datahub-project/datahub-skills/pull/49)
adds `datahub-context-drift` — the workflow described here, as a DataHub skill,
in DataHub's own repository, following the conventions of the skills already
there. Whether or not it is merged, the argument is not "DataHub is missing
something"; it is "DataHub is missing something, and here is the piece".

A second PR, [`datahub-project/datahub#18622`](https://github.com/datahub-project/datahub/pull/18622),
fixes something we hit while building: the Agent Context Kit had no shared way to
resolve which of an entity's two descriptions a reader actually sees. That bug
cost us a silent zero-findings scan before we found it (see
[`VALIDATION-INTEGRITY.md`](VALIDATION-INTEGRITY.md)), and the fix is upstream so
the next person does not pay for it.

## The honest limit of this argument

None of the above says the gap is hard to close. It says DataHub has not closed
it in open source, and that everything shipped there answers presence rather than
accuracy. If DataHub Cloud's Context Hub evaluations do exactly this, that is
evidence the problem is worth solving — not evidence that this is redundant,
since the whole point is that the open-source user has nothing.
