# Grounding — APIs & contracts

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing any external interface — HTTP/gRPC/GraphQL endpoints, SDKs,
error shapes, pagination, versioning, or deprecation decisions.
**Doctrine hooks:** AX-05, AX-06, AX-09, AX-10, AX-11, AX-16, DD-02, DD-13, PAT-01, PAT-04,
PAT-06, PAT-10, PAT-20

## Design checklist

- [ ] Is the contract (OpenAPI/proto/GraphQL schema) written and reviewed before the
      implementation, and is it executable in CI? *(AX-06, DD-02)*
- [ ] Is every unsafe operation safe to deliver twice — idempotency key, natural dedup, or
      compare-and-set? *(AX-10, PAT-06)*
- [ ] Do list endpoints use opaque cursors with bounded page sizes and a documented sort
      order? *(PAT-10)*
- [ ] Are errors one typed, documented format clients can branch on — not ad-hoc bodies or
      200-with-error? *(AX-11)*
- [ ] Is this change additive? If breaking: new version, deprecation window, and telemetry on
      old-version usage? *(AX-06, PAT-04)*
- [ ] Do readers ignore unknown fields while strictly validating the fields they act on?
      *(DD-13, PAT-01)*
- [ ] What do clients see under overload — rate-limit headers, Retry-After, and a retry policy
      that won't amplify? *(AX-09, PAT-20)*
- [ ] Is the exposed surface the minimum, and is it classified public vs internal with the
      matching compatibility promise? *(AX-05)*
- [ ] Is compatibility checked mechanically (openapi-diff, buf breaking, registry mode) rather
      than by reviewer eyeballs? *(DD-02)*
- [ ] For staggered rollouts, which side needs backward vs forward compatibility, and is the
      deploy order stated? *(DD-13)*

## Resource modeling and ergonomics

- **REST resource modeling / Richardson maturity model** — model resources around nouns and
  lifecycle; level 2 (verbs + status codes) is the pragmatic target — a clean action endpoint
  beats a contorted resource, and HATEOAS rarely pays. *(AX-06)*
- **Correct verbs & status codes** — generic clients key retries and caching off them:
  200-with-error-body breaks tooling; 4xx means caller bug, 5xx means yours; keep GET/PUT/DELETE
  idempotent. *(AX-10, AX-11)*
- **Pagination: cursor over offset** — the repo default is keyset cursors; offset only for small
  static sets. Keep cursors opaque so their encoding can change without a version bump. *(PAT-10)*
- **Filtering, sorting, sparse fieldsets** — an open-ended filter grammar is an unindexable query
  API; whitelist filterable/sortable fields against known indexes and cap combinations, or you
  have shipped your database.
- **Standard error formats (RFC 9457 problem+json)** — one machine-readable shape with a stable
  `type` URI lets clients branch on error kind, not message strings; never leak stack traces or
  internal identifiers. *(AX-11)*
- **Conditional requests / ETags** — concurrent PUTs silently lose updates without
  If-Match/ETag optimistic concurrency; conditional GET buys client caching for free. Default for
  any read-modify-write resource.

## Reliability semantics at the edge

- **Idempotency keys for unsafe operations** — store the key with the result and replay the
  stored response on duplicates; re-executing "just once more" is the double-charge bug.
  *(AX-10, PAT-06)*
- **Rate-limit headers & Retry-After** — publish limits and honor Retry-After in your own
  clients; without server-stated backoff, clients invent retry storms that arrive synchronized.
  *(AX-09, PAT-20)*

## Versioning, compatibility, deprecation

- **API versioning: URI vs header vs media type** — pick one mechanism per API and bias toward
  additive change so most changes need no version at all; URI versions are crude but debuggable
  from logs. *(AX-06, PAT-04)*
- **Deprecation policy; Sunset headers** — a deprecation without old-version usage telemetry and
  a dated Sunset header never ends; announce, measure, then remove on the stated date. *(PAT-04)*
- **Tolerant reader** — ignore unknown fields but validate the fields you act on; tolerance
  without validation turns schema drift into silent corruption. *(DD-13, PAT-01)*
- **Backward vs forward compatibility** — staggered deploys mean old readers meet new data
  (forward) and new readers meet old data (backward); name which direction each pair needs and
  sequence the rollout accordingly. *(DD-13)*
- **Semantic versioning as a promise, not a number** — the major version is a compatibility
  contract; if CI cannot detect a break mechanically, you cannot honestly promise semver.
  *(AX-06, DD-02)*
- **Public vs internal API standards** — anything consumed by a party you cannot deploy is
  public and gets full deprecation discipline; decide the classification at design time, not
  when the first external caller complains. *(AX-05, PAT-04)*

## Contract-first tooling

- **OpenAPI / JSON Schema; contract-first design** — write the spec before the handler and make
  it executable (request validation and contract tests generated from it); a hand-maintained
  spec that trails the code is worse than none. *(AX-06, DD-02)*
- **SDK generation** — generate clients from the contract instead of hand-writing them, but
  review the generated surface as a public interface: it freezes your naming and error shapes
  into consumers. *(AX-05)*
- **Consumer-driven contract tests** — when you cannot run consumers' stacks, verify their
  recorded expectations (Pact-style) in provider CI so breaks surface before deploy, not after.
  *(AX-16)*

## gRPC, GraphQL, and schema evolution

- **gRPC: protobuf field numbers, unknown fields, deadlines** — never reuse or renumber fields
  (`reserved` deleted ones); unknown fields must survive proxy round-trips; propagate deadlines
  through every hop or timeouts stack uselessly. *(AX-09, DD-13)*
- **GraphQL: resolvers, dataloader, complexity limits, persisted queries** — resolvers hide N+1
  by design, so batch with dataloader; enforce depth/complexity limits and prefer persisted
  queries publicly, or clients author your worst query. *(PAT-20)*
- **Schema evolution rules (protobuf/Avro)** — encode compatibility rules in CI (buf breaking,
  schema-registry compatibility mode); human review does not catch a removed field two services
  away. *(DD-02, DD-13)*
