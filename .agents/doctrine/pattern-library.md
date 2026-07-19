# Pattern Library

Default answers to recurring problems. Each entry is the pattern a plan gets
for free — using it needs no justification; *not* using it needs an ADR citing
the pattern ID. This is how the repository stays consistent instead of
re-deciding solved problems per feature. Stack-specific bindings (which
library, which queue) belong in ADRs; the pattern here is the invariant.

## Boundaries and interfaces

- **PAT-01 Validate at the boundary.** Parse and validate all external input
  into typed internal structures at the edge; the interior trusts its types
  (AX-08). One validation layer, not scattered defensive checks.
- **PAT-02 Ports and adapters.** The domain core defines interfaces (ports);
  infrastructure implements them (adapters). Swapping a database, queue, or
  HTTP client changes adapters only (AX-03/04).
- **PAT-03 Data access behind a repository interface.** Persistence goes
  through a narrow, intention-revealing interface per aggregate/entity —
  no query logic scattered through business code, no ORM entities leaking
  across module boundaries.
- **PAT-04 API versioning and deprecation.** Additive changes to the current
  version; breaking changes get a new version plus a deprecation window with
  telemetry on old-version usage (AX-06, DD-13).

## Reliability

- **PAT-05 Timeout, retry, breaker — in that order.** Every outbound call:
  explicit timeout; bounded retries with exponential backoff and jitter on
  idempotent operations only; circuit breaker or shed when the dependency is
  persistently down (AX-09).
- **PAT-06 Idempotency keys for external mutations.** Client-supplied or
  derived keys deduplicate retried commands; store the key with the result
  (AX-10).
- **PAT-07 Background work through a queue.** Anything not needed in the
  request path becomes a persisted job with at-least-once delivery, an
  idempotent handler, bounded retries, and a dead-letter path with alerting.
- **PAT-08 Graceful degradation over hard failure.** When a non-critical
  dependency fails, serve the degraded documented behavior (stale cache,
  reduced feature, queued write) and record it — never cascade the outage.

## Data in motion

- **PAT-09 Cache with an ownership story.** Every cache names its source of
  truth, invalidation trigger, TTL, and staleness tolerance (DD-17). A cache
  without an invalidation design is a bug factory.
- **PAT-10 Pagination by cursor.** List endpoints paginate with stable
  cursors (keyset), bounded page sizes, and a documented sort order. Offset
  pagination only for small, static sets.
- **PAT-11 Outbox for cross-system consistency.** When a transaction must
  also emit an event or call another system, write the intent to an outbox in
  the same transaction and deliver asynchronously (DD-16). Distributed
  transactions are not the default.
- **PAT-12 Events carry facts, not commands.** Published events state what
  happened with a versioned schema; consumers decide what to do. Choose
  events vs synchronous calls per the coupling and consistency the contract
  requires, and record the choice in the plan.

## Operations

- **PAT-13 Structured logs, metrics, traces.** Logs are structured key-value
  with correlation/trace IDs and no secrets or PII (DD-14); every feature
  emits rate/error/duration metrics; traces propagate across boundaries
  (AX-14).
- **PAT-14 Feature flags with an expiry.** Risky behavior ships behind a
  flag with an owner and a removal date; flags are configuration (AX-13) and
  dead flags are deleted (AX-20).
- **PAT-15 Health and readiness split.** Liveness says "restart me";
  readiness says "route to me"; readiness checks dependencies, liveness does
  not.
- **PAT-16 Config schema with fail-fast startup.** Configuration is declared,
  typed, and validated at startup; a misconfigured process refuses to start
  rather than limping (AX-13).

## Security

- **PAT-17 AuthN at the edge, authZ at the resource.** Identity is
  established once at the boundary; authorization is checked where the
  resource is accessed, deny-by-default, with decisions logged (AX-14).
- **PAT-18 Secrets from a store, rotated.** Runtime secrets come from a
  secret manager/environment injection, never the repo; design for rotation
  without deploys (AX-13).
- **PAT-19 Vetted primitives only.** Cryptography, password handling, and
  token validation use maintained, audited libraries with safe defaults —
  never hand-rolled primitives, protocols, or verification logic. Passwords
  get an established memory-hard KDF; tokens are verified with the library's
  full validation (signature, expiry, audience), not string inspection.
