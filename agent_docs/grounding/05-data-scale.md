# Grounding — Data beyond one database: replication, sharding, NoSQL, analytics, caching

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** adding a second datastore, cache, or read path; designing replication/failover,
partitioning/sharding, a NoSQL/search/vector/time-series store, an analytics pipeline, or any
cache or CDN layer.
**Doctrine hooks:** AX-01, AX-09, AX-10, AX-11, AX-18, DD-01, DD-02, DD-03, DD-06, DD-08, DD-09,
DD-12, DD-13, DD-14, DD-15, DD-16, DD-17, DD-18, PAT-08, PAT-09, PAT-11, PAT-17, PAT-20, DF-02,
DF-05, DF-06

## Design checklist

- [ ] Is every store beyond the source of truth a rebuildable projection with a named rebuild
  path, or has it been justified as source data? *(DD-17, DF-02)*
- [ ] For each read path: what staleness bound is acceptable, and where is it stated? Which
  operations require read-your-writes? *(DF-05, PAT-09)*
- [ ] What happens on failover — data loss window, promotion procedure, split-brain guard, and
  how clients rediscover the writer? *(AX-09)*
- [ ] Is the partition/shard/cache key derived from the dominant access pattern, and what is the
  plan when it hot-spots or must change? *(AX-18)*
- [ ] Does every cache name its source of truth, TTL, invalidation trigger, and stampede
  protection? *(PAT-09)*
- [ ] Are pipelines and backfills idempotent, resumable, and replayable with verification counts?
  *(DD-12, AX-10)*
- [ ] Can regulated data (PII, right-to-be-forgotten) be located and deleted in every replica,
  cache, index, and analytics copy? *(DD-14, DD-15)*
- [ ] Does each new store have an owner and a priced operational story (managed vs self-hosted)?
  *(DD-18, DF-06, AX-01)*

## Beyond one database

- **Read replicas & replication lag** — lag is unbounded under load; never read a replica in a
  path that just wrote, and monitor lag as an SLI with a shed/redirect plan *(DF-05, PAT-09)*.
- **Read-your-writes after failover** — a promoted replica may miss recent commits; sessions
  pinned to "the writer" can silently time-travel — design session stickiness or version tokens
  for it *(DF-05)*.
- **Synchronous vs asynchronous replication** — async risks losing acknowledged writes on
  failover; sync trades write latency and availability for it — pick per data class and state the
  loss window in the ADR *(DF-05)*.
- **Failover, promotion, split brain** — automate promotion with fencing (quorum, STONITH-style
  guards); two writers accepting writes is worse than downtime — rehearse failover before you
  need it *(AX-09, DD-09)*.
- **Partitioning: range / list / hash** — range enables pruning and range scans but invites
  hot tails (e.g. time-ordered keys); hash spreads load but kills range queries — choose from the
  query shape, not habit *(AX-18)*.
- **Sharding** — the **key choice** is near-irreversible: pick for even spread and single-shard
  queries; plan **resharding** (consistent hashing, split/merge) day one; expect **hot shards**
  and treat **cross-shard queries**/transactions as designs to avoid *(DD-16, AX-18)*.
- **CQRS read models** — the pattern trade-off lives in `02-patterns-and-architecture.md`; here, the
  read side is a rebuildable projection that lags — state its staleness bound and rebuild path
  *(DF-02, DD-17)*.
- **Materialized views** — the cheapest read model: precomputed inside the same database with a
  stated refresh cadence — reach for one before an external store *(DD-17, DF-02)*.
- **Polyglot persistence** — every extra store multiplies consistency seams, backup paths, and
  on-call surface; add one only as a secondary projection for a demonstrated access pattern
  *(DF-02, DD-17, AX-01)*.
- **NoSQL families: key-value, document, wide-column, graph** — each is a bet on one access
  pattern and gives up ad-hoc queries and cross-entity integrity; you take over what the
  relational engine did for free *(DF-02, DD-03)*.
- **Document modeling: embed vs reference** — embed what is read and updated together and
  bounded in size; reference what grows unboundedly or is shared — embedded copies of shared data
  need one owning write path *(DD-08, DD-09)*.
- **Single-table design & partition keys (DynamoDB-style)** — model access patterns first and
  accept that new query shapes need new indexes or migrations; a low-cardinality or celebrity
  **partition key** creates **hot partitions** that throttle regardless of provisioned capacity.
- **Graph databases & traversals** — justified by multi-hop traversal as the dominant query
  (recursive SQL degrading); as a general store they sacrifice constraints and aggregation —
  prefer a secondary projection *(DF-02, DD-17)*.
- **Time-series databases: retention, downsampling** — declare retention and downsampling tiers
  at design time; raw-forever fills disks, and rollups discard detail you cannot recover — state
  what queries each tier still answers *(DD-15)*.
- **Search engines** — the **inverted index** is a rebuildable projection: **analyzer**/mapping
  changes require full **reindexing** (alias-swap into a new index, don't mutate in place); tune
  **BM25** relevance with a labeled query set, not vibes *(DD-17, AX-18)*.
- **Vector databases** — **ANN** indexes (**HNSW/IVF**) trade recall for latency: measure recall
  against exact search on your data before trusting results; index params and filters shift the
  trade-off, and the index is a rebuildable projection *(DD-17, AX-18)*.

## Data engineering & analytics

- **OLTP vs OLAP** — analytics queries on the OLTP database will eventually take it down; move
  them to a replica or warehouse projection before the incident, not after *(DD-17, DF-02)*.
- **Row vs columnar storage** — columnar wins scans/aggregations over few columns, loses on
  point lookups and single-row updates; picking one store for both workloads serves neither
  *(AX-18)*.
- **Parquet / ORC / Arrow** — default to Parquet on disk and Arrow in memory; schema evolution
  in these files is limited (additive, name-based) — plan column additions, never in-place type
  changes *(DD-13)*.
- **Warehouse vs lake vs lakehouse** — the fork is schema-on-write vs schema-on-read: lakes
  without enforced contracts become swamps — pick per query maturity and record it *(DF-02,
  DD-02)*.
- **ETL vs ELT** — default ELT (load raw, transform in-warehouse) for replayability: raw
  retained means transforms are re-runnable; transform-before-load loses the input you'd need to
  fix a bug *(DD-17)*.
- **Dimensional modeling: facts, dimensions, star & snowflake** — facts are immutable events at
  a declared grain; get the grain wrong and every downstream metric is wrong — prefer star over
  snowflake until dimension size forces it *(DD-01)*.
- **Slowly changing dimensions** — decide overwrite (type 1) vs history rows (type 2) per
  dimension before the first report; retrofitting history after overwrites is impossible
  *(DD-15, DD-01)*.
- **Change data capture** — prefer log-based CDC over dual writes or polling; consumers must
  tolerate duplicates and reordering, and schema changes upstream break pipelines silently —
  contract them *(PAT-11, DD-13, AX-10)*.
- **Idempotent, replayable pipelines** — every stage rerunnable from durable input with
  deterministic output (overwrite-by-partition, merge keys); a pipeline you cannot replay cannot
  be fixed *(AX-10, DD-12)*.
- **Backfills & late-arriving data** — process by event time with a stated lateness window and a
  reconciliation path beyond it; batched, resumable, verified with counts *(DD-12, DD-06)*.
- **Data quality tests & data contracts** — assert freshness, volume, nulls, and referential
  checks at pipeline boundaries and fail loudly; producer schema changes go through a versioned
  contract, not surprise *(DD-02, DD-13, AX-11)*.
- **Data lineage & cataloging** — if you cannot trace a metric to its sources, you cannot debug
  it or honor deletion; record lineage as pipelines are built, with each dataset owned *(DD-18,
  DD-14)*.
- **Medallion architecture** — bronze/silver/gold layering is DD-17 applied to pipelines: raw
  immutable, each layer rebuildable from the one below; writing gold directly from sources
  forfeits replayability *(DD-17)*.
- **Right-to-be-forgotten in pipelines** — erasure must propagate to raw layers, replicas,
  caches, indexes, and derived copies; immutable raw zones need crypto-shredding or rewrite
  strategies designed at ingestion, not at request time *(DD-14, DD-15)*.

## Caching

- **Cache-aside, read-through, write-through, write-behind, write-around** — default cache-aside
  (simple, cache failure degrades to source); write-behind risks losing acknowledged writes —
  treat it as a durability decision, not a cache tweak *(PAT-09, PAT-08, DF-05)*.
- **TTL design** — TTL is the staleness bound and the invalidation backstop: derive it from
  business tolerance, jitter it to avoid synchronized expiry, and never set it "long because
  invalidation works" *(PAT-09, DF-05)*.
- **Cache invalidation** — every cached value names its invalidation trigger at design time;
  "we'll add invalidation later" is the bug factory PAT-09 exists to prevent *(PAT-09, DD-17)*.
- **Versioned / namespaced cache keys** — bump a version segment in the key to invalidate whole
  classes atomically on deploy or schema change; cheaper and safer than enumerating keys to
  delete *(PAT-09)*.
- **Event-driven invalidation** — invalidate from the owning write path's events (outbox), not
  from readers guessing; delivery is at-least-once and delayed, so TTL remains the backstop
  *(PAT-11, DD-09, PAT-09)*.
- **Cache stampede / dogpile** — a hot key expiring sends a thundering herd to the source;
  default request coalescing (**singleflight**), or **locking** / **probabilistic early expiry**
  — any popular key needs one of these *(PAT-20, AX-09)*.
- **Negative caching** — cache "not found" with a short TTL to stop misses hammering the
  source, but bound it or a newly created entity stays invisible past creation *(PAT-09)*.
- **Hot keys** — one celebrity key can saturate a single cache node; detect via per-key metrics,
  then replicate the key, add a local tier, or split with key suffixing *(AX-18, PAT-20)*.
- **Eviction policies: LRU, LFU, TinyLFU, ARC** — LRU dies on scans, LFU on shifting
  popularity; default the library's modern default (TinyLFU/ARC) and validate with measured hit
  rate, not intuition *(AX-18, AX-01)*.
- **Local vs distributed caches; multi-tier** — local caches are fastest and most incoherent
  (per-instance staleness after writes); each added tier multiplies invalidation paths — state
  coherence expectations per tier *(PAT-09, DF-05)*.
- **CDN & edge caching** — the cache key is the design: normalize URLs, declare **Vary**
  headers precisely (over-varying kills hit rate, under-varying leaks responses across users),
  and never let authenticated responses default to cacheable *(PAT-09, PAT-17)*.
- **Memoization vs caching** — memoization suits pure functions in-process; the moment the value
  depends on mutable external state it is a cache and owes PAT-09 its invalidation story
  *(PAT-09)*.
- **Cache warming** — a cold cache after deploy or failover can stampede the source into
  collapse; warm critical keys before taking traffic, or ramp traffic gradually *(PAT-20,
  AX-09)*.
- **Freshness vs consistency tradeoffs** — a cache is a deliberate consistency downgrade: state
  the staleness bound per read path and which operations must bypass it — "usually fresh" is not
  a bound *(DF-05, PAT-09)*.
