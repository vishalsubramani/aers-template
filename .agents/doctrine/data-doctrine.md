# Data Doctrine

Data outlives code. These axioms govern how data is shaped, changed, and
protected so the foundation is designed deliberately — never improvised inside
a feature task. Cite IDs in plans and ADRs; deviation requires an ADR.

## Designing the shape

- **DD-01 Schema first.** The data shape (entities, fields, types,
  constraints, relationships) is designed and human-reviewed before code that
  writes it. A feature that introduces or alters a schema states the full
  delta in its plan's data section; "we'll see what the code needs" is not a
  data model.
- **DD-02 The schema is a public contract.** Anything that persists —
  tables, documents, events, files — is an interface with consumers.
  It gets the same versioning and compatibility discipline as an API (AX-06).
- **DD-03 The database enforces integrity.** Primary keys, foreign keys,
  NOT NULL, UNIQUE, and CHECK constraints live in the database, not only in
  application code. Application validation is a courtesy; the constraint is
  the guarantee.
- **DD-04 Stable surrogate identity.** Every entity has an immutable
  surrogate primary key. Natural keys (emails, usernames, external IDs) are
  UNIQUE constraints, never the identity — they change; identity must not.
  Keys are never reused.
- **DD-05 Nullability is a decision.** NOT NULL is the default. A nullable
  field requires a stated meaning for NULL distinct from empty/zero/unknown
  — if you cannot state it, the field is not nullable.
- **DD-06 Time is UTC and explicit.** Persist timestamps in UTC with
  timezone-aware types. Record `created_at`/`updated_at` on durable entities.
  Distinguish event time from record time when both matter.
- **DD-07 Exact types for exact quantities.** Money and precise quantities
  use integer minor units or decimals — never binary floats. Enumerations are
  constrained (enum types or CHECK), not free strings.
- **DD-08 Normalize by default.** Third normal form is the starting point.
  Denormalization is a performance decision made on evidence (AX-18),
  recorded in an ADR, with one owning write path keeping the copies
  consistent.
- **DD-09 One writer per datum.** Every table/collection has exactly one
  owning module or service that performs writes. Everything else reads
  through an interface or consumes events. Shared write access is how data
  rots.

## Changing the shape

- **DD-10 Migrations are code.** Every schema change is a versioned, ordered
  migration committed with the feature, executable by machine, with a tested
  rollback or an explicit statement of irreversibility in the plan. An
  applied migration is immutable — fix forward with a new one.
- **DD-11 Expand → migrate → contract.** Breaking changes ship as three
  deploys: add the new shape alongside the old, migrate readers/writers and
  backfill, then remove the old shape after verification. One-shot breaking
  migrations are R2+ and need an ADR.
- **DD-12 Backfills are migrations too.** Bulk data corrections are
  idempotent, resumable, rate-limited, and verified with counts or checksums
  recorded in evidence — never ad-hoc scripts run once from a laptop.
- **DD-13 Readers tolerate additive change.** Consumers ignore unknown
  fields; producers never change the meaning of an existing field — add a new
  field and deprecate the old (AX-06 applies to data).

## Protecting the data

- **DD-14 Classify at design time.** Every new field gets a classification
  from `.agents/context/data-classification.md` in the plan's data section.
  PII is minimized at collection, segregated where practical, and never
  written to logs, traces, or evidence (redaction is the default).
- **DD-15 Deletion is designed, not bolted on.** Retention period and
  deletion/erasure mechanics are decided when the data is introduced.
  Soft-delete vs hard-delete is chosen per entity with its audit and privacy
  consequences stated.
- **DD-16 Invariants live in transactions.** A multi-row/multi-entity
  invariant is maintained inside an explicit transaction boundary with a
  stated isolation expectation — or redesigned so it doesn't span one.
  Cross-service invariants get sagas/outbox patterns (PAT-11), not hope.
- **DD-17 Derived data is downstream.** Caches, search indexes, and analytics
  stores are rebuildable projections of the source of truth and never write
  back to it. If it cannot be rebuilt, it is not derived — treat it as source
  data with DD-01..16 applied.
- **DD-18 Every dataset has an owner.** A named team/module owns each durable
  dataset's schema, quality, and lifecycle, recorded in
  `.agents/context/ownership.md`.
