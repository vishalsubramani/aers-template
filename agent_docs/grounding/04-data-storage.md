# Grounding — Relational databases, schema & migrations

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing tables, indexes, queries, transactions, ORM data access,
schema migrations, backfills, or anything that touches a relational database's write path.
**Doctrine hooks:** AX-01, AX-08, AX-10, AX-12, AX-14, AX-15, AX-18, DD-01, DD-02, DD-03, DD-04,
DD-05, DD-06, DD-07, DD-08, DD-10, DD-11, DD-12, DD-14, DD-15, DD-16, DD-17, PAT-01, PAT-03,
PAT-09, PAT-10, DF-02

## Design checklist

- [ ] Is the full schema delta (types, constraints, nullability, keys) stated in the plan before
      any code writes it? *(DD-01, DD-03, DD-05)*
- [ ] Are amounts and precise quantities exact types (never floats), enums constrained, and
      timestamps timezone-aware UTC — and does every new field carry a classification in the
      plan's data section? *(DD-06, DD-07, DD-14)*
- [ ] For every multi-row invariant: which transaction boundary and isolation level protects it,
      and which anomaly (lost update, write skew) was checked? *(DD-16)*
- [ ] Does every new query have an index that serves it, verified with EXPLAIN on realistic data
      volume — and is each new index's write cost accepted?
- [ ] Under concurrent writers, is contention handled by an explicit choice: optimistic version
      column, `FOR UPDATE`, or advisory lock — with a consistent lock ordering? *(AX-12)*
- [ ] Is the migration expand → migrate → contract, safe to run while the old code still serves
      traffic, and is rollback tested or irreversibility declared? *(DD-10, DD-11, AX-15)*
- [ ] Are backfills batched, resumable, idempotent, and verified with counts? *(DD-12)*
- [ ] Does any DDL statement take a long-held lock on a large or hot table (type change, NOT NULL,
      non-concurrent index)? If yes, what is the online strategy?
- [ ] Is pagination keyset-based, and are list queries bounded? *(PAT-10)*
- [ ] Soft or hard delete — chosen per entity with query, index, uniqueness, and privacy
      consequences stated? *(DD-15)*
- [ ] Is the connection pool sized from arithmetic (instances × pool vs. DB max connections), not
      defaults?

## Relational databases

- **ACID** — check each letter separately: durability hinges on fsync/replication settings, and
  "I" is only what your chosen isolation level actually gives — never assume serializable
  *(DD-16)*.
- **Transactions & isolation levels** — read committed is the common default; state the level an
  invariant needs rather than inheriting it, and handle serialization-failure retries if you raise
  it *(DD-16)*.
- **Anomalies: dirty read, non-repeatable read, phantom read, lost update, write skew** — for each
  invariant, name which anomaly could break it; **lost update** and **write skew** survive read
  committed and snapshot isolation respectively, so they bite most.
- **MVCC** — readers don't block writers, but every update copies the row: expect dead tuples,
  vacuum debt, and stale snapshots in long transactions; design hot-update tables accordingly.
- **Two-phase locking** — engines that lock instead of snapshot (or in serializable mode) block
  readers/writers; lock-heavy transactions must be short and acquire in one global order.
- **Optimistic locking** — default for low-contention read-modify-write: version column plus
  compare-and-set, retry on conflict; cheaper than locks but callers must handle the retry
  *(AX-10, AX-12)*.
- **Pessimistic locking** — reach for it only when conflicts are frequent or retries costly; held
  locks serialize throughput and any lock held across user think-time is a design bug.
- **SELECT ... FOR UPDATE** — the standard read-modify-write guard inside one transaction; without
  it the read is unlocked and the update races. Prefer `SKIP LOCKED` for job-queue polling.
- **Advisory locks** — app-defined mutexes for things with no row to lock (cron singletons,
  migrations); session-scoped ones leak through pooled connections — prefer transaction-scoped.
- **Deadlock detection & lock ordering** — the database resolves deadlocks by aborting a victim,
  so callers need retries; prevent them by acquiring rows/tables in one canonical order everywhere
  *(AX-12)*.
- **Indexing: B-tree, hash, GIN/GiST, BRIN, covering, composite, partial, expression** — B-tree is
  default; **composite** column order must match query prefixes; **partial** indexes fit
  soft-delete/status filters; every index taxes writes — justify each *(AX-18)*.
- **Index selectivity & cardinality** — an index on a low-cardinality column (status, boolean,
  tenant flags) is mostly dead weight; the planner will skip it — check selectivity before adding.
- **EXPLAIN / ANALYZE & reading query plans** — evidence for any query-performance claim
  *(AX-18)*: run on production-scale data, and treat seq scans on large tables and misestimated
  row counts as findings.
- **Join strategies: nested loop, hash join, merge join** — a nested loop on two large inputs
  means a missing index or bad estimate; plan flips at data-size thresholds cause "worked in
  staging" latency cliffs.
- **Planner statistics** — stale or default stats produce catastrophic plans; after bulk loads or
  backfills, analyze the table, and expect skewed columns to need extended statistics.
- **N+1 queries** — the ORM's favorite trap: a loop of lazy loads that profiles fine on dev data;
  review any relationship traversal inside iteration, fix with joins or batched IN-loading
  *(PAT-03)*.
- **Eager vs lazy loading** — declare per query path, not globally: lazy in loops causes N+1,
  blanket-eager drags whole object graphs; the repository interface should make the choice visible
  *(PAT-03)*.
- **Connection pooling & pool-sizing math** — connections are scarce (each has server-side cost);
  size from instances × pool ≤ DB max minus admin headroom, and beware serverless/lambda fan-out
  exhausting it.
- **Prepared statements** — parameterize always — it's the SQL-injection boundary *(PAT-01)* and
  saves parse cost; note generic plans can misbehave on skewed parameters, and poolers may break
  session-level prepares.
- **Batch writes** — per-row inserts in a loop are a network-latency tax; use multi-row
  insert/COPY, keep batches bounded so transactions stay short and failures are retryable
  *(DD-12)*.
- **Upserts (ON CONFLICT)** — the atomic answer to check-then-insert races and the idempotent
  write primitive *(AX-10)*; requires a real unique constraint, and "DO NOTHING" silently swallows
  conflicts — decide if that's correct.
- **Keyset (cursor) vs offset pagination** — offset scans and discards all skipped rows and drifts
  under concurrent writes; keyset on a unique-suffixed sort is the default *(PAT-10)*.
- **Soft deletes** — long-term cost: every query, unique constraint, and foreign key must now
  account for `deleted_at`; choose per entity with the privacy/erasure story stated, use partial
  indexes *(DD-15)*.
- **Surrogate vs natural keys** — surrogate PK always; natural keys are UNIQUE constraints because
  they change and identity must not *(DD-04)*.
- **UUIDv4 vs UUIDv7 vs sequences** — random v4 keys shred B-tree locality and cache at scale;
  prefer UUIDv7 or sequences for high-insert tables, and never treat sequence gaps as bugs
  *(DD-04)*.
- **Foreign keys, cascades, constraints** — the last line of defense: put them in the database,
  not just the ORM *(DD-03, AX-08)*; treat `ON DELETE CASCADE` as a mass-delete footgun — prefer
  RESTRICT and explicit deletion, and index FK columns.
- **Views & materialized views** — views are query aliases, not performance; materialized views
  are derived data needing an explicit refresh trigger and staleness bound *(DD-17, PAT-09)*.
- **Triggers & stored procedures** — use with restraint: invisible write-path logic that dodges
  tests, tracing, and code review; acceptable for audit/integrity mechanics, not business rules —
  needs an ADR.
- **Write-ahead logs, checkpoints, fsync** — durability is a configuration, not a given: relaxed
  fsync/async commit trades crash-loss for speed — make that trade only in an ADR; WAL volume
  spikes during backfills.
- **Vacuum & table bloat** — MVCC's bill: high-churn tables bloat and slow scans, and
  long-running/idle-in-transaction sessions block cleanup — set transaction timeouts and watch
  dead-tuple metrics *(AX-14)*.
- **B-tree vs LSM engines; compaction; write amplification** — LSM buys write throughput with
  read/compaction cost and background stalls; choosing a non-default engine is a DF-02 decision
  with an ADR *(DF-02, AX-01)*.

## Schema & migrations

- **Normal forms (1NF–BCNF) & when to denormalize** — 3NF is the default; denormalize only on
  measured evidence, with one owning write path keeping copies consistent *(DD-08, AX-18)*.
- **Timestamp columns** — reach for the timezone-aware type by default; naive datetimes look fine
  until the first cross-region reader or DST boundary, and durable entities want
  `created_at`/`updated_at` from day one *(DD-06)*.
- **Money & enum columns** — a float amount or free-string status column passes review and
  corrupts later: exact types for quantities, enum types or CHECK constraints for enumerations
  *(DD-07, AX-08)*.
- **Field classification at design time** — classify each new column when the schema is designed,
  not at audit time; retrofitting classification means grepping production data for PII *(DD-14)*.
- **Migrations as code; forward-only mindset** — versioned, ordered, machine-runnable, committed
  with the feature; an applied migration is immutable — fix forward with a new one, never edit
  history *(DD-10)*.
- **Expand → migrate → contract** — the default for any breaking change: old and new code must
  both work at every intermediate step; a one-shot rename/drop is an outage with extra steps
  *(DD-11, AX-15)*.
- **Backfills: batched, resumable, idempotent** — bounded batches with progress tracking,
  rate-limited, restartable mid-way, verified with counts/checksums — never one giant UPDATE in a
  migration *(DD-12)*.
- **Online DDL (gh-ost, pt-osc, CONCURRENTLY)** — table-locking DDL on hot tables needs an online
  path: `CREATE INDEX CONCURRENTLY`, `NOT VALID` constraints validated later, plus `lock_timeout`
  so a blocked DDL fails instead of queueing all traffic behind it.
- **Schema versioning** — the live schema version is tracked in the database and asserted at
  deploy; drift between environments or ORM models and applied migrations is a build failure, not
  a surprise *(DD-02)*.
- **Seed data & reference data** — reference data (enums-as-rows, lookup tables) is migrated code
  with the schema *(DD-10)*; environment seed/fixture data is not — keep the two pipelines
  separate so tests never depend on prod-only rows.
